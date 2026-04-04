#!/usr/bin/env bash
# provision.sh — Create and configure a GCP VM for URLPulse
#
# Usage:
#   ./scripts/provision.sh                              # Interactive (prompts for confirmation)
#   ./scripts/provision.sh --project my-project-id      # Explicit project
#   ./scripts/provision.sh --yes                        # Non-interactive (CI/automation)
#   ./scripts/provision.sh --zone us-east1-b            # Override zone
#
# Prerequisites: gcloud CLI installed and authenticated

set -euo pipefail

# ── Defaults (override via flags) ────────────────────────────────────────────
VM_NAME="urlpulse-vm"
ZONE="us-central1-a"
REGION="us-central1"
MACHINE_TYPE="e2-standard-2"
DISK_SIZE="50GB"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
REPO_URL=""
FIREWALL_RULE="urlpulse-allow"
IP_NAME="urlpulse-ip"
TARGET_PROJECT=""
ASSUME_YES="false"

# ── Parse flags ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)       VM_NAME="$2"; shift 2 ;;
    --zone)       ZONE="$2"; REGION="${2%-*}"; shift 2 ;;
    --machine)    MACHINE_TYPE="$2"; shift 2 ;;
    --repo)       REPO_URL="$2"; shift 2 ;;
    --project)    TARGET_PROJECT="$2"; shift 2 ;;
    -y|--yes)     ASSUME_YES="true"; shift ;;
    -h|--help)
      echo "Usage: ./scripts/provision.sh [--name vm-name] [--zone zone] [--machine type] [--repo url] [--project project-id] [--yes]"
      exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Preflight: gcloud CLI ───────────────────────────────────────────────────
echo "==> Preflight checks"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud CLI is not installed."
  echo "Install: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

# ── Preflight: authenticated account ────────────────────────────────────────
ACTIVE_ACCOUNT=$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null || true)

if [ -z "$ACTIVE_ACCOUNT" ]; then
  echo "ERROR: No active gcloud account."
  echo "Run:  gcloud auth login"
  exit 1
fi
echo "  Account: $ACTIVE_ACCOUNT"

# ── Preflight: project selection ─────────────────────────────────────────────
if [ -n "$TARGET_PROJECT" ]; then
  # Verify the project exists and user has access
  if ! gcloud projects describe "$TARGET_PROJECT" &>/dev/null; then
    echo "ERROR: Cannot access project '$TARGET_PROJECT'."
    echo "Check the project ID and your permissions."
    exit 1
  fi
  gcloud config set project "$TARGET_PROJECT" >/dev/null 2>&1
  ACTIVE_PROJECT="$TARGET_PROJECT"
else
  ACTIVE_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
  if [ -z "$ACTIVE_PROJECT" ] || [ "$ACTIVE_PROJECT" = "(unset)" ]; then
    echo ""
    echo "ERROR: No GCP project selected."
    echo "Either pass --project <id> or run:  gcloud config set project <project-id>"
    echo ""
    echo "Your available projects:"
    gcloud projects list --format="table(projectId, name)" 2>/dev/null || true
    exit 1
  fi
fi
echo "  Project: $ACTIVE_PROJECT"

# ── Preflight: billing enabled ───────────────────────────────────────────────
BILLING_ENABLED=$(gcloud billing projects describe "$ACTIVE_PROJECT" --format="value(billingEnabled)" 2>/dev/null || echo "unknown")
if [ "$BILLING_ENABLED" = "False" ]; then
  echo ""
  echo "ERROR: Billing is not enabled for project '$ACTIVE_PROJECT'."
  echo "Enable billing: https://console.cloud.google.com/billing/linkedaccount?project=$ACTIVE_PROJECT"
  exit 1
elif [ "$BILLING_ENABLED" = "unknown" ]; then
  echo "  Billing: could not verify (may lack billing viewer role — continuing)"
else
  echo "  Billing: enabled"
fi

# ── Preflight: Compute Engine API ────────────────────────────────────────────
if ! gcloud services list --enabled --filter="name:compute.googleapis.com" --format="value(name)" 2>/dev/null | grep -q compute; then
  echo "  Compute API not enabled — enabling now..."
  gcloud services enable compute.googleapis.com
