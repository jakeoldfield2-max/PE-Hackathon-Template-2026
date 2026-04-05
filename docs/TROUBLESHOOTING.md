# Troubleshooting Guide

> Diagnose and fix common issues across the full URLPulse stack.

---

## Quick Reference — Which Tool for What

| What you need | Tool | Command |
|---------------|------|---------|
| Check if containers are running | Docker | `docker compose ps` |
| View container logs | Docker | `docker compose logs <service> --tail=50` |
| Check app health | curl | `curl http://localhost/health` |
| Check DB connectivity | curl | `curl http://localhost/ready` |
| Query Prometheus metrics | Prometheus UI | `http://localhost:9090` |
| View dashboards | Grafana UI | `http://localhost:3000` |
| Check alert status | Alertmanager UI | `http://localhost:9093` |
| View GCP logs (remote) | gcloud CLI | `gcloud logging read 'resource.type="gce_instance"' --limit=10` |
| View GCP logs (browser) | GCP Console | Logs Explorer → filter `resource.type="gce_instance"` |
| Inspect container config | Docker | `docker inspect <container_name>` |
| Check VM status | gcloud CLI | `gcloud compute instances describe urlpulse-vm --zone=us-central1-a` |
| SSH into VM | gcloud CLI | `gcloud compute ssh urlpulse-vm --zone=us-central1-a` |
| Run chaos tests | Script | `./scripts/chaos.sh <test>` |
| Run load tests | k6 | `k6 run tests/load/baseline.js` |

---

## Local Development Issues

### 1. Port Binding Errors (`Address already in use`)

The stack requires ports 80, 3000, 5432, 6379, 9090, and 9093.

**Symptoms:**
```
Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Diagnose:**
```bash
# Find what's using the port
lsof -i :5432    # PostgreSQL
lsof -i :6379    # Redis
lsof -i :80      # Nginx/Apache
lsof -i :3000    # Grafana or other dev servers
```

**Fix:**
- Stop the conflicting service: `brew services stop postgresql@16`
- Or remap the port in `docker-compose.yml` (change the left side only): `"5433:5432"`

---

### 2. `uv: command not found`

**Symptoms:** `bash: uv: command not found` when running `uv sync` or `uv run`.

**Fix:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing, restart your terminal or run `source ~/.zshrc`.

---

### 3. Database Connection Refused (Non-Docker)

**Symptoms:**
```
peewee.OperationalError: connection to server at "localhost", port 5432 failed
```

**Diagnose:**
```bash
# Is PostgreSQL running?
pg_isready -h localhost -p 5432

# Does the database exist?
psql -l | grep hackathon_db
```

**Fix:**
- Ensure `.env` has `DATABASE_HOST=localhost`
- Create the database if missing: `createdb hackathon_db`
- If using Docker DB with local app, expose the port: `ports: ["5432:5432"]` in `docker-compose.yml`

---

### 4. Docker Compose Fails to Start

**Symptoms:** Containers exit immediately or enter restart loops.

**Diagnose:**
```bash
# Check which containers are failing
docker compose ps

# Check logs for the failing container
docker compose logs app-1 --tail=30
docker compose logs postgres --tail=30

# Verify .env has all required variables
grep -c "=" .env
```

**Common causes:**
- Missing `.env` file — copy from example: `cp .env.example .env`
- Missing required secrets (`POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `DISCORD_WEBHOOK_URL`)
- Stale Docker cache — rebuild: `docker compose build --no-cache`

---

### 5. Tests Fail Locally

**Symptoms:** `uv run pytest` fails with import or connection errors.

**Fix:**
```bash
# Tests use SQLite in-memory — no DB needed
# Make sure TESTING env var is NOT set to interfere
uv sync
uv run pytest tests/ -v

# If you see import errors, sync dependencies
uv sync --dev
```

---

## Observability Issues

### 6. No Logs in GCP Cloud Logging

App containers use the `gcplogs` Docker logging driver to forward logs to GCP Cloud Logging.

**Symptoms:** Logs Explorer shows "No data found".

**Diagnose step by step:**

