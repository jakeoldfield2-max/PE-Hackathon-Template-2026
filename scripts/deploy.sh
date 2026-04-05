#!/usr/bin/env bash
# deploy.sh — Deploy URLPulse to GCP Compute Engine
#
# Usage:
#   ./scripts/deploy.sh                              # Auto-detects: gcloud or env vars
#   ./scripts/deploy.sh --rollback                   # Rollback to previous commit
#   ./scripts/deploy.sh --vm urlpulse-vm --zone us-central1-a  # Explicit VM
#
# In CI: uses DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY env vars (GitHub Secrets)
# Locally: uses gcloud compute ssh (no env vars needed)

set -euo pipefail

APP_DIR="PE-Hackathon-Template-2026"
VM_NAME="urlpulse-vm"
ZONE="us-central1-a"
ROLLBACK="false"

now() { date '+%H:%M:%S'; }
log() { echo "[$(now)] [deploy] $1"; }
ok() { echo "[$(now)] [ok] $1"; }
warn() { echo "[$(now)] [wait] $1"; }
err() { echo "[$(now)] [error] $1"; }

sleep_with_progress() {
  local seconds="$1"
  local reason="${2:-waiting}"
  for i in $(seq 1 "$seconds"); do
    warn "$reason (${i}/${seconds}s)"
    sleep 1
  done
}

# ── Parse flags ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rollback)   ROLLBACK="true"; shift ;;
    --vm)         VM_NAME="$2"; shift 2 ;;
    --zone)       ZONE="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: ./scripts/deploy.sh [--rollback] [--vm name] [--zone zone]"
      echo ""
      echo "Locally:  uses gcloud compute ssh (no setup needed)"
      echo "In CI:    uses DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY env vars"
      exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Determine SSH method ────────────────────────────────────────────────────
if [ -n "${DEPLOY_HOST:-}" ] && [ -n "${DEPLOY_USER:-}" ] && [ -n "${DEPLOY_KEY:-}" ]; then
  # CI mode: use raw SSH with base64-encoded key
  log "Using CI deploy (SSH key)"
  SSH_KEY_FILE=$(mktemp)
  trap 'rm -f "$SSH_KEY_FILE"' EXIT

  # Validate and decode the base64 key
  if ! echo "$DEPLOY_KEY" | base64 -d > "$SSH_KEY_FILE" 2>/dev/null; then
    err "DEPLOY_KEY is not valid base64."
    log "To fix: base64 -w 0 < your_ssh_key | copy to GitHub Secret"
    warn "Skipping deploy due to invalid credentials"
    exit 0
  fi

  # Verify it looks like an SSH key
  if ! grep -q "PRIVATE KEY" "$SSH_KEY_FILE" 2>/dev/null; then
    err "DEPLOY_KEY does not appear to be an SSH private key"
    warn "Skipping deploy due to invalid credentials"
    exit 0
  fi

  chmod 600 "$SSH_KEY_FILE"
  TARGET="$DEPLOY_HOST"

  run_remote() {
    ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
      "${DEPLOY_USER}@${DEPLOY_HOST}" "$1"
  }
else
  # Local mode: use gcloud
  if ! command -v gcloud >/dev/null 2>&1; then
    err "gcloud CLI not installed and no DEPLOY_HOST/DEPLOY_USER/DEPLOY_KEY env vars set"
    log "Local: install gcloud CLI -> https://cloud.google.com/sdk/docs/install"
    log "CI: set DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY as GitHub Secrets"
    exit 1
  fi
  log "Using gcloud SSH (VM: $VM_NAME, zone: $ZONE)"
  TARGET="$VM_NAME"

  run_remote() {
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="$1"
  }
fi

# ── Rollback mode ────────────────────────────────────────────────────────────
if [ "$ROLLBACK" = "true" ]; then
  log "Rolling back on $TARGET"
  run_remote "cd $APP_DIR && git log --oneline -2 && git revert --no-edit HEAD && docker compose up -d --build"
  log "Rollback complete. Verifying health..."
  sleep_with_progress 5 "Waiting for services after rollback"
  run_remote "curl -sf http://localhost/health || echo 'WARNING: health check failed after rollback'"
  exit 0
fi

# ── Ensure VM has logging scopes (gcloud local mode only) ────────────────────
if [ -z "${DEPLOY_HOST:-}" ] && command -v gcloud >/dev/null 2>&1; then
  CURRENT_SCOPES=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" \
    --format='value(serviceAccounts[0].scopes)' 2>/dev/null || echo "")
  if ! echo "$CURRENT_SCOPES" | grep -q "logging.write"; then
    log "Adding logging/monitoring scopes to VM (requires restart)"
    gcloud compute instances stop "$VM_NAME" --zone="$ZONE" --quiet
    gcloud compute instances set-service-account "$VM_NAME" --zone="$ZONE" \
      --scopes=default,logging-write,monitoring-write --quiet
    gcloud compute instances start "$VM_NAME" --zone="$ZONE" --quiet
    sleep_with_progress 10 "Waiting for VM to restart"
  fi
  # Ensure Logging API is enabled
  if ! gcloud services list --enabled --filter="name:logging.googleapis.com" \
    --format="value(name)" 2>/dev/null | grep -q logging; then
    log "Enabling Cloud Logging API"
    gcloud services enable logging.googleapis.com
  fi
fi

# ── Deploy ───────────────────────────────────────────────────────────────────
log "Deploying to $TARGET"

run_remote "
  set -e
  cd $APP_DIR

  echo '--- Pulling latest changes ---'
  git pull origin main

  echo '--- Rebuilding and restarting containers ---'
  docker compose up -d --build --force-recreate --remove-orphans

  echo '--- Waiting for health check ---'
  for i in 1 2 3 4 5; do
    echo '--- Waiting for health check ('"$i"'/5s) ---'
    sleep 1
  done
  if curl -sf http://localhost/health > /dev/null; then
    echo 'Health check passed'
  else
    echo 'Health check FAILED — check logs with: docker compose logs app-1'
    exit 1
  fi

  echo '--- Deployment complete ---'
  docker compose ps
"

ok "Deploy to $TARGET succeeded"