fi
echo "  Compute API: enabled"

# ── Preflight: resolve repo URL ──────────────────────────────────────────────
if [ -z "$REPO_URL" ]; then
  REPO_URL=$(git remote get-url origin 2>/dev/null || true)
fi

if [ -z "$REPO_URL" ]; then
  echo ""
  echo "ERROR: No repo URL found."
  echo ""
  echo "Pass it via --repo flag:"
  echo "  ./scripts/provision.sh --repo https://github.com/your-org/PE-Hackathon-Template-2026.git"
  echo ""
  echo "Or run this script from inside the cloned repo (auto-detects from git remote)."
  exit 1
fi

# Convert SSH URL to HTTPS (VM won't have GitHub SSH keys)
if [[ "$REPO_URL" == git@github.com:* ]]; then
  REPO_URL="https://github.com/${REPO_URL#git@github.com:}"
  echo "  Repo: $REPO_URL (converted from SSH to HTTPS)"
else
  echo "  Repo: $REPO_URL"
fi

echo ""

# ── Confirmation ─────────────────────────────────────────────────────────────
echo "==> Will provision:"
echo "    VM:       $VM_NAME ($MACHINE_TYPE, $DISK_SIZE)"
echo "    Zone:     $ZONE"
echo "    Firewall: ports 22, 80, 3000, 9090, 9093"
echo "    Project:  $ACTIVE_PROJECT"
echo ""

if [ "$ASSUME_YES" != "true" ]; then
  read -r -p "Proceed? (yes/no): " CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted. No resources were changed."
    exit 0
  fi
fi

# ── 1. Create VM ─────────────────────────────────────────────────────────────
echo ""
echo "--- Step 1/7: Creating VM ---"
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
  echo "VM '$VM_NAME' already exists — skipping."
else
  gcloud compute instances create "$VM_NAME" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="$IMAGE_FAMILY" \
    --image-project="$IMAGE_PROJECT" \
    --boot-disk-size="$DISK_SIZE" \
    --zone="$ZONE" \
    --tags=urlpulse
  echo "VM created."
fi

# ── 2. Reserve static IP ────────────────────────────────────────────────────
echo "--- Step 2/7: Reserving static IP ---"
if gcloud compute addresses describe "$IP_NAME" --region="$REGION" &>/dev/null; then
  echo "Static IP '$IP_NAME' already exists."
else
  gcloud compute addresses create "$IP_NAME" --region="$REGION"
fi

STATIC_IP=$(gcloud compute addresses describe "$IP_NAME" --region="$REGION" --format='value(address)')
echo "Static IP: $STATIC_IP"

# Attach static IP to VM (remove any existing access config first)
CURRENT_ACCESS=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" \
  --format='value(networkInterfaces[0].accessConfigs[0].name)' 2>/dev/null || true)
if [ -n "$CURRENT_ACCESS" ]; then
  gcloud compute instances delete-access-config "$VM_NAME" \
    --zone="$ZONE" --access-config-name="$CURRENT_ACCESS" 2>/dev/null || true
fi
gcloud compute instances add-access-config "$VM_NAME" \
  --zone="$ZONE" --access-config-name="External NAT" --address="$STATIC_IP"
echo "Static IP attached."

# ── 3. Firewall rules ───────────────────────────────────────────────────────
echo "--- Step 3/7: Configuring firewall ---"
if gcloud compute firewall-rules describe "$FIREWALL_RULE" &>/dev/null; then
  echo "Firewall rule '$FIREWALL_RULE' already exists."
else
  gcloud compute firewall-rules create "$FIREWALL_RULE" \
    --allow=tcp:22,tcp:80,tcp:3000,tcp:9090,tcp:9093 \
    --target-tags=urlpulse \
    --description="URLPulse: SSH, Nginx, Grafana, Prometheus, Alertmanager"
  echo "Firewall rule created."
fi

