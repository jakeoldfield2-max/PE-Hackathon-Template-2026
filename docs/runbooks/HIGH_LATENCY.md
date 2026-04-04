# Runbook: HighLatency

## Alert: HighLatency

### Summary
The 95th percentile (p95) request latency exceeds 2 seconds for more than 2 minutes. This means 5% of requests are taking longer than 2 seconds to complete.

### Severity
- **Warning**

### Impact
- Poor user experience (slow page loads)
- Potential timeout errors for clients
- Cascading delays in dependent systems
- Risk of connection pool exhaustion

### Possible Causes
1. Database queries running slow (missing indexes, lock contention)
2. High traffic load exceeding capacity
3. Redis cache misses causing database overload
4. Network latency between services
5. Resource contention (CPU/memory pressure)
6. Large response payloads
7. Slow external API calls

### Diagnosis Steps

1. **Check current latency in Grafana**
   - Open http://localhost:3000
   - View "P95 Latency" panel
   - Identify when latency started increasing

2. **Check which endpoints are slow**
   ```bash
   # Query Prometheus for latency by endpoint
   curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_request_duration_seconds_bucket[5m]))by(le,endpoint))"
   ```

3. **Check request rate (traffic spike?)**
   ```bash
   curl -s "http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total[1m]))"
   ```

4. **Check database performance**
   ```bash
   docker compose exec postgres psql -U postgres -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
   ```

5. **Check Redis cache hit rate**
   ```bash
   docker compose exec redis redis-cli INFO stats | grep hit
   ```

6. **Check container resource usage**
   ```bash
   docker stats --no-stream
   ```

### Resolution Steps

1. **If traffic spike, scale if possible or wait for it to subside**
   - Monitor traffic patterns
   - Consider rate limiting if attack

2. **If database slow**
   ```bash
   # Check for long-running queries
   docker compose exec postgres psql -U postgres -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"

   # Kill long-running query if needed
   docker compose exec postgres psql -U postgres -c "SELECT pg_cancel_backend(<pid>);"
   ```

3. **If cache misses high, warm the cache**
   ```bash
   curl -X POST http://localhost/seed
   curl http://localhost/users  # Populate cache
   ```

4. **If resource exhaustion, restart containers**
   ```bash
   docker compose restart app-1 app-2 app-3
   ```

5. **Verify latency has improved**
   - Monitor Grafana dashboard
   - P95 should drop below 2 seconds

### Escalation
- If p95 exceeds 5 seconds: Escalate immediately
- If unresolved after 15 minutes: Escalate to senior engineer
- If caused by traffic spike: Consider scaling or CDN

### Prevention
- Implement database query monitoring
- Set up slow query logging
- Cache frequently accessed data
- Load test regularly to understand capacity limits
- Consider horizontal scaling for high traffic

### Related Links
- [CAPACITY.md](../CAPACITY.md)
- [HighMemoryUsage Runbook](./HIGH_MEMORY_USAGE.md)
