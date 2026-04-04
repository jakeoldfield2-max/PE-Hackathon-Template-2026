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
| `POST` | `/shorten` | Create a shortened URL |
| `POST` | `/update` | Update a URL |
| `POST` | `/delete` | Delete a URL |

## Quick Start (Docker)

```bash
# 1. Configure environment
cp .env.example .env
# Edit placeholders in .env using the Common Standard profile values.
# Required: DATABASE_PASSWORD, POSTGRES_PASSWORD,
#           GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD, DISCORD_WEBHOOK_URL
# Docker startup fails fast when required secrets are missing.

# 2. Start everything (3 app instances, Nginx, PostgreSQL, Redis)
docker compose up -d --build

# 3. Seed demo data
curl -X POST http://localhost/seed

# 4. Verify
curl http://localhost/health    # → {"status":"ok"}
curl http://localhost/ready     # → {"status":"ready","database":"connected"}
curl http://localhost/stats     # → {"total_users":3,"total_urls":10,...}
curl http://localhost/users     # → cached response (check X-Cache header)

# 5. View logs
docker compose logs -f
```

Quick checks:

- Docker mode: http://localhost/health
- Local mode: http://localhost:5000/health

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

# For local app run (no Docker), override only these values in .env:
#   DATABASE_HOST=localhost
#   REDIS_HOST=localhost
#   POSTGRES_* can stay as-is (only used by docker-compose)
# For Supabase, replace DATABASE_* values with Supabase credentials.
# Make sure PostgreSQL is running locally if you are not using Supabase:
#   brew install postgresql@16 && brew services start postgresql@16
#   createdb hackathon_db

# 3. Run the server
uv run run.py
# Server starts at http://localhost:5000

# 3.1 Main local endpoints
#   App root:        http://localhost:5000
#   Health:          http://localhost:5000/health
#   Readiness:       http://localhost:5000/ready
#   Metrics:         http://localhost:5000/metrics

# 4. Verify it's working
curl http://localhost:5000/health
# → {"status":"ok"}
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
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── url.py           # Url model
│   │   └── event.py         # Event model
│   └── routes/
│       ├── seed.py          # POST /seed — demo data
│       ├── stats.py         # GET /stats — system overview
│       ├── users.py         # User CRUD (cached)
│       └── url_actions/     # URL shorten/update/delete
├── nginx/
│   └── nginx.conf           # Round-robin load balancer config
├── tests/                   # pytest suite (SQLite in-memory)
├── scripts/
│   ├── provision.sh         # One-time GCP VM setup (idempotent)
│   └── deploy.sh            # SSH deploy to GCP VM (+ rollback)
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
./scripts/provision.sh --project pe-hackathon-template-2026  # Safer: explicit project
./scripts/provision.sh --yes      # Non-interactive mode (CI/automation)
./scripts/deploy.sh               # Deploy latest main via SSH
./scripts/deploy.sh --rollback    # Revert last deploy
```

CI auto-deploys on merge to `main` (blocked unless tests + docker-build pass).
See [docs/DEPLOY.md](docs/DEPLOY.md) for first-time setup and troubleshooting.

## Documentation

| Doc | What it covers |
|-----|---------------|
| [docs/DEPLOY.md](docs/DEPLOY.md) | GCP VM setup, CI deploy, rollback procedures |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Technical choices with rationale (GCP, Nginx, Redis, etc.) |
| [docs/CAPACITY.md](docs/CAPACITY.md) | Load test results, bottleneck analysis, scaling roadmap |
| [docs/FAILURE_MODES.md](docs/FAILURE_MODES.md) | What breaks, impact, and how the system recovers |
| [docs/INCIDENT_POSTMORTEM.md](docs/INCIDENT_POSTMORTEM.md) | INC-001: Redis OOM cache miss storm |
| [docs/FEATURES.md](docs/FEATURES.md) | Every feature mapped to its hackathon quest |