# ── 4. Wait for VM to be ready ──────────────────────────────────────────────
echo "--- Step 4/7: Waiting for VM SSH to be ready ---"
for i in $(seq 1 12); do
  if gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="echo ok" 2>/dev/null; then
    break
  fi
  if [ "$i" -eq 12 ]; then
    echo "ERROR: VM SSH not ready after 60s. Check the VM in GCP Console."
    exit 1
  fi
  echo "  Waiting for SSH... (attempt $i/12)"
  sleep 5
done

# ── 5. Install Docker on VM ─────────────────────────────────────────────────
echo "--- Step 5/7: Installing Docker ---"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command='
  set -e
  if command -v docker >/dev/null 2>&1; then
    echo "Docker already installed: $(docker --version)"
  else
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed."
  fi

  if docker compose version >/dev/null 2>&1; then
    echo "Docker Compose already installed: $(docker compose version)"
  else
    echo "Installing Docker Compose plugin..."
    sudo apt-get update -qq && sudo apt-get install -y -qq docker-compose-plugin
    echo "Docker Compose installed."
  fi
'

# ── 6. Clone repo + validate Docker works ────────────────────────────────────
echo "--- Step 6/7: Cloning repo and validating Docker ---"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
  set -e

  # Clone or pull
  if [ -d PE-Hackathon-Template-2026 ]; then
    echo 'Repo already cloned — pulling latest.'
    cd PE-Hackathon-Template-2026 && git pull
  else
    git clone $REPO_URL
  fi

  # Validate docker works (newgrp to pick up docker group without re-login)
  if ! docker info >/dev/null 2>&1; then
    echo 'Activating docker group...'
    sg docker -c 'docker info >/dev/null 2>&1' || {
      echo 'WARNING: Docker group not yet active. You may need to SSH in manually and run: newgrp docker'
    }
  else
    echo 'Docker access: OK'
  fi
"

# ── 7. Generate SSH key for CI deploy ────────────────────────────────────────
echo "--- Step 7/7: CI deploy key ---"
KEYS_DIR=".keys"
DEPLOY_KEY_FILE="$KEYS_DIR/urlpulse-deploy-key"
mkdir -p "$KEYS_DIR"

if [ -f "$DEPLOY_KEY_FILE" ]; then
  echo "Deploy key '$DEPLOY_KEY_FILE' already exists — skipping generation."
else
  ssh-keygen -t ed25519 -f "$DEPLOY_KEY_FILE" -N "" -C "urlpulse-ci-deploy" >/dev/null 2>&1
  echo "Generated deploy key: $DEPLOY_KEY_FILE"

  # Add public key to VM authorized_keys
  PUBKEY=$(cat "${DEPLOY_KEY_FILE}.pub")
  gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
    mkdir -p ~/.ssh
    if ! grep -q 'urlpulse-ci-deploy' ~/.ssh/authorized_keys 2>/dev/null; then
      echo '$PUBKEY' >> ~/.ssh/authorized_keys
      echo 'Deploy key added to VM.'
    else
      echo 'Deploy key already in authorized_keys.'
    fi
  "
fi

DEPLOY_KEY_B64=$(base64 < "$DEPLOY_KEY_FILE" | tr -d '\n')
SSH_USER=$(gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="whoami" 2>/dev/null || echo "<ssh-user>")

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  VM provisioned successfully!"
echo "============================================"
echo ""
echo "  VM:      $VM_NAME"
echo "  IP:      $STATIC_IP"
echo "  Zone:    $ZONE"
echo "  Project: $ACTIVE_PROJECT"
echo ""
echo "  Next steps:"
echo "    1. SSH in and create .env:"
echo "       gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "       cd PE-Hackathon-Template-2026 && cp .env.example .env && nano .env"
echo ""
echo "    2. Start the app:"
echo "       docker compose up -d --build"
echo "       curl http://$STATIC_IP/health"
echo ""
echo "    3. Add these GitHub Secrets (Settings → Secrets → Actions):"
echo "       DEPLOY_HOST=$STATIC_IP"
echo "       DEPLOY_USER=$SSH_USER"
echo "       DEPLOY_KEY=$DEPLOY_KEY_B64"
echo ""
echo "  After adding secrets, every push to main auto-deploys via CI."
echo ""
