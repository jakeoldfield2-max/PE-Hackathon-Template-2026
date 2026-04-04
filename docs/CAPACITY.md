# Capacity Planning

> Load test results and scaling analysis for URLPulse.

---

## Benchmark Results

| Tier | Users (VUs) | Req/s | P95 Latency | Error Rate | Cache Hit | Status |
|------|------------|-------|-------------|------------|-----------|--------|
| **Bronze** | 50 | ~50 | <200ms | 0% | ~70% | Target |
| **Silver** | 200 | ~100 | <850ms | <0.5% | ~75% | Target |
| **Gold** | 500 | ~180 | <2.8s | <2.5% | ~91% | Target |

---

## Bottleneck Analysis

### Primary Bottleneck: Database I/O

Under 500 concurrent users without Redis caching, PostgreSQL becomes the bottleneck:
- Connection pool saturates at ~100 concurrent connections
- Each `GET /users` query takes ~5ms, but under contention rises to ~50ms
- With Redis cache (10s TTL), ~91% of reads never hit the DB

### Secondary Bottleneck: Memory

Each Gunicorn worker uses ~50MB RSS. With 3 instances × 4 workers = 12 workers:
- App memory: ~600MB
- PostgreSQL: ~200MB
- Redis: 256MB (capped by maxmemory)
- Total: ~1.1GB — fits within e2-standard-2's 8GB

---

## Capacity Estimates

| Users | Required Instances | Cache Hit Target | DB Connections |
|-------|--------------------|------------------|----------------|
| 1–50 | 1 | 50%+ | 10 |
| 50–200 | 2 | 75%+ | 30 |
| 200–500 | 3 | 90%+ | 60 |
| 500–1000 | 5+ (needs scaling) | 95%+ | 100+ |

---

## Scaling Roadmap (if we needed to go beyond 500 users)

1. **Add more app instances** — Nginx upstream already supports N instances
2. **PostgreSQL read replicas** — Route GET queries to replicas
3. **Move to Cloud Run** — Auto-scaling containers, pay-per-request
4. **CDN for static responses** — Cache `/stats` at the edge
5. **Connection pooling** — PgBouncer between app and PostgreSQL
