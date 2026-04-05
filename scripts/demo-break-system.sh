#!/usr/bin/env bash
# demo-break-system.sh
#
# Purpose:
#   Run a stage-friendly "break the system" demo with preflight checks,
#   controlled failures, and explicit recovery verification.
#
# Usage:
#   ./scripts/demo-break-system.sh
#   ./scripts/demo-break-system.sh --remote
#   ./scripts/demo-break-system.sh --remote --skip-seed

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

REMOTE="false"
SKIP_SEED="false"
VM_NAME="${VM_NAME:-urlpulse-vm}"
ZONE="${ZONE:-us-central1-a}"
BASE_URL="${BASE_URL:-http://localhost}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="true"
      shift
      ;;
    --skip-seed)
      SKIP_SEED="true"
      shift
      ;;
    *)
      echo "Usage: ./scripts/demo-break-system.sh [--remote] [--skip-seed]"
      exit 1
      ;;
  esac
done

now() { date '+%H:%M:%S'; }
log()  { echo -e "${CYAN}[$(now)] [demo]${NC} $1"; }
ok()   { echo -e "${GREEN}[$(now)] [ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(now)] [wait]${NC} $1"; }
err()  { echo -e "${RED}[$(now)] [error]${NC} $1"; }

resolve_remote_url() {
  if ! command -v gcloud >/dev/null 2>&1; then
    err "gcloud is required for --remote mode"
    exit 1
  fi

  local ip
  ip=$(gcloud compute addresses describe urlpulse-ip --region="${ZONE%-*}" --format='value(address)' 2>/dev/null || true)

  if [ -z "$ip" ]; then
    ip=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || true)
  fi

  if [ -z "$ip" ]; then
    err "Could not resolve remote VM IP. Set VM_NAME/ZONE or check gcloud auth/project."
    exit 1
  fi

  BASE_URL="http://$ip"
  ok "Remote target resolved: $BASE_URL"
}

http_code() {
  local method="$1"
  local path="$2"
  curl -sS -o /dev/null -w "%{http_code}" -X "$method" "$BASE_URL$path" 2>/dev/null || echo "000"
}

assert_code() {
  local method="$1"
  local path="$2"
  local expected="$3"
  local code
  code=$(http_code "$method" "$path")
  if [ "$code" != "$expected" ]; then
    err "$method $path expected $expected, got $code"
    exit 1
  fi
  ok "$method $path -> $code"
}

wait_for_code() {
  local method="$1"
  local path="$2"
  local expected="$3"
  local max_wait="${4:-90}"

  log "Waiting for $method $path to return $expected (max ${max_wait}s)..."
  for i in $(seq 1 "$max_wait"); do
    local code
    code=$(http_code "$method" "$path")
    if [ "$code" = "$expected" ]; then
      ok "$method $path -> $code after ${i}s"
      return 0
    fi
    if [ "$i" -eq 1 ] || [ $((i % 5)) -eq 0 ]; then
      warn "$method $path still at $code (${i}/${max_wait}s)"
    fi
    sleep 1
  done

  err "$method $path did not reach $expected within ${max_wait}s"
  return 1
}

run_chaos_step() {
  local mode="$1"
  if [ "$REMOTE" = "true" ]; then
    ./scripts/chaos.sh --remote "$mode"
  else
    ./scripts/chaos.sh "$mode"
  fi
}

if [ "$REMOTE" = "true" ]; then
  resolve_remote_url
else
  ok "Local target: $BASE_URL"
fi

log "Preflight: verifying service is healthy before demo"
assert_code GET /health 200
assert_code GET /ready 200

if [ "$SKIP_SEED" = "false" ]; then
  log "Seeding demo data"
  seed_code=$(http_code POST /seed)
  if [ "$seed_code" = "200" ] || [ "$seed_code" = "201" ]; then
    ok "POST /seed -> $seed_code"
  else
    err "POST /seed expected 200/201, got $seed_code"
    exit 1
  fi
else
  warn "Skipping seed step (--skip-seed)"
fi

log "Phase 1: kill one app instance (expect no outage)"
run_chaos_step kill-one
assert_code GET /health 200

log "Phase 2: kill Redis (expect graceful degradation)"
run_chaos_step kill-redis
assert_code GET /health 200

log "Phase 3: kill Postgres (expect /ready to fail briefly)"
run_chaos_step kill-db
assert_code GET /health 200
wait_for_code GET /ready 200 120

log "Phase 4: trigger high error rate alert"
run_chaos_step error-flood

log "Phase 5: full app outage + recovery"
run_chaos_step kill-all
assert_code GET /health 200
assert_code GET /ready 200

echo ""
ok "Break-the-system demo completed successfully"
warn "Watch Discord/Alertmanager for HighErrorRate and ServiceDown alerts"
log "Suggested tabs: $BASE_URL:3000 (Grafana), $BASE_URL:9090/alerts (Prometheus), $BASE_URL:9093 (Alertmanager)"
