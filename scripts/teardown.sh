#!/usr/bin/env bash
# teardown.sh — Destroy all hosted URLPulse infrastructure on GCP
#
# Usage:
#   ./scripts/teardown.sh                              # Interactive (prompts for confirmation)
#   ./scripts/teardown.sh --project my-project-id      # Explicit project
#   ./scripts/teardown.sh --yes                        # Non-interactive (CI/automation)
#   ./scripts/teardown.sh --zone us-east1-b            # Override zone
#
# This script will:
#   1. Stop and remove all Docker containers + volumes on the VM
#   2. Delete the GCP Compute Engine VM
#   3. Release the static IP address
#   4. Delete the firewall rule
#   5. Remove local deploy keys
#
# Prerequisites: gcloud CLI installed and authenticated

set -euo pipefail

# ── Defaults (must match provision.sh) ──────────────────────────────────────
VM_NAME="urlpulse-vm"
ZONE="us-central1-a"
REGION="us-central1"
FIREWALL_RULE="urlpulse-allow"
IP_NAME="urlpulse-ip"
TARGET_PROJECT=""
ASSUME_YES="false"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m' # No Color

now() { date '+%H:%M:%S'; }
log()  { echo -e "[$(now)] [teardown] $1"; }
ok()   { echo -e "[$(now)] ${GREEN}[ok]${NC} $1"; }
warn() { echo -e "[$(now)] ${YELLOW}[warn]${NC} $1"; }
err()  { echo -e "[$(now)] ${RED}[error]${NC} $1"; }

# ── Parse flags ─────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)       VM_NAME="$2"; shift 2 ;;
    --zone)       ZONE="$2"; REGION="${2%-*}"; shift 2 ;;
    --project)    TARGET_PROJECT="$2"; shift 2 ;;
    -y|--yes)     ASSUME_YES="true"; shift ;;
    -h|--help)
      echo "Usage: ./scripts/teardown.sh [--name vm-name] [--zone zone] [--project project-id] [--yes]"
      exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Preflight: gcloud CLI ──────────────────────────────────────────────────
log "Preflight checks"

if ! command -v gcloud >/dev/null 2>&1; then
  err "gcloud CLI is not installed"
  log "Install: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

# ── Preflight: authenticated account ───────────────────────────────────────
ACTIVE_ACCOUNT=$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null || true)

if [ -z "$ACTIVE_ACCOUNT" ]; then
  err "No active gcloud account"
  log "Run: gcloud auth login"
  exit 1
fi
ok "Account: $ACTIVE_ACCOUNT"

# ── Preflight: project selection ───────────────────────────────────────────
if [ -n "$TARGET_PROJECT" ]; then
  if ! gcloud projects describe "$TARGET_PROJECT" &>/dev/null; then
    err "Cannot access project '$TARGET_PROJECT'"
    exit 1
  fi
  gcloud config set project "$TARGET_PROJECT" >/dev/null 2>&1
  ACTIVE_PROJECT="$TARGET_PROJECT"
else
  ACTIVE_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
  if [ -z "$ACTIVE_PROJECT" ] || [ "$ACTIVE_PROJECT" = "(unset)" ]; then
    err "No GCP project selected"
    log "Either pass --project <id> or run: gcloud config set project <project-id>"
    exit 1
  fi
fi
ok "Project: $ACTIVE_PROJECT"

# ── Discover what exists ───────────────────────────────────────────────────
echo ""
log "Discovering existing resources..."

VM_EXISTS="false"
IP_EXISTS="false"
FW_EXISTS="false"
KEYS_EXIST="false"

if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
  VM_EXISTS="true"
  VM_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" \
    --format='value(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || echo "unknown")
fi

if gcloud compute addresses describe "$IP_NAME" --region="$REGION" &>/dev/null; then
  IP_EXISTS="true"
  STATIC_IP=$(gcloud compute addresses describe "$IP_NAME" --region="$REGION" \
    --format='value(address)' 2>/dev/null || echo "unknown")
fi

if gcloud compute firewall-rules describe "$FIREWALL_RULE" &>/dev/null; then
  FW_EXISTS="true"
fi

if [ -d ".keys" ] && [ -f ".keys/urlpulse-deploy-key" ]; then
  KEYS_EXIST="true"
fi

# ── Show what will be destroyed ────────────────────────────────────────────
echo ""
echo -e "${RED}${BOLD}============================================${NC}"
echo -e "${RED}${BOLD}  WARNING: DESTRUCTIVE OPERATION${NC}"
echo -e "${RED}${BOLD}============================================${NC}"
echo ""
echo -e "${BOLD}The following resources will be ${RED}permanently destroyed${NC}${BOLD}:${NC}"
echo ""

