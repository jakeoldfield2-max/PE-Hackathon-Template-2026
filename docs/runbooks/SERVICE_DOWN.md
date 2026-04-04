# Runbook: ServiceDown

## Alert: ServiceDown

### Summary
One or more URLPulse application instances are unreachable and not responding to health checks.

### Severity
- **Critical**

### Impact
- Reduced application capacity
- Traffic automatically shifted to remaining healthy instances via Nginx round-robin
- If all 3 instances down: Complete service outage

### Possible Causes
1. Container crashed or was killed (OOM, unhandled exception)
2. Database connection failure preventing startup
3. Redis connection failure
4. Docker daemon issues
5. Resource exhaustion (CPU/memory/disk)

### Diagnosis Steps

1. **Check which instance is down**
   ```bash
   docker compose ps
   ```

2. **Check container logs for errors**
   ```bash
   docker compose logs app-1 --tail 50
   docker compose logs app-2 --tail 50
   docker compose logs app-3 --tail 50
   ```

3. **Check if dependencies are healthy**
   ```bash
   docker compose ps postgres redis
   curl http://localhost/ready
   ```

4. **Check system resources**
   ```bash
   docker stats --no-stream
   ```

### Resolution Steps

1. **Restart the failed instance**
   ```bash
   docker compose restart app-1  # Replace with affected instance
   ```

2. **If restart fails, check logs and fix underlying issue**
   ```bash
   docker compose logs app-1 --tail 100
   ```

3. **If database related, verify database is accessible**
   ```bash
   docker compose exec postgres pg_isready
   ```

4. **Full stack restart (last resort)**
   ```bash
   docker compose down
   docker compose up -d
   ```

5. **Verify recovery**
   ```bash
   curl http://localhost/health
   curl http://localhost/ready
   ```

### Escalation
- If unresolved after 15 minutes, escalate to: On-call engineer
- If all instances down: Immediate escalation to team lead

### Prevention
- Monitor memory usage to prevent OOM kills
- Ensure database connection pooling is configured correctly
- Set up container resource limits
- Regular health check monitoring

### Related Links
- [FAILURE_MODES.md](../FAILURE_MODES.md)
- [HighMemoryUsage Runbook](./HIGH_MEMORY_USAGE.md)
