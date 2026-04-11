# URLPulse — Production-Grade URL Shortener

> **MLH Production Engineering Hackathon 2026**

A production-grade URL shortener built to survive chaos. Shorten URLs, track events, and prove your system can handle load, recover from failures, and alert when things break.

## Tech Stack

| Layer | Technology | Why | Default Access |
|-------|-----------|-----|----------------|
| **Language** | Python 3.13 | Template default, team familiarity | N/A |
| **Framework** | Flask | Lightweight, hackathon-friendly | Local: http://localhost:5000 |
| **ORM** | Peewee | Simple, DatabaseProxy pattern for connection pooling | N/A |
| **Database** | PostgreSQL 16 | Production-grade relational DB | Internal: 5432 |
| **Cache** | Redis 7 | In-memory caching with TTL & LRU eviction | Internal: 6379 |
| **WSGI Server** | Gunicorn | Multi-worker concurrent request handling | Internal app port: 5000 |
| **Load Balancer** | Nginx | Round-robin across 3 app instances | Docker API: http://localhost (80) |
| **Containerization** | Docker + Docker Compose | Full stack orchestration | `docker compose up -d --build` |
| **Metrics** | Prometheus | Scrapes /metrics, stores time-series data | http://localhost:9090 |
| **Dashboards** | Grafana | Four Golden Signals visualization | http://localhost:3000 |
| **Alerting** | Alertmanager → Discord | Automated incident notifications | Alertmanager UI: http://localhost:9093 |
| **CI/CD** | GitHub Actions | Test → Build → Deploy pipeline | GitHub Actions tab |
| **Infrastructure** | GCP VM + Docker Compose | Reproducible cloud deployment | Cloud VM |
| **Load Testing** | k6 | Scriptable load tests (50/200/500 users) | CLI |
| **Package Manager** | uv | Fast Python dependency management | CLI |

## Architecture

```
Internet
   │
   ▼
┌─────────┐
│  Nginx  │  :80  (round-robin load balancer)
└────┬────┘
     │
     ├──────────────┬──────────────┐
     ▼              ▼              ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│  App 1  │  │  App 2  │  │  App 3  │  Flask + Gunicorn
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     ▼            ▼            ▼
┌─────────┐  ┌─────────┐
│ Postgres │  │  Redis  │
│   :5432  │  │  :6379  │
└──────────┘  └─────────┘

Observability:
  Prometheus (:9090) → Grafana (:3000) → Alertmanager (:9093) → Discord
```

## Data Model

- **User** — username, email, created_at
- **Url** — linked to a User, short_code (unique), original_url, title, is_active, timestamps
- **Event** — linked to both Url and User, event_type (created/updated/deleted), details (JSON)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check — is the process alive? |
| `GET` | `/ready` | Readiness check — is the DB connected? |
| `GET` | `/stats` | System overview (users, URLs, events) |
| `POST` | `/seed` | Populate demo data (idempotent) |
| `POST` | `/users` | Create a user |
| `GET` | `/users` | List all users |
| `GET` | `/users/<id>` | Get user by ID |
| `POST` | `/users/bulk` | Bulk-create users from CSV or JSON payload |
| `PUT` | `/users/<id>` | Update a user |
| `DELETE` | `/users/<id>` | Delete a user |
| `GET` | `/urls` | List URLs, optionally filtered by user or active status |
| `POST` | `/urls` | Create a shortened URL |
| `GET` | `/urls/<id>` | Get URL by ID |
| `PUT` | `/urls/<id>` | Update a URL |
| `DELETE` | `/urls/<id>` | Delete a URL |
| `GET` | `/s/<short_code>` | Redirect to the original URL |
| `GET` | `/s/<short_code>/info` | Inspect a short URL without redirecting |
| `GET` | `/s/<short_code>/stats` | Get click statistics for a short URL |

## Quick Start (Docker)

```bash
# 1. Configure environment
cp .env.example .env
# Edit placeholders in .env using the Common Standard profile values.
# Required: DATABASE_PASSWORD, POSTGRES_PASSWORD,
#           GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD, DISCORD_WEBHOOK_URL
# Docker startup fails fast when required secrets are missing.

# 2. Start backend (3 app instances, Nginx, PostgreSQL, Redis, Prometheus, Grafana)
docker compose up -d --build

# 3. Seed demo data
curl -X POST http://localhost/seed

# 4. Start frontend (Streamlit UI — runs outside Docker)
uv run streamlit run app/ui_app.py
# UI opens at http://localhost:8501

# 5. Verify backend
curl http://localhost/health    # → {"status":"ok"}
curl http://localhost/ready     # → {"status":"ready","database":"connected"}
curl http://localhost/stats     # → {"total_users":3,"total_urls":10,...}
curl http://localhost/users     # → cached response (check X-Cache header)
curl -X POST http://localhost/urls \
     -H 'Content-Type: application/json' \
     -d '{"user_id":1,"original_url":"https://example.com","title":"Example"}'
```

| Service | URL |
|---------|-----|
| Backend API (via Nginx) | http://localhost |
| Streamlit UI | http://localhost:8501 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |

## Security Notes

- Do not hardcode passwords, tokens, or webhook URLs in code or docker-compose.
- Keep all secrets in .env (already ignored by git) and treat .env.example as schema only.
- Rotate any secret immediately if it was ever committed or shared.

## Environment Standard

- Single env schema: one shared .env.example used by all environments.
- Docker-first defaults: the baseline values work for docker compose without uncommenting blocks.
- Minimal overrides: for local run, only override host values; for Supabase, replace DATABASE_* values.
- Fail fast on required secrets: compose requires POSTGRES_PASSWORD, GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD, and DISCORD_WEBHOOK_URL.

## Running Locally (No Docker)

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Override these values in .env:
#   DATABASE_HOST=localhost
#   REDIS_HOST=localhost
# For Supabase, replace DATABASE_* values with Supabase credentials.
# For local PostgreSQL:
#   brew install postgresql@16 && brew services start postgresql@16
#   createdb hackathon_db

# 3. Start backend API
uv run run.py
# Backend starts at http://localhost:5000

# 4. Start frontend (in a separate terminal)
uv run streamlit run app/ui_app.py
# UI opens at http://localhost:8501

# 5. Verify
curl http://localhost:5000/health   # → {"status":"ok"}
```

## Running Tests

```bash
# Run all tests (uses SQLite in-memory — no DB needed)
uv run pytest tests/ -v

