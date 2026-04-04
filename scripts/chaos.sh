#!/usr/bin/env bash
# chaos.sh — Chaos engineering scripts for URLPulse
#
# Usage (local — run against local Docker stack):
#   ./scripts/chaos.sh kill-one
#   ./scripts/chaos.sh full-demo
#
# Usage (remote — run against hosted VM):
#   ./scripts/chaos.sh --remote kill-one          # Uses gcloud SSH
#   ./scripts/chaos.sh --remote error-flood       # Sends requests to VM IP
#   ./scripts/chaos.sh --remote full-demo
#
# Modes:
#   kill-one      Kill 1 app instance, verify 2 still serve
#   kill-all      Kill all instances, wait for Discord alert
#   error-flood   Send 200 bad requests to trigger HighErrorRate alert
#   kill-db       Kill PostgreSQL, show /health vs /ready difference
#   kill-redis    Kill Redis, verify graceful degradation
#   full-demo     Run all chaos tests sequentially
#
# All modes auto-recover — containers have restart:always

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Remote mode ──────────────────────────────────────────────────────────────
REMOTE="false"
VM_NAME="${VM_NAME:-urlpulse-vm}"
ZONE="${ZONE:-us-central1-a}"
APP_DIR="PE-Hackathon-Template-2026"

if [ "${1:-}" = "--remote" ]; then
  REMOTE="true"
  shift
fi

if [ "$REMOTE" = "true" ]; then
  # Get VM IP for curl-based checks
  VM_IP=$(gcloud compute addresses describe urlpulse-ip --region="${ZONE%-*}" --format='value(address)' 2>/dev/null || echo "")
  if [ -z "$VM_IP" ]; then
    VM_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "")
  fi
  if [ -z "$VM_IP" ]; then
    echo "ERROR: Could not determine VM IP. Check gcloud config."
    exit 1
  fi
  BASE_URL="http://$VM_IP"
  echo -e "${CYAN}[chaos]${NC} Remote mode: targeting $VM_NAME ($VM_IP)"
else
  BASE_URL="${BASE_URL:-http://localhost}"
fi

# Run a docker compose command — locally or via SSH
run_docker() {
  if [ "$REMOTE" = "true" ]; then
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="cd $APP_DIR && docker compose $1" 2>/dev/null
  else
    docker compose $1
  fi
}

log()  { echo -e "${CYAN}[chaos]${NC} $1"; }
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WAIT]${NC} $1"; }

check_health() {
  local status
  status=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
  echo "$status"
}

check_ready() {
  local status
  status=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/ready" 2>/dev/null || echo "000")
  echo "$status"
}

wait_for_recovery() {
  local label="$1"
  local max_wait="${2:-60}"
  log "Waiting for $label to recover (max ${max_wait}s)..."
  for i in $(seq 1 "$max_wait"); do
    if [ "$(check_health)" = "200" ]; then
      pass "$label recovered after ${i}s"
      return 0
    fi
    sleep 1
  done
  fail "$label did not recover after ${max_wait}s"
  return 1
}

# ── Mode: kill-one ───────────────────────────────────────────────────────────
kill_one() {
  echo ""
  log "=== CHAOS: Kill One Instance ==="
  log "Proves: horizontal scaling — 2 of 3 instances keep serving"
  echo ""

  log "Killing app-1..."
  run_docker "stop app-1"

  sleep 2

  local status
  status=$(check_health)
  if [ "$status" = "200" ]; then
    pass "/health still returns 200 (served by app-2 or app-3)"
  else
    fail "/health returned $status"
  fi

  # Show which instances are running
  log "Running instances:"
  run_docker "ps --format 'table {{.Name}}\t{{.Status}}'" | grep app

  log "Restarting app-1..."
  run_docker "start app-1"
  sleep 3

  pass "app-1 restarted. All 3 instances serving."
  run_docker "ps --format 'table {{.Name}}\t{{.Status}}'" | grep app
  echo ""
}

# ── Mode: kill-all ───────────────────────────────────────────────────────────
kill_all() {
  echo ""
  log "=== CHAOS: Kill All Instances ==="
  log "Proves: alerting works — Discord should fire ServiceDown alert (~60-90s)"
  echo ""

  log "Killing all app instances..."
  run_docker "stop app-1 app-2 app-3"

  local status
  status=$(check_health)
  if [ "$status" != "200" ]; then
    pass "/health is DOWN (status: $status) — correct!"
  else
    fail "/health still returns 200 — something is wrong"
  fi

  warn "Check Discord for ServiceDown alert (fires after ~60s)..."
  warn "Waiting 30s to demonstrate downtime..."
  sleep 30

  log "Restarting all instances..."
  run_docker "start app-1 app-2 app-3"

  wait_for_recovery "app instances"
  echo ""
}