```bash
# 1. Check the container is using gcplogs driver
docker inspect urlpulse-app-1 --format='{{.HostConfig.LogConfig.Type}}'
# Expected: gcplogs

# 2. Check VM has logging scopes
gcloud compute instances describe urlpulse-vm --zone=us-central1-a \
  --format='value(serviceAccounts[0].scopes)' | tr ';' '\n' | grep logging
# Expected: https://www.googleapis.com/auth/logging.write

# 3. Check Logging API is enabled
gcloud services list --enabled --filter="name:logging.googleapis.com"
# Expected: logging.googleapis.com listed

# 4. Verify logs are arriving
gcloud logging read 'resource.type="gce_instance"' --limit=5 --freshness=10m
```

**Fix by cause:**

| Cause | Fix |
|-------|-----|
| Container using `json-file` driver | Recreate: `docker compose up -d --force-recreate app-1 app-2 app-3` |
| VM missing `logging-write` scope | Re-deploy: `./scripts/deploy.sh` (auto-adds scopes, restarts VM once) |
| Logging API not enabled | `gcloud services enable logging.googleapis.com` |
| Wrong filter in Logs Explorer | Use `resource.type="gce_instance"` not `"global"` |

**Correct Logs Explorer query:**
```
resource.type="gce_instance"
logName="projects/pe-hackathon-template-2026/logs/gcplogs-docker-driver"
```

**Note:** With the `gcplogs` driver, `docker compose logs` will not show output locally on the VM. Use GCP Logs Explorer or `gcloud logging read` instead.

---

### 7. Prometheus Targets Down

**Symptoms:** `http://localhost:9090/targets` shows app targets as DOWN.

**Diagnose:**
```bash
# Are containers running?
docker compose ps

# Can Prometheus reach the apps internally?
docker exec urlpulse-prometheus wget -qO- http://app-1:5000/metrics | head -5

# Check Prometheus config
docker exec urlpulse-prometheus cat /etc/prometheus/prometheus.yml
```

**Fix:**
- If containers are restarting: check `docker compose logs <service>` for errors
- If Prometheus can't reach apps: ensure they're on the same Docker network (`docker network ls`)
- If config is wrong: edit `prometheus/prometheus.yml` and reload: `curl -X POST http://localhost:9090/-/reload`

---

### 8. Grafana "No Data" on Dashboards

**Symptoms:** Dashboards load but all panels show "No data".

**Diagnose:**
```bash
# 1. Is Prometheus scraping?
# Visit http://localhost:9090/targets — all should be UP

# 2. Does Prometheus have data?
# Visit http://localhost:9090/graph, query: http_requests_total
# If empty, generate traffic:
curl http://localhost/health
curl http://localhost/users
curl http://localhost/stats

# 3. Is the Grafana data source correct?
# Grafana → Settings (gear icon) → Data Sources → Prometheus
# URL should be: http://prometheus:9090 (internal Docker hostname)
```

**Fix:**
- Wrong data source URL: change from `http://localhost:9090` to `http://prometheus:9090`
- No metrics yet: generate traffic, then wait 15s for Prometheus to scrape
- Dashboard provisioning failed: restart Grafana: `docker compose restart grafana`

---

### 9. Discord Alerts Not Firing

**Symptoms:** Chaos tests trigger alerts but no Discord messages appear.

**Diagnose:**
```bash
# 1. Is Alertmanager receiving alerts?
# Visit http://localhost:9093 — check if alerts show as "firing"

# 2. Is the webhook adapter running?
docker compose logs discord-webhook --tail=20

# 3. Is the webhook URL valid?
grep DISCORD_WEBHOOK_URL .env

# 4. Test the webhook directly
curl -X POST "$(grep DISCORD_WEBHOOK_URL .env | cut -d= -f2)" \
  -H 'Content-Type: application/json' \
  -d '{"content":"Test alert from URLPulse"}'
```

**Fix:**
- `DISCORD_WEBHOOK_URL` set to placeholder: create a real webhook in Discord (Server Settings → Integrations → Webhooks)
- Webhook adapter crashed: `docker compose restart discord-webhook`
- Alertmanager not routing: check `alertmanager/alertmanager.yml` has the correct `webhook_configs` URL

---

## Deployment Issues

### 10. `gcloud: command not found`

