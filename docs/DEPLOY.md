# Deployment Guide

> All deployment is scripted. No manual commands needed.

---

## Scripts

| Script | What it does |
|--------|-------------|
| `scripts/provision.sh` | Creates GCP VM, static IP, firewall rules, installs Docker, clones repo |
| `scripts/deploy.sh` | SSHes into VM, pulls latest code, rebuilds containers, health checks |
| `scripts/deploy.sh --rollback` | Reverts last commit on VM and redeploys |

---

## First-Time Setup

```bash
# 1. Authenticate with GCP
gcloud auth login
gcloud config set project <your-project-id>

# 2. Provision the VM (idempotent — safe to re-run)
./scripts/provision.sh

# 3. SSH in, create .env, start the app
gcloud compute ssh urlpulse-vm --zone=us-central1-a
cd PE-Hackathon-Template-2026 && cp .env.example .env && nano .env
docker compose up -d --build

# 4. Set GitHub Secrets for CI deploy (values printed by provision.sh)
#    DEPLOY_HOST=<static-ip>
#    DEPLOY_USER=<ssh-user>
#    DEPLOY_KEY=<base64-ssh-key>
```

After this, every push to `main` auto-deploys via CI.

---

## Rollback

```bash
# Quick — revert last deploy
./scripts/deploy.sh --rollback

# Specific commit — SSH in
gcloud compute ssh urlpulse-vm --zone=us-central1-a
cd PE-Hackathon-Template-2026
git log --oneline -10
git revert --no-edit HEAD~N..HEAD
docker compose up -d --build
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| SSH refused | Check firewall: `gcloud compute firewall-rules list --filter=urlpulse` |
| Health check fails | `docker compose logs app-1` |
| Container won't start | Check `.env` has all required vars |
| Disk full | `docker system prune -a` |
| Permission denied | `sudo usermod -aG docker $USER` then re-login |
