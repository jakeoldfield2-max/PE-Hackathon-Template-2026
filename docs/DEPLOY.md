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
#    See "GitHub Secrets for CI Deploy" below if you missed the output.
```

That's it. Every push to `main` now auto-deploys via CI.

---

## GitHub Secrets for CI Deploy

CI auto-deploy requires three GitHub Secrets (**Settings → Secrets and variables → Actions**):

| Secret | Value | Example |
|--------|-------|---------|
| `DEPLOY_HOST` | VM external IP | `34.61.209.x` |
| `DEPLOY_USER` | SSH username on the VM | `yatinkalra` |
| `DEPLOY_KEY` | Base64-encoded SSH private key | *(see below)* |

### Why you might be missing these

`provision.sh` generates the deploy key and prints all three values at the end of its run. But if you:
- **Scrolled past the output** — the values are printed once and not saved anywhere except `.keys/urlpulse-deploy-key`
- **Set up the VM manually** (e.g., via GCP Console or `gcloud` directly) — `provision.sh` was never run, so no key was generated
- **Ran `deploy.sh` locally** — local deploys use `gcloud compute ssh` which needs no secrets, so the missing secrets were never noticed until CI ran

In all these cases, CI silently skips the deploy (it exits 0 with a "Skipping deploy" message, so the job shows green even though nothing was deployed).

### Setting up DEPLOY_KEY manually

If you lost the `provision.sh` output or never ran it:

```bash
# 1. Generate a key pair (if you don't have one in .keys/)
ssh-keygen -t ed25519 -f urlpulse-deploy-key -N "" -C "urlpulse-ci-deploy"

# 2. Add the PUBLIC key to your VM
gcloud compute ssh urlpulse-vm --zone=us-central1-a --command="
  mkdir -p ~/.ssh
  echo '$(cat urlpulse-deploy-key.pub)' >> ~/.ssh/authorized_keys
"

# 3. Base64-encode the PRIVATE key and copy to clipboard
base64 < urlpulse-deploy-key | tr -d '\n' | pbcopy   # macOS
# base64 -w 0 < urlpulse-deploy-key | xclip          # Linux

# 4. Paste into GitHub → Settings → Secrets → Actions → DEPLOY_KEY
```

### Verifying secrets are working

After adding all three secrets, push to `main` (or re-run CI) and check the **Deploy via SSH** step. You should see:

```
==> Using CI deploy (SSH key)
==> Deploying to 34.61.209.x...
```

If you still see `ERROR: DEPLOY_KEY is not valid base64`, the secret value has extra whitespace or newlines — re-encode with `tr -d '\n'`.

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
| CI deploy shows green but skips | `DEPLOY_HOST`/`DEPLOY_USER`/`DEPLOY_KEY` secrets not set — see [GitHub Secrets for CI Deploy](#github-secrets-for-ci-deploy) |
| `DEPLOY_KEY is not valid base64` | Re-encode: `base64 < key \| tr -d '\n'` and re-paste into GitHub Secrets |
| CI deploys but local `deploy.sh` works | Local uses `gcloud ssh` (no secrets needed); CI needs the three secrets above |