**Fix:**
```bash
# macOS
brew install google-cloud-sdk

# Or official installer
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

---

### 11. `No active gcloud account`

**Symptoms:** `provision.sh` or `deploy.sh` fails immediately.

**Fix:**
```bash
gcloud auth login
gcloud config set project pe-hackathon-template-2026
```

---

### 12. SSH Connection Refused to VM

**Diagnose:**
```bash
# Is the VM running?
gcloud compute instances describe urlpulse-vm --zone=us-central1-a \
  --format='value(status)'

# Are firewall rules in place?
gcloud compute firewall-rules list --filter=urlpulse

# Try SSH directly
gcloud compute ssh urlpulse-vm --zone=us-central1-a
```

**Fix:**
- VM stopped: `gcloud compute instances start urlpulse-vm --zone=us-central1-a`
- No firewall rule: re-run `./scripts/provision.sh` (idempotent — skips existing resources)
- SSH key issues: `gcloud compute os-login ssh-keys add --key-file=~/.ssh/id_ed25519.pub`

---

### 13. CI Deploy Shows Green but Nothing Deployed

**Symptoms:** GitHub Actions job succeeds but code on VM is outdated.

**Cause:** Missing GitHub Secrets. CI silently skips the deploy when `DEPLOY_HOST`, `DEPLOY_USER`, or `DEPLOY_KEY` are not set.

**Fix:** See [DEPLOY.md — GitHub Secrets for CI Deploy](DEPLOY.md#github-secrets-for-ci-deploy).

---

### 14. Health Check Fails After Deploy

**Diagnose:**
```bash
# SSH into VM
gcloud compute ssh urlpulse-vm --zone=us-central1-a

# Check containers
cd PE-Hackathon-Template-2026
docker compose ps
docker compose logs app-1 --tail=30

# Check if .env is present and complete
wc -l .env
grep DATABASE_PASSWORD .env
```

**Fix:**
- Missing `.env`: re-run `./scripts/setup-vm.sh`
- Bad code: rollback with `./scripts/deploy.sh --rollback`
- Disk full: `docker system prune -a` (removes unused images/containers)

---

### 15. Docker Permission Denied on VM

**Symptoms:** `Got permission denied while trying to connect to the Docker daemon socket`

**Fix:**
```bash
sudo usermod -aG docker $USER
newgrp docker
# Or log out and log back in
```

---

## Performance Issues

### 16. High Latency on Responses

**Diagnose:**
```bash
# Check Prometheus for p99 latency
# Visit http://localhost:9090/graph
# Query: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Check if Redis is working (cache miss = slower)
curl -I http://localhost/users
# Look for X-Cache: HIT vs MISS header

# Check if containers are resource-starved
docker stats --no-stream
```

**Fix:**
- Redis down: `docker compose restart redis`
- Too many workers: adjust `--workers` in Dockerfile (default: 4 per instance)
- DB queries slow: check `docker compose logs postgres` for slow query warnings

---

### 17. High Memory Usage Alert

**Diagnose:**
```bash
# Check which container is using memory
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

# Check if it's the chaos memory hog endpoint
curl http://localhost/health
```

**Fix:**
- After chaos tests: restart affected container: `docker compose restart app-1`
- Persistent high memory: check for memory leaks in application logs
- Redis over limit: Redis auto-evicts with `allkeys-lru` policy (configured in `docker-compose.yml`)

---

## Related Documentation

| Doc | What it covers |
|-----|---------------|
| [DEPLOY.md](DEPLOY.md) | GCP VM setup, CI deploy, GitHub Secrets, rollback |
| [DECISIONS.md](DECISIONS.md) | Technical choices with rationale (GCP, Nginx, Redis, etc.) |
| [LOAD_AND_CHAOS.md](LOAD_AND_CHAOS.md) | Load testing tiers, chaos tests, demo order |
| [CAPACITY.md](CAPACITY.md) | Load test results, bottleneck analysis, scaling roadmap |
| [FAILURE_MODES.md](FAILURE_MODES.md) | What breaks, impact, auto-recovery behavior |
| [INCIDENT_POSTMORTEM.md](INCIDENT_POSTMORTEM.md) | INC-001: Redis OOM cache miss storm |
| [FEATURES.md](FEATURES.md) | Every feature mapped to its hackathon quest |
| [runbooks/](runbooks/) | Step-by-step runbooks for each alert type |