# Run with coverage (70% minimum required for CI)
uv run pytest tests/ --cov=app --cov-fail-under=70
```

## Project Structure

```
urlpulse/
├── app/
│   ├── __init__.py          # App factory + health/ready/error handlers
│   ├── cache.py             # Redis caching with graceful degradation
│   ├── database.py          # DB connection + BaseModel
│   ├── ui_app.py            # Streamlit frontend (run separately)
│   ├── ui/                  # Streamlit components (sidebar, tabs, styles)
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── url.py           # Url model
│   │   └── event.py         # Event model
│   └── routes/
│       ├── seed.py          # POST /seed — demo data
│       ├── stats.py         # GET /stats — system overview
│       ├── users.py         # User CRUD (cached)
│       ├── urls.py          # URL CRUD + listing
│       └── url_actions/     # URL shortening, redirect, and legacy compatibility
├── nginx/
│   └── nginx.conf           # Round-robin load balancer config
├── tests/                   # pytest suite (SQLite in-memory)
├── scripts/
│   ├── provision.sh         # One-time GCP VM setup (idempotent)
│   ├── setup-vm.sh          # Create .env, start app, seed data on VM
│   ├── deploy.sh            # SSH deploy to GCP VM (+ rollback)
│   ├── teardown.sh          # Destroy all hosted infrastructure
│   └── chaos.sh             # Chaos engineering (kill instances, DB, Redis)
├── docs/                    # Architecture, decisions, deploy guide, runbooks
├── .env.example             # Common env schema (Docker baseline + minimal overrides)
├── Dockerfile               # Python 3.13 + Gunicorn
├── docker-compose.yml       # Full stack (3 apps, Nginx, PG, Redis)
├── pyproject.toml
├── run.py
└── README.md
```

## Deployment

```bash
./scripts/provision.sh --project pe-hackathon-template-2026  # Create VM, firewall, Docker
./scripts/setup-vm.sh              # Create .env, start app, seed data (prompts for secrets)
./scripts/deploy.sh                # Deploy latest main via SSH
./scripts/deploy.sh --rollback     # Revert last deploy
./scripts/teardown.sh              # Destroy all hosted infrastructure (VM, IP, firewall, keys)
```

CI auto-deploys on merge to `main` (blocked unless tests + docker-build pass).
See [docs/DEPLOY.md](docs/DEPLOY.md) for first-time setup and troubleshooting.


## Troubleshooting

Common issues and quick fixes. For the full guide with diagnostic commands and step-by-step fixes, see **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**.

| # | Issue | Quick Fix |
|---|-------|-----------|
| 1 | **Port already in use** | `lsof -i :<port>` to find the conflict, stop it or remap in `docker-compose.yml` |
| 2 | **`uv: command not found`** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| 3 | **DB connection refused (local)** | Set `DATABASE_HOST=localhost` in `.env`, ensure PostgreSQL is running |
| 4 | **Containers won't start** | Check `.env` has all required vars, run `docker compose logs <service>` |
| 5 | **No logs in GCP Cloud Logging** | Filter by `resource.type="gce_instance"`, not `"global"`. See [full guide](docs/TROUBLESHOOTING.md#6-no-logs-in-gcp-cloud-logging) |
| 6 | **Prometheus targets DOWN** | `docker compose ps` — restart failed containers |
| 7 | **Grafana shows "No data"** | Check Prometheus data source URL is `http://prometheus:9090` (not localhost) |
| 8 | **Discord alerts not firing** | Verify `DISCORD_WEBHOOK_URL` in `.env`, check `docker compose logs discord-webhook` |
| 9 | **CI deploy skips silently** | Add `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY` GitHub Secrets. See [DEPLOY.md](docs/DEPLOY.md#github-secrets-for-ci-deploy) |
| 10 | **SSH refused to VM** | Check VM is running: `gcloud compute instances describe urlpulse-vm --zone=us-central1-a` |
| 11 | **High latency** | Check Redis is up (`X-Cache` header), run `docker stats` for resource usage |
| 12 | **Docker permission denied on VM** | `sudo usermod -aG docker $USER && newgrp docker` |

## Environment Variables

The project uses a .env file to manage configuration across the Flask app, PostgreSQL, Redis, and the observability stack.

| Variable               | Description                                         | Default (Docker) |
|------------------------|-----------------------------------------------------|------------------|
| **App & Database**         |                                                     |                  |
| FLASK_DEBUG            | Enables debug mode and hot-reloading.               | true             |
| DATABASE_NAME          | The name of the Postgres database.                  | hackathon_db     |
| DATABASE_HOST          | Hostname of the DB. Use localhost for local runs.   | postgres         |
| DATABASE_USER          | Database user for the application.                  | postgres         |
| DATABASE_PASSWORD      | Required. Password for the application user.        | Required         |
| Postgres Bootstrap     |                                                     |                  |
| POSTGRES_DB            | Initial database created by the container.          | hackathon_db     |
| POSTGRES_PASSWORD      | Required. Root password for the Postgres container. | Required         |
| **Redis**                  |                                                     |                  |
| REDIS_HOST             | Hostname for the Redis cache.                       | redis            |
| REDIS_PORT             | Port for Redis connections.                         | 6379             |
| **Observability**          |                                                     |                  |
| GRAFANA_ADMIN_USER     | Admin username for the Grafana dashboard.           | Required         |
| GRAFANA_ADMIN_PASSWORD | Admin password for the Grafana dashboard.           | Required         |
| DISCORD_WEBHOOK_URL    | Webhook for Alertmanager notifications.             | Required         |


## Testing the Hosted App

```bash
# Get your VM's external IP
VM_IP=$(gcloud compute addresses describe urlpulse-ip --region=us-central1 --format='value(address)')

# Health & readiness
curl http://$VM_IP/health
curl http://$VM_IP/ready

# Seed demo data & test endpoints
curl -X POST http://$VM_IP/seed
curl http://$VM_IP/users
curl http://$VM_IP/stats

# Dashboards
# Grafana:      http://$VM_IP:3000
# Prometheus:   http://$VM_IP:9090
# Alertmanager: http://$VM_IP:9093
```

## Load Testing & Chaos Engineering

```bash
# Install k6: brew install k6

# Load tests (run in order — Bronze → Silver → Gold)
k6 run --env BASE_URL=http://$VM_IP tests/load/baseline.js   # 50 VUs
k6 run --env BASE_URL=http://$VM_IP tests/load/scale.js      # 200 VUs
k6 run --env BASE_URL=http://$VM_IP tests/load/tsunami.js    # 500 VUs

# Chaos tests — local (against local Docker stack)
./scripts/chaos.sh kill-one      # Kill 1 instance, verify 2 still serve
./scripts/chaos.sh full-demo     # Run all chaos tests sequentially

# Chaos tests — remote (against hosted VM via gcloud SSH)
./scripts/chaos.sh --remote kill-one      # Kill 1 instance on VM
./scripts/chaos.sh --remote kill-db       # Show /health vs /ready difference
./scripts/chaos.sh --remote kill-redis    # Verify graceful degradation
./scripts/chaos.sh --remote error-flood   # Trigger HighErrorRate alert → Discord
./scripts/chaos.sh --remote high-latency   # Trigger HighLatency alert → Discord
./scripts/chaos.sh --remote high-memory    # Trigger HighMemoryUsage alert → Discord
./scripts/chaos.sh --remote full-demo     # Run all chaos tests on VM

# Live "break the system" demo (preflight + full outage + recovery)
./scripts/demo_break_system.sh
./scripts/demo_break_system.sh --remote
```

See [docs/LOAD_AND_CHAOS.md](docs/LOAD_AND_CHAOS.md) for the full guide — tier breakdowns, what each test proves, recommended demo order, and how to interpret results.

## Documentation

| Doc | What it covers |
|-----|---------------|
| [docs/DEPLOY.md](docs/DEPLOY.md) | GCP VM setup, CI deploy, rollback procedures |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Full troubleshooting guide — diagnostics, tools, step-by-step fixes |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Technical choices with rationale (GCP, Nginx, Redis, etc.) |
| [docs/LOAD_AND_CHAOS.md](docs/LOAD_AND_CHAOS.md) | Load testing guide, chaos engineering demo, recommended demo order |
| [docs/CAPACITY.md](docs/CAPACITY.md) | Load test results, bottleneck analysis, scaling roadmap |
| [docs/FAILURE_MODES.md](docs/FAILURE_MODES.md) | What breaks, impact, and how the system recovers |
| [docs/INCIDENT_POSTMORTEM.md](docs/INCIDENT_POSTMORTEM.md) | INC-001: Redis OOM cache miss storm |
| [docs/FEATURES.md](docs/FEATURES.md) | Every feature mapped to its hackathon quest |
