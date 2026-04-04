# Feature → Quest Mapping

> Every feature mapped to the hackathon quest it satisfies, with evidence.

---

## Reliability Quest

| Tier | Feature | Evidence |
|------|---------|----------|
| **Bronze** | `/health` endpoint | `curl http://localhost/health` → `{"status":"ok"}` |
| **Bronze** | Docker `restart: always` | `docker kill app-1` → auto-restarts in ~5s |
| **Silver** | JSON error responses | `curl http://localhost/nonexistent` → `{"error":"Not found","status":404}` |
| **Silver** | `/ready` endpoint | `curl http://localhost/ready` → checks DB connectivity |
| **Silver** | CI blocks deploy on test failure | GitHub Actions: deploy `needs: [test]` |
| **Gold** | 3 instances survive 1 kill | Kill app-1, app-2+3 continue serving |
| **Gold** | Automated recovery | Docker restart policy + Nginx health routing |

## Scalability Quest

| Tier | Feature | Evidence |
|------|---------|----------|
| **Bronze** | Gunicorn multi-worker | 4 workers per instance = 12 total |
| **Bronze** | Docker containerization | `docker compose up` runs full stack |
| **Silver** | Nginx load balancing | Round-robin across 3 instances |
| **Silver** | Redis caching (10s TTL) | `X-Cache: HIT` header on cached responses |
| **Gold** | 500 VU load test passes | k6 tsunami.js: p95<5s, errors<5% |
| **Gold** | ~91% cache hit rate | Redis absorbs majority of read traffic |

## Incident Response Quest

| Tier | Feature | Evidence |
|------|---------|----------|
| **Bronze** | Event logging (User/URL/Event models) | All URL changes logged with event_type |
| **Silver** | Structured error responses | Consistent JSON format for all errors |
| **Gold** | Discord alerts on outage | Alertmanager → Discord webhook on ServiceDown |
| **Gold** | Operational runbooks | docs/RUNBOOK.md with step-by-step recovery |
| **Gold** | Incident postmortem | docs/INCIDENT_POSTMORTEM.md (INC-001) |

## Documentation Quest

| Tier | Feature | Evidence |
|------|---------|----------|
| **Bronze** | README with setup instructions | One-command `docker compose up` |
| **Silver** | Architecture diagram | ASCII diagram in README + docs/ARCHITECTURE.md |
| **Gold** | Technical decision records | docs/DECISIONS.md — 6 ADRs with rationale |
| **Gold** | Failure mode analysis | docs/FAILURE_MODES.md — 6 scenarios |
| **Gold** | Capacity planning | docs/CAPACITY.md — load test results + scaling roadmap |