if [ "$VM_EXISTS" = "true" ]; then
  echo -e "  ${RED}✖${NC} VM:           $VM_NAME (zone: $ZONE, IP: $VM_IP)"
  echo -e "                   All Docker containers, volumes, and data on this VM"
else
  echo -e "  ${YELLOW}–${NC} VM:           $VM_NAME (not found — skipping)"
fi

if [ "$IP_EXISTS" = "true" ]; then
  echo -e "  ${RED}✖${NC} Static IP:    $IP_NAME ($STATIC_IP)"
else
  echo -e "  ${YELLOW}–${NC} Static IP:    $IP_NAME (not found — skipping)"
fi

if [ "$FW_EXISTS" = "true" ]; then
  echo -e "  ${RED}✖${NC} Firewall:     $FIREWALL_RULE"
else
  echo -e "  ${YELLOW}–${NC} Firewall:     $FIREWALL_RULE (not found — skipping)"
fi

if [ "$KEYS_EXIST" = "true" ]; then
  echo -e "  ${RED}✖${NC} Deploy keys:  .keys/urlpulse-deploy-key*"
else
  echo -e "  ${YELLOW}–${NC} Deploy keys:  (not found — skipping)"
fi

echo ""
echo -e "  ${BOLD}Project:${NC}  $ACTIVE_PROJECT"
echo ""

# Check if there's nothing to destroy
if [ "$VM_EXISTS" = "false" ] && [ "$IP_EXISTS" = "false" ] && [ "$FW_EXISTS" = "false" ] && [ "$KEYS_EXIST" = "false" ]; then
  echo -e "${GREEN}No resources found to destroy. Nothing to do.${NC}"
  exit 0
fi

echo -e "${YELLOW}${BOLD}This action is IRREVERSIBLE. All data (database, cache, metrics) will be lost.${NC}"
echo ""

# ── Confirmation ───────────────────────────────────────────────────────────
if [ "$ASSUME_YES" != "true" ]; then
  read -r -p "Are you sure you want to destroy everything? (yes/no): " CONFIRM
  echo ""
  if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted. No resources were changed."
    exit 0
  fi
fi

# ── 1. Stop containers on VM (best-effort) ────────────────────────────────
if [ "$VM_EXISTS" = "true" ]; then
  echo ""
  echo "--- Step 1/4: Stopping Docker containers on VM ---"
  gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
    set -e
    if [ -d PE-Hackathon-Template-2026 ]; then
      cd PE-Hackathon-Template-2026
      echo 'Stopping all containers and removing volumes...'
      docker compose down -v --remove-orphans 2>/dev/null || true
      docker system prune -af --volumes 2>/dev/null || true
      echo 'Containers and volumes removed.'
    else
      echo 'App directory not found — skipping container cleanup.'
    fi
  " 2>/dev/null || warn "Could not SSH into VM to stop containers (continuing with VM deletion)"
else
  echo ""
  echo "--- Step 1/4: Stop containers (skipped — VM not found) ---"
fi

# ── 2. Delete VM ──────────────────────────────────────────────────────────
echo "--- Step 2/4: Deleting VM ---"
if [ "$VM_EXISTS" = "true" ]; then
  gcloud compute instances delete "$VM_NAME" --zone="$ZONE" --quiet
  ok "VM '$VM_NAME' deleted"
else
  log "VM '$VM_NAME' not found — skipping"
fi

# ── 3. Release static IP ─────────────────────────────────────────────────
echo "--- Step 3/4: Releasing static IP ---"
if [ "$IP_EXISTS" = "true" ]; then
  gcloud compute addresses delete "$IP_NAME" --region="$REGION" --quiet
  ok "Static IP '$IP_NAME' released"
else
  log "Static IP '$IP_NAME' not found — skipping"
fi

# ── 4. Delete firewall rule ──────────────────────────────────────────────
echo "--- Step 4/4: Deleting firewall rule ---"
if [ "$FW_EXISTS" = "true" ]; then
  gcloud compute firewall-rules delete "$FIREWALL_RULE" --quiet
  ok "Firewall rule '$FIREWALL_RULE' deleted"
else
  log "Firewall rule '$FIREWALL_RULE' not found — skipping"
fi

# ── 5. Remove local deploy keys ─────────────────────────────────────────
if [ "$KEYS_EXIST" = "true" ]; then
  echo ""
  log "Removing local deploy keys"
  rm -f .keys/urlpulse-deploy-key .keys/urlpulse-deploy-key.pub
  rmdir .keys 2>/dev/null || true
  ok "Deploy keys removed"
fi

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}  Teardown complete${NC}"
echo -e "${GREEN}${BOLD}============================================${NC}"
echo ""
echo "  All URLPulse infrastructure has been destroyed."
echo ""
echo "  To re-provision from scratch:"
echo "    ./scripts/provision.sh"
echo "    ./scripts/setup-vm.sh"
echo ""
