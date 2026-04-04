# Runbook: HighMemoryUsage

## Alert: HighMemoryUsage

### Summary
Application process memory (RSS) exceeds 500MB for more than 2 minutes. This indicates potential memory leak or unexpectedly high memory consumption.

### Severity
- **Warning**

### Impact
- Risk of container being killed by OOM (Out of Memory) killer
- Degraded performance due to memory pressure
- Potential service disruption if container crashes
- May affect other containers on the same host

### Possible Causes
1. Memory leak in application code
2. Large objects held in memory (unbounded caches)
3. Many concurrent requests holding memory
4. Large file uploads or processing
5. Database result sets not properly released
6. Redis client connection pooling issues

### Diagnosis Steps

1. **Check current memory usage in Grafana**
   - Open http://localhost:3000
   - View "Memory" panel
   - Identify trend (gradual increase = leak, sudden spike = load)

2. **Check container memory stats**
   ```bash
   docker stats --no-stream
   ```

3. **Check which instance is affected**
   ```bash
   curl -s "http://localhost:9090/api/v1/query?query=process_resident_memory_bytes" | jq
   ```

4. **Check request rate (high traffic?)**
   ```bash
   curl -s "http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total[1m]))"
   ```

5. **Check application logs for issues**
   ```bash
   docker compose logs app-1 --tail 100
   ```

### Resolution Steps

1. **Immediate: Restart affected container**
   ```bash
   docker compose restart app-1  # Replace with affected instance
   ```

2. **If memory grows again quickly after restart**
   - Likely a memory leak or sustained high load
   - Check recent code changes
   - Consider rollback:
   ```bash
   ./scripts/deploy.sh --rollback
   ```

3. **If Redis-related (cache growing unbounded)**
   ```bash
   # Check Redis memory
   docker compose exec redis redis-cli INFO memory

   # Clear cache if needed (will cause temporary performance dip)
   docker compose exec redis redis-cli FLUSHDB
   ```

4. **If database connections not being released**
   ```bash
   docker compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
   ```

5. **Monitor after fix**
   - Watch Grafana memory panel
   - Memory should stabilize below 500MB

### Escalation
- If memory exceeds 800MB: Immediate escalation (OOM risk)
- If containers keep crashing: Escalate to senior engineer
- If memory leak confirmed: Create bug ticket for development team

### Prevention
- Set container memory limits in docker-compose.yml
- Implement proper connection pooling
- Use bounded caches with TTL and max size
- Regular code reviews for memory management
- Load testing to identify memory patterns

### Related Links
- [INCIDENT_POSTMORTEM.md](../INCIDENT_POSTMORTEM.md) - INC-001 Redis OOM
- [ServiceDown Runbook](./SERVICE_DOWN.md)
