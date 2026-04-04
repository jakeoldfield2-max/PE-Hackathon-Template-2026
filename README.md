# URLPulse — Production-Grade URL Shortener

> **MLH Production Engineering Hackathon 2026**

A production-grade URL shortener built to survive chaos. Shorten URLs, track events, and prove your system can handle load, recover from failures, and alert when things break.

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Language** | Python 3.13 | Template default, team familiarity |
| **Framework** | Flask | Lightweight, hackathon-friendly |
| **ORM** | Peewee | Simple, DatabaseProxy pattern for connection pooling |
| **Database** | PostgreSQL 16 | Production-grade relational DB |
| **Cache** | Redis 7 | In-memory caching with TTL & LRU eviction |
| **WSGI Server** | Gunicorn | Multi-worker concurrent request handling |
| **Load Balancer** | Nginx | Round-robin across 3 app instances |
| **Containerization** | Docker + Docker Compose | Full stack orchestration |
| **Metrics** | Prometheus | Scrapes /metrics, stores time-series data |
| **Dashboards** | Grafana | Four Golden Signals visualization |
| **Alerting** | Alertmanager → Discord | Automated incident notifications |
| **CI/CD** | GitHub Actions | Test → Build → Deploy pipeline |
| **Infrastructure** | GCP + Terraform | Reproducible cloud deployment |
| **Load Testing** | k6 | Scriptable load tests (50/200/500 users) |
| **Package Manager** | uv | Fast Python dependency management |

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
# Edit .env — uncomment "Option C: Docker Compose" and set passwords

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

## Running Locally (No Docker)

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment — pick ONE option in .env
cp .env.example .env

# Option A: Supabase (recommended for teams — shared DB, no local setup)
#   Fill in your Supabase credentials in .env
#   Get them from: Supabase Dashboard → Connect → Connection string

# Option B: Local PostgreSQL
#   Uncomment the local block in .env and comment out the Supabase block
#   Make sure PostgreSQL is running locally:
#   brew install postgresql@16 && brew services start postgresql@16
#   createdb hackathon_db

# 3. Run the server
uv run run.py
# Server starts at http://localhost:5000

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
├── docs/                    # Architecture, decisions, runbooks
├── .env.example             # Config template (local, Supabase, or Docker)
├── Dockerfile               # Python 3.13 + Gunicorn
├── docker-compose.yml       # Full stack (3 apps, Nginx, PG, Redis)
├── pyproject.toml
├── run.py
└── README.md
```

## Documentation

| Doc | What it covers |
|-----|---------------|
| [docs/DECISIONS.md](docs/DECISIONS.md) | Technical choices with rationale (GCP, Nginx, Redis, etc.) |
| [docs/CAPACITY.md](docs/CAPACITY.md) | Load test results, bottleneck analysis, scaling roadmap |
| [docs/FAILURE_MODES.md](docs/FAILURE_MODES.md) | What breaks, impact, and how the system recovers |
| [docs/INCIDENT_POSTMORTEM.md](docs/INCIDENT_POSTMORTEM.md) | INC-001: Redis OOM cache miss storm |
| [docs/FEATURES.md](docs/FEATURES.md) | Every feature mapped to its hackathon quest |
