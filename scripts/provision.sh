#!/usr/bin/env bash
# provision.sh — Create and configure a GCP VM for URLPulse
#
# Usage:
#   ./scripts/provision.sh                    # Use defaults
#   ./scripts/provision.sh --zone us-east1-b  # Override zone
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - A GCP project selected (gcloud config set project <project-id>)

set -euo pipefail

# ── Defaults (override via flags) ────────────────────────────────────────────
VM_NAME="urlpulse-vm"
ZONE="us-central1-a"
REGION="us-central1"
MACHINE_TYPE="e2-standard-2"
DISK_SIZE="50GB"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"
REPO_URL="https://github.com/${GITHUB_REPOSITORY:-<your-org>/PE-Hackathon-Template-2026}.git"
FIREWALL_RULE="urlpulse-allow"
IP_NAME="urlpulse-ip"

# ── Parse flags ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)       VM_NAME="$2"; shift 2 ;;
    --zone)       ZONE="$2"; REGION="${2%-*}"; shift 2 ;;
    --machine)    MACHINE_TYPE="$2"; shift 2 ;;
    --repo)       REPO_URL="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: ./scripts/provision.sh [--name vm-name] [--zone zone] [--machine type] [--repo url]"
      exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

echo "==> Provisioning URLPulse VM"
echo "    VM:      $VM_NAME"
echo "    Zone:    $ZONE"
echo "    Machine: $MACHINE_TYPE"
echo ""

# ── 1. Create VM ─────────────────────────────────────────────────────────────
echo "--- Step 1/6: Creating VM ---"
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
  echo "VM '$VM_NAME' already exists — skipping creation."
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
echo "--- Step 2/6: Reserving static IP ---"
if gcloud compute addresses describe "$IP_NAME" --region="$REGION" &>/dev/null; then
  echo "Static IP '$IP_NAME' already exists."
else
  gcloud compute addresses create "$IP_NAME" --region="$REGION"
fi

STATIC_IP=$(gcloud compute addresses describe "$IP_NAME" --region="$REGION" --format='value(address)')
echo "Static IP: $STATIC_IP"

# Attach IP to VM (delete existing access config first if needed)
gcloud compute instances delete-access-config "$VM_NAME" \
  --zone="$ZONE" --access-config-name="External NAT" 2>/dev/null || true
gcloud compute instances add-access-config "$VM_NAME" \
  --zone="$ZONE" --access-config-name="External NAT" --address="$STATIC_IP"
echo "Static IP attached to VM."

# ── 3. Firewall rules ───────────────────────────────────────────────────────
echo "--- Step 3/6: Configuring firewall ---"
if gcloud compute firewall-rules describe "$FIREWALL_RULE" &>/dev/null; then
  echo "Firewall rule '$FIREWALL_RULE' already exists."
else
  gcloud compute firewall-rules create "$FIREWALL_RULE" \
    --allow=tcp:22,tcp:80,tcp:3000,tcp:9090,tcp:9093 \
    --target-tags=urlpulse \
    --description="URLPulse: SSH, Nginx, Grafana, Prometheus, Alertmanager"
  echo "Firewall rule created."
fi

# ── 4. Install Docker on VM ─────────────────────────────────────────────────
echo "--- Step 4/6: Installing Docker on VM ---"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
  if command -v docker &>/dev/null; then
    echo 'Docker already installed.'
  else
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker \$USER
    echo 'Docker installed. Group changes applied.'
  fi

  if docker compose version &>/dev/null; then
    echo 'Docker Compose already installed.'
  else
    sudo apt-get update -qq && sudo apt-get install -y -qq docker-compose-plugin
    echo 'Docker Compose installed.'
  fi
"

# ── 5. Clone repo ───────────────────────────────────────────────────────────
echo "--- Step 5/6: Cloning repo ---"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
  if [ -d PE-Hackathon-Template-2026 ]; then
    echo 'Repo already cloned — pulling latest.'
    cd PE-Hackathon-Template-2026 && git pull
  else
    git clone $REPO_URL
  fi
"

# ── 6. Summary ───────────────────────────────────────────────────────────────
echo ""
echo "==> VM provisioned successfully!"
echo ""
echo "    VM:        $VM_NAME"
echo "    IP:        $STATIC_IP"
echo "    Zone:      $ZONE"
echo ""
echo "  Next steps:"
echo "    1. SSH in:  gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "    2. Create .env:  cd PE-Hackathon-Template-2026 && cp .env.example .env && nano .env"
echo "    3. Start:   docker compose up -d --build"
echo "    4. Verify:  curl http://$STATIC_IP/health"
echo ""
echo "  For CI deploy, add these GitHub Secrets:"
echo "    DEPLOY_HOST=$STATIC_IP"
echo "    DEPLOY_USER=<your-ssh-user>"
echo "    DEPLOY_KEY=<base64-encoded-ssh-key>"
