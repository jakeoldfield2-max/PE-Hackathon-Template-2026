#!/usr/bin/env bash
# setup-vm.sh — Configure .env and start the app on the GCP VM
#
# Usage:
#   ./scripts/setup-vm.sh                                    # Interactive (prompts for secrets)
#   ./scripts/setup-vm.sh --db-pass X --grafana-user Y ...   # Non-interactive

set -euo pipefail

VM_NAME="urlpulse-vm"
ZONE="us-central1-a"
APP_DIR="PE-Hackathon-Template-2026"

DB_PASS=""
GRAFANA_USER=""
GRAFANA_PASS=""
DISCORD_WEBHOOK=""

now() { date '+%H:%M:%S'; }
log() { echo "[$(now)] [setup-vm] $1"; }
ok() { echo "[$(now)] [ok] $1"; }
warn() { echo "[$(now)] [wait] $1"; }
err() { echo "[$(now)] [error] $1"; }

# ── Parse flags ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vm)              VM_NAME="$2"; shift 2 ;;
    --zone)            ZONE="$2"; shift 2 ;;
    --db-pass)         DB_PASS="$2"; shift 2 ;;
    --grafana-user)    GRAFANA_USER="$2"; shift 2 ;;
    --grafana-pass)    GRAFANA_PASS="$2"; shift 2 ;;
    --discord-webhook) DISCORD_WEBHOOK="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: ./scripts/setup-vm.sh [--db-pass X] [--grafana-user X] [--grafana-pass X] [--discord-webhook URL]"
      echo ""
      echo "If flags are omitted, you will be prompted interactively."
      exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Prompt for missing values ────────────────────────────────────────────────
if [ -z "$DB_PASS" ]; then
  read -r -p "Database password: " DB_PASS
  if [ -z "$DB_PASS" ]; then
    err "Database password is required"
    exit 1
  fi
fi

if [ -z "$GRAFANA_USER" ]; then
  read -r -p "Grafana admin username [admin]: " GRAFANA_USER
  GRAFANA_USER="${GRAFANA_USER:-admin}"
fi

if [ -z "$GRAFANA_PASS" ]; then
  read -r -p "Grafana admin password: " GRAFANA_PASS
  if [ -z "$GRAFANA_PASS" ]; then
    err "Grafana password is required"
    exit 1
  fi
fi

if [ -z "$DISCORD_WEBHOOK" ]; then
  read -r -p "Discord webhook URL (or 'skip' to skip alerting): " DISCORD_WEBHOOK
  if [ "$DISCORD_WEBHOOK" = "skip" ]; then
    DISCORD_WEBHOOK="https://discord.com/api/webhooks/placeholder"
  fi
fi

log "Configuring VM: $VM_NAME (zone: $ZONE)"

# ── Generate .env content ───────────────────────────────────────────────────
ENV_CONTENT="FLASK_DEBUG=false

# --- App DB connection ---
DATABASE_NAME=hackathon_db
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=${DB_PASS}

# --- Postgres container bootstrap ---
POSTGRES_DB=hackathon_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${DB_PASS}

# --- Redis connection ---
REDIS_HOST=redis
REDIS_PORT=6379

# --- Observability credentials ---
GRAFANA_ADMIN_USER=${GRAFANA_USER}
GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASS}
DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK}
"

# ── SSH into VM and set up ───────────────────────────────────────────────────
log "Creating .env on VM"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
  cd $APP_DIR

  # Write .env
  cat > .env << 'ENVEOF'
${ENV_CONTENT}
ENVEOF

  echo '.env created.'

  echo '--- Building and starting containers ---'
  docker compose up -d --build

  echo '--- Waiting for services to be ready ---'
  for i in 1 2 3 4 5 6 7 8 9 10; do
    echo '--- Waiting for services ('"$i"'/10s) ---'
    sleep 1
  done

  echo '--- Health check ---'
  if curl -sf http://localhost/health; then
    echo ''
    echo 'Health check: PASSED'
  else
    echo 'Health check: FAILED'
    echo 'Check logs: docker compose logs app-1'
    exit 1
  fi

  echo ''
  echo '--- Readiness check ---'
  curl -sf http://localhost/ready && echo ''

  echo ''
  echo '--- Seeding demo data ---'
  curl -sf -X POST http://localhost/seed && echo ''

  echo ''
  echo '--- Container status ---'
  docker compose ps
"

# ── Get external IP for summary ──────────────────────────────────────────────
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" \
  --format='value(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "<unknown>")

echo ""
echo "============================================"
echo "  App is live!"
echo "============================================"
echo ""
echo "  App:          http://$EXTERNAL_IP"
echo "  Health:       http://$EXTERNAL_IP/health"
echo "  Users:        http://$EXTERNAL_IP/users"
echo "  Stats:        http://$EXTERNAL_IP/stats"
echo "  Grafana:      http://$EXTERNAL_IP:3000"
echo "  Prometheus:   http://$EXTERNAL_IP:9090"
echo "  Alertmanager: http://$EXTERNAL_IP:9093"
echo ""
