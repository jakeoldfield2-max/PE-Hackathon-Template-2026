#!/usr/bin/env bash
# deploy.sh — Deploy URLPulse to GCP Compute Engine via SSH
#
# Usage:
#   ./scripts/deploy.sh                  # Deploy latest main
#   ./scripts/deploy.sh --rollback       # Rollback to previous commit
#
# Required env vars: DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY (base64-encoded)
# These should be set as GitHub Secrets for CI usage.

set -euo pipefail

APP_DIR="PE-Hackathon-Template-2026"
COMPOSE="docker compose"

# ── Validate required environment variables ──────────────────────────────────
for var in DEPLOY_HOST DEPLOY_USER DEPLOY_KEY; do
  if [ -z "${!var:-}" ]; then
    echo "ERROR: $var is not set. See docs/DEPLOY.md for setup instructions."
    exit 1
  fi
done

# ── Setup SSH key from base64-encoded secret ─────────────────────────────────
SSH_KEY_FILE=$(mktemp)
trap 'rm -f "$SSH_KEY_FILE"' EXIT
echo "$DEPLOY_KEY" | base64 -d > "$SSH_KEY_FILE"
chmod 600 "$SSH_KEY_FILE"

SSH_CMD="ssh -i $SSH_KEY_FILE -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${DEPLOY_USER}@${DEPLOY_HOST}"

# ── Rollback mode ────────────────────────────────────────────────────────────
if [ "${1:-}" = "--rollback" ]; then
  echo "==> Rolling back to previous commit..."
  $SSH_CMD "cd $APP_DIR && git log --oneline -2 && git revert --no-edit HEAD && $COMPOSE up -d --build"
  echo "==> Rollback complete. Verifying health..."
  sleep 5
  $SSH_CMD "curl -sf http://localhost/health || echo 'WARNING: health check failed after rollback'"
  exit 0
fi

# ── Deploy latest main ───────────────────────────────────────────────────────
echo "==> Deploying to ${DEPLOY_HOST}..."

$SSH_CMD bash <<'REMOTE'
set -euo pipefail
cd PE-Hackathon-Template-2026

echo "--- Pulling latest changes ---"
git pull origin main

echo "--- Rebuilding and restarting containers ---"
docker compose up -d --build --remove-orphans

echo "--- Waiting for health check ---"
sleep 5
if curl -sf http://localhost/health > /dev/null; then
  echo "✓ Health check passed"
else
  echo "✗ Health check FAILED — check logs with: docker compose logs app-1"
  exit 1
fi

echo "--- Deployment complete ---"
docker compose ps
REMOTE

echo "==> Deploy to ${DEPLOY_HOST} succeeded."
