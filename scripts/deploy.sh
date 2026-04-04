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
  echo "==> Using CI deploy (SSH key)"
  SSH_KEY_FILE=$(mktemp)
  trap 'rm -f "$SSH_KEY_FILE"' EXIT
  echo "$DEPLOY_KEY" | base64 -d > "$SSH_KEY_FILE"
  chmod 600 "$SSH_KEY_FILE"
  TARGET="$DEPLOY_HOST"

  run_remote() {
    ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
      "${DEPLOY_USER}@${DEPLOY_HOST}" "$1"
  }
else
  # Local mode: use gcloud
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "ERROR: gcloud CLI not installed and no DEPLOY_HOST/DEPLOY_USER/DEPLOY_KEY env vars set."
    echo ""
    echo "Local:  install gcloud CLI → https://cloud.google.com/sdk/docs/install"
    echo "CI:     set DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY as GitHub Secrets"
    exit 1
  fi
  echo "==> Using gcloud SSH (VM: $VM_NAME, zone: $ZONE)"
  TARGET="$VM_NAME"

  run_remote() {
    gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="$1"
  }
fi

# ── Rollback mode ────────────────────────────────────────────────────────────
if [ "$ROLLBACK" = "true" ]; then
  echo "==> Rolling back on $TARGET..."
  run_remote "cd $APP_DIR && git log --oneline -2 && git revert --no-edit HEAD && docker compose up -d --build"
  echo "==> Rollback complete. Verifying health..."
  sleep 5
  run_remote "curl -sf http://localhost/health || echo 'WARNING: health check failed after rollback'"
  exit 0
fi

# ── Deploy ───────────────────────────────────────────────────────────────────
echo "==> Deploying to $TARGET..."

run_remote "
  set -e
  cd $APP_DIR

  echo '--- Pulling latest changes ---'
  git pull origin main

  echo '--- Rebuilding and restarting containers ---'
  docker compose up -d --build --remove-orphans

  echo '--- Waiting for health check ---'
  sleep 5
  if curl -sf http://localhost/health > /dev/null; then
    echo 'Health check passed'
  else
    echo 'Health check FAILED — check logs with: docker compose logs app-1'
    exit 1
  fi

  echo '--- Deployment complete ---'
  docker compose ps
"

echo "==> Deploy to $TARGET succeeded."
