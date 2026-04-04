# Failure Mode Analysis

> What breaks, what happens when it does, and how the system recovers.

---

## Scenario 1: App Instance Crash

| Field | Detail |
|-------|--------|
| **Trigger** | `docker kill urlpulse-app-1` or OOM kill |
| **Impact** | 1 of 3 instances down — Nginx routes to remaining 2 |
| **Detection** | Prometheus `up{job="urlpulse"} == 0` within 15s |
| **Recovery** | Docker `restart: always` brings it back in ~5s |
| **Data loss** | None — in-flight requests on that instance get 502 from Nginx |

**Demo command:** `docker kill urlpulse-app-1 && curl http://localhost/health`
→ Still returns 200 (served by app-2 or app-3)

---

## Scenario 2: PostgreSQL Down

| Field | Detail |
|-------|--------|
| **Trigger** | `docker kill urlpulse-postgres` |
| **Impact** | `/ready` returns 503, write operations fail |
| **Detection** | `/health` still returns 200 (app is alive), `/ready` returns 503 |
| **Recovery** | Docker restarts PostgreSQL, app reconnects automatically |
| **Data loss** | None — PostgreSQL uses WAL + named volume |

**Key insight:** This is why we have both `/health` and `/ready`. The app is alive but can't serve traffic — load balancer should stop routing to it.

---

## Scenario 3: Redis Down

| Field | Detail |
|-------|--------|
| **Trigger** | `docker kill urlpulse-redis` |
| **Impact** | Caching disabled — all requests hit PostgreSQL directly |
| **Detection** | Cache hit rate drops to 0% in Grafana, latency increases |
| **Recovery** | Docker restarts Redis, `cache.py` reconnects on next request |
| **Data loss** | Cache only — no persistent data in Redis |

**Key insight:** Graceful degradation — the app works without Redis, just slower. This is intentional design in `app/cache.py` (returns `None` on failure, routes fall through to DB).

---

## Scenario 4: Nginx Down

| Field | Detail |
|-------|--------|
| **Trigger** | `docker kill urlpulse-nginx` or bad config |
| **Impact** | All external traffic fails (connection refused on port 80) |
| **Detection** | Cannot reach any endpoint from outside |
| **Recovery** | Docker `restart: always` brings it back. If config is bad, stays in restart loop. |
| **Data loss** | None — app instances are fine, just unreachable |

---

## Scenario 5: Disk Full

| Field | Detail |
|-------|--------|
| **Trigger** | Docker logs or PostgreSQL WAL fills disk |
| **Impact** | PostgreSQL stops accepting writes, containers may fail to restart |
| **Detection** | Write errors in application logs |
| **Recovery** | `docker system prune`, clean old logs, increase disk |
| **Data loss** | Possible if WAL corruption occurs |

---

## Scenario 6: Bad Deployment

| Field | Detail |
|-------|--------|
| **Trigger** | Code bug pushed to main, all containers fail to start |
| **Impact** | Complete outage — all 3 app instances crash-loop |
| **Detection** | All instances show `restart: always` loop in `docker compose ps` |
| **Recovery** | Rollback: `git revert HEAD && docker compose up -d --build` |
| **Data loss** | None — database volume persists |

---

## Summary Table

| Scenario | Severity | Auto-Recovery | Detection Time |
|----------|----------|---------------|----------------|
| 1 app crash | Low | Yes (restart) | 15s (Prometheus) |
| PostgreSQL down | High | Yes (restart) | Immediate (/ready) |
| Redis down | Medium | Yes (graceful) | 15s (metrics) |
| Nginx down | Critical | Yes (restart) | Immediate |
| Disk full | High | No (manual) | Minutes |
| Bad deploy | Critical | No (rollback) | Seconds |
