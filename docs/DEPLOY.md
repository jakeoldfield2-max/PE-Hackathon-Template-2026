# Deployment Guide

> Fully scripted. No manual GCP Console steps needed.

---

## Scripts

| Script | What it does |
|--------|-------------|
| `scripts/provision.sh` | Creates VM, static IP, firewall, installs Docker, clones repo, generates CI deploy key |
| `scripts/setup-vm.sh` | Creates `.env`, starts containers, seeds data, verifies health |
| `scripts/deploy.sh` | SSHes into VM, pulls latest, rebuilds containers, runs health check |
| `scripts/deploy.sh --rollback` | Reverts last commit on VM and redeploys |

---

## First-Time Setup

```bash
# 1. Provision (validates account, project, billing, APIs — then creates everything)
./scripts/provision.sh --project <your-project-id>

# 2. Set up .env, start the app, seed data (prompts for passwords)
./scripts/setup-vm.sh

# 3. Add the GitHub Secrets printed by provision.sh (DEPLOY_HOST, DEPLOY_USER, DEPLOY_KEY)
```

That's it. Every push to `main` now auto-deploys via CI.

---

## What provision.sh validates before creating anything

1. `gcloud` CLI is installed
2. An active GCP account exists (`gcloud auth login`)
3. Project exists and you have access
4. Billing is enabled on the project
5. Compute Engine API is enabled (auto-enables if not)
6. Repo URL is resolvable (auto-detects from git remote)
7. Asks for confirmation before creating resources (skip with `--yes`)

---

## Rollback

```bash
./scripts/deploy.sh --rollback            # Revert last deploy

# Or for a specific commit:
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
| `No active gcloud account` | `gcloud auth login` |
| `Billing is not enabled` | Enable at console.cloud.google.com/billing |
| SSH refused | `gcloud compute firewall-rules list --filter=urlpulse` |
| Health check fails | `docker compose logs app-1` |
| Container won't start | Check `.env` has all required vars |
| Disk full | `docker system prune -a` |
| Docker permission denied | Re-login or `newgrp docker` |
