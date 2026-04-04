# Technical Decisions

> Each decision documents **what** we chose, **what alternatives** we considered, and **why** we went this route.

---

## #1 — GCP over AWS

| | |
|---|---|
| **Chosen** | Google Cloud Platform (e2-standard-2 VM) |
| **Alternatives** | AWS EC2, DigitalOcean, Railway |
| **Why** | GCP credits expiring soon, better console UX for quick setup. Single VM is sufficient for this hackathon — no need for managed Kubernetes. Cost: ~$1.66/day (≈₹280 for the entire hackathon). |

## #2 — Nginx over HAProxy

| | |
|---|---|
| **Chosen** | Nginx (round-robin upstream) |
| **Alternatives** | HAProxy, Traefik, Caddy |
| **Why** | Simplicity — Nginx config is ~50 lines. Industry standard for reverse proxy + load balancing. Built-in gzip compression. HAProxy is more powerful but overkill for 3 upstream instances. |

## #3 — Redis over Memcached

| | |
|---|---|
| **Chosen** | Redis 7 with allkeys-lru eviction |
| **Alternatives** | Memcached, in-app LRU cache |
| **Why** | Per-key TTL (10s for users, 5s for URLs) — Memcached only has global expiry. LRU eviction policy prevents OOM crashes (learned from INC-001). Persistence via appendonly means cache survives Redis restarts. In-app cache doesn't work with 3 instances (each would have its own stale cache). |

## #4 — Peewee over SQLAlchemy

| | |
|---|---|
| **Chosen** | Peewee ORM |
| **Alternatives** | SQLAlchemy, raw SQL, Django ORM |
| **Why** | Template default — team already familiar. DatabaseProxy pattern makes it easy to swap between PostgreSQL (production) and SQLite (tests). Lightweight — no complex session management. |

## #5 — Gunicorn (4 workers) over Flask dev server

| | |
|---|---|
| **Chosen** | Gunicorn with 4 workers, 30s timeout |
| **Alternatives** | Flask development server, uWSGI, Uvicorn |
| **Why** | Flask dev server is single-threaded — cannot handle concurrent requests from load testing. 4 workers = 2 × CPU cores + 1 (standard I/O-bound formula). 30s timeout prevents slow queries from blocking workers. Gunicorn is the most common Python WSGI server. |

## #6 — SQLite in-memory for tests

| | |
|---|---|
| **Chosen** | SQLite `:memory:` via Peewee's `SqliteDatabase` |
| **Alternatives** | PostgreSQL container for tests, mock database |
| **Why** | Speed — tests run in ~3s vs ~30s with a real PostgreSQL container. Peewee's DatabaseProxy makes the swap transparent. Mocks are dangerous — we got burned when mocked tests passed but real DB had schema issues. SQLite covers model/route logic; integration tests run against real PostgreSQL in Docker. |

## #7 — Single .env schema standard

| | |
|---|---|
| **Chosen** | One shared `.env.example` schema with Docker-first baseline and minimal per-environment overrides |
| **Alternatives** | Multiple env templates per environment (`.env.docker`, `.env.local`, `.env.supabase`) |
| **Why** | A single schema reduces onboarding errors and merge drift. Docker baseline lets teammates run quickly, while local/Supabase only require overriding a few keys. Required secret checks in Compose fail fast when critical values are missing, preventing insecure defaults from silently running. |

## #8 — SSH deploy over manual provisioning

| | |
|---|---|
| **Chosen** | Manual GCP Compute Engine VM + SSH deploy from CI |
| **Alternatives** | Manual SSH deploy, Cloud Run, Firebase Hosting |
| **Why** | Deployment tooling adds 1-2 hours of setup risk (service accounts, IAM, credentials JSON) for zero extra quest points. Judges score app reliability, not IaC. SSH deploy gives identical CI/CD evidence (deploy blocked when tests fail). Firebase Hosting is serverless — hides the infrastructure we need to demonstrate (containers, load balancing, chaos recovery). Cloud Run auto-scales but doesn't show manual scaling decisions. A single VM running Docker Compose is the sweet spot: full control, visible infrastructure, minimal setup time. |
