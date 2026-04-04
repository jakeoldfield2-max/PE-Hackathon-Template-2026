# Runbook: HighErrorRate

## Alert: HighErrorRate

### Summary
The application is returning HTTP 5xx errors at a rate exceeding 5% of total requests for more than 2 minutes.

### Severity
- **Warning**

### Impact
- Users experiencing failed requests
- Potential data inconsistency if write operations fail
- Degraded user experience
- SLA may be at risk

### Possible Causes
1. Database connection pool exhausted
2. Redis connection failures
3. Unhandled exceptions in application code
4. Downstream service failures
5. Invalid data causing processing errors
6. Resource exhaustion (memory, connections)

### Diagnosis Steps

1. **Check current error rate in Grafana**
   - Open http://localhost:3000
   - View "Error Rate" panel

2. **Identify which endpoints are failing**
   ```bash
   # Check Prometheus for errors by endpoint
   curl -s "http://localhost:9090/api/v1/query?query=http_requests_total{status=~'5..'}" | jq
   ```

3. **Check application logs for exceptions**
   ```bash
   docker compose logs app-1 --tail 100 | grep -i error
   docker compose logs app-2 --tail 100 | grep -i error
   docker compose logs app-3 --tail 100 | grep -i error
   ```

4. **Check database connectivity**
   ```bash
   curl http://localhost/ready
   ```

5. **Check Redis connectivity**
   ```bash
   docker compose exec redis redis-cli ping
   ```

### Resolution Steps

1. **If database related**
   ```bash
   docker compose restart postgres
   # Wait for health check, then restart apps
   docker compose restart app-1 app-2 app-3
   ```

2. **If Redis related**
   ```bash
   docker compose restart redis
   ```

3. **If code-related errors, check recent deployments**
   - Review recent commits
   - Consider rollback if needed:
   ```bash
   ./scripts/deploy.sh --rollback
   ```

4. **If resource exhaustion**
   ```bash
   docker stats --no-stream
   # Restart affected containers
   docker compose restart app-1 app-2 app-3
   ```

5. **Verify error rate has decreased**
   - Monitor Grafana dashboard
   - Check Prometheus: error rate should drop below 5%

### Escalation
- If error rate exceeds 20%: Immediate escalation
- If unresolved after 10 minutes: Escalate to senior engineer
- If affecting all endpoints: Consider maintenance mode

### Prevention
- Implement circuit breakers for external dependencies
- Add retry logic with exponential backoff
- Monitor error trends before they hit alert thresholds
- Regular load testing to identify breaking points

### Related Links
- [CAPACITY.md](../CAPACITY.md)
- [ServiceDown Runbook](./SERVICE_DOWN.md)
