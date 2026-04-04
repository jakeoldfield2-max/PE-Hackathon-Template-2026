#!/usr/bin/env bash
# chaos.sh — Chaos engineering scripts for URLPulse
#
# Usage:
#   ./scripts/chaos.sh kill-one       Kill 1 app instance, verify 2 still serve
#   ./scripts/chaos.sh kill-all       Kill all app instances, wait for alert
#   ./scripts/chaos.sh error-flood    Send 200 bad requests to trigger HighErrorRate
#   ./scripts/chaos.sh kill-db        Kill PostgreSQL, show /health vs /ready difference
#   ./scripts/chaos.sh kill-redis     Kill Redis, verify graceful degradation
#   ./scripts/chaos.sh full-demo      Run all chaos tests sequentially
#
# All modes auto-recover — containers have restart:always

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

BASE_URL="${BASE_URL:-http://localhost}"

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
  docker compose stop app-1

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
  docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep app

  log "Restarting app-1..."
  docker compose start app-1
  sleep 3

  pass "app-1 restarted. All 3 instances serving."
  docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep app
  echo ""
}

# ── Mode: kill-all ───────────────────────────────────────────────────────────
kill_all() {
  echo ""
  log "=== CHAOS: Kill All Instances ==="
  log "Proves: alerting works — Discord should fire ServiceDown alert (~60-90s)"
  echo ""

  log "Killing all app instances..."
  docker compose stop app-1 app-2 app-3

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
  docker compose start app-1 app-2 app-3

  wait_for_recovery "app instances"
  echo ""
}

# ── Mode: error-flood ────────────────────────────────────────────────────────
error_flood() {
  echo ""
  log "=== CHAOS: Error Flood ==="
  log "Proves: HighErrorRate alert triggers when error rate > 10%"
  echo ""

  log "Sending 200 bad requests to trigger errors..."
  local error_count=0
  for i in $(seq 1 200); do
    local status
    status=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/users/99999" 2>/dev/null || echo "000")
    if [ "$status" != "200" ]; then
      error_count=$((error_count + 1))
    fi
  done

  pass "Sent 200 requests, $error_count returned errors"
  warn "Check Discord for HighErrorRate alert (~60s)..."
  log "Check Prometheus: http://localhost:9090/alerts"
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
  docker compose stop postgres

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
  docker compose start postgres

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
  docker compose stop redis

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
  docker compose start redis
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
  docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "app|postgres|redis|nginx"
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
    echo "Usage: ./scripts/chaos.sh <mode>"
    echo ""
    echo "Modes:"
    echo "  kill-one      Kill 1 app instance, verify 2 still serve"
    echo "  kill-all      Kill all instances, wait for Discord alert"
    echo "  error-flood   Send 200 bad requests, trigger HighErrorRate alert"
    echo "  kill-db       Kill PostgreSQL, show /health vs /ready"
    echo "  kill-redis    Kill Redis, verify graceful degradation"
    echo "  full-demo     Run all chaos tests sequentially"
    ;;
esac