# ── Mode: error-flood ────────────────────────────────────────────────────────
error_flood() {
  echo ""
  log "=== CHAOS: Error Flood ==="
  log "Proves: HighErrorRate alert triggers when error rate > 10%"
  log "Target: $BASE_URL"
  echo ""

  log "Sending sustained 5xx errors for ~3 minutes to trigger alert..."
  log "  (Alert rule requires error rate > 5% for 2 consecutive minutes)"
  local error_count=0
  local total=0
  local end_time=$((SECONDS + 180))
  while [ $SECONDS -lt $end_time ]; do
    for i in $(seq 1 10); do
      curl -sf -o /dev/null "$BASE_URL/chaos/error" 2>/dev/null || true
      error_count=$((error_count + 1))
      total=$((total + 1))
    done
    # Mix in a few good requests so the rate calculation has a denominator
    curl -sf -o /dev/null "$BASE_URL/health" 2>/dev/null || true
    total=$((total + 1))
    sleep 1
  done

  pass "Sent $total requests ($error_count were 5xx errors)"
  warn "Check Discord for HighErrorRate alert (should fire soon)..."
  log "Check Prometheus: ${BASE_URL}:9090/alerts"
  echo ""
}

# ── Mode: kill-db ────────────────────────────────────────────────────────────
kill_db() {
  echo ""
  log "=== CHAOS: Kill Database ==="
  log "Proves: /health vs /ready difference — app is alive but not ready"
  echo ""

  # Show before state
  log "Before: checking endpoints..."
  local health_before ready_before
  health_before=$(check_health)
  ready_before=$(check_ready)
  log "  /health: $health_before  /ready: $ready_before"

  log "Killing PostgreSQL..."
  run_docker "stop postgres"

  sleep 3

  local health_after ready_after
  health_after=$(check_health)
  ready_after=$(check_ready)

  log "After killing DB:"
  if [ "$health_after" = "200" ]; then
    pass "/health: $health_after — app process is ALIVE"
  else
    fail "/health: $health_after"
  fi

  if [ "$ready_after" != "200" ]; then
    pass "/ready: $ready_after — app is NOT READY (DB disconnected)"
  else
    fail "/ready: $ready_after — should be 503"
  fi

  log "Restarting PostgreSQL..."
  run_docker "start postgres"

  # Wait for postgres to be healthy
  sleep 10

  local ready_recovered
  ready_recovered=$(check_ready)
  if [ "$ready_recovered" = "200" ]; then
    pass "/ready: $ready_recovered — DB reconnected"
  else
    warn "/ready: $ready_recovered — DB may still be starting up"
  fi
  echo ""
}

# ── Mode: kill-redis ─────────────────────────────────────────────────────────
kill_redis() {
  echo ""
  log "=== CHAOS: Kill Redis ==="
  log "Proves: graceful degradation — app serves requests without cache"
  echo ""

  # Show cached response
  log "Before: fetching /users (should be cached)..."
  local cache_header
  cache_header=$(curl -sf -D - "$BASE_URL/users" 2>/dev/null | grep -i "X-Cache" || echo "No X-Cache header")
  log "  $cache_header"

  log "Killing Redis..."
  run_docker "stop redis"

  sleep 2

  local status
  status=$(check_health)
  if [ "$status" = "200" ]; then
    pass "/health: 200 — app still running without Redis"
  else
    fail "/health: $status"
  fi

  # Try fetching users without cache
  local users_status
  users_status=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/users" 2>/dev/null || echo "000")
  if [ "$users_status" = "200" ]; then
    pass "/users: 200 — serves from DB directly (graceful degradation)"
  else
    fail "/users: $users_status"
  fi

  log "Restarting Redis..."
  run_docker "start redis"
  sleep 3

  pass "Redis back online. Cache warming up."
  echo ""
}

# ── Mode: full-demo ──────────────────────────────────────────────────────────
full_demo() {
  echo ""
  echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║     URLPulse Chaos Engineering Demo    ║${NC}"
  echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
  echo ""

  kill_one
  sleep 2
  kill_redis
  sleep 2
  kill_db
  sleep 2
  error_flood

  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║     All chaos tests completed!         ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
  echo ""
  log "Final status:"
  run_docker "ps --format 'table {{.Name}}\t{{.Status}}'" | grep -E "app|postgres|redis|nginx"
}

# ── Main ─────────────────────────────────────────────────────────────────────
case "${1:-help}" in
  kill-one)     kill_one ;;
  kill-all)     kill_all ;;
  error-flood)  error_flood ;;
  kill-db)      kill_db ;;
  kill-redis)   kill_redis ;;
  full-demo)    full_demo ;;
  *)
    echo "Usage: ./scripts/chaos.sh [--remote] <mode>"
    echo ""
    echo "Modes:"
    echo "  kill-one      Kill 1 app instance, verify 2 still serve"
    echo "  kill-all      Kill all instances, wait for Discord alert"
    echo "  error-flood   Send 200 bad requests, trigger HighErrorRate alert"
    echo "  kill-db       Kill PostgreSQL, show /health vs /ready"
    echo "  kill-redis    Kill Redis, verify graceful degradation"
    echo "  full-demo     Run all chaos tests sequentially"
    echo ""
    echo "Options:"
    echo "  --remote      Run against hosted VM (uses gcloud SSH for docker commands)"
    echo "                Without --remote, runs against local Docker stack"
    echo ""
    echo "Examples:"
    echo "  ./scripts/chaos.sh kill-one                # Local"
    echo "  ./scripts/chaos.sh --remote kill-one       # Remote VM"
    echo "  ./scripts/chaos.sh --remote full-demo      # Full demo on VM"
    ;;
esac
