# Runbook Template

Use this format when creating new runbooks for production alerts.

---

## Alert: [ALERT_NAME]

### Summary
Brief description of what this alert means.

### Severity
- **Critical** / **Warning**

### Impact
What is affected when this alert fires? Who/what is impacted?

### Possible Causes
1. Cause 1
2. Cause 2
3. Cause 3

### Diagnosis Steps
1. Step 1 - What to check first
2. Step 2 - How to gather more information
3. Step 3 - How to identify root cause

### Resolution Steps
1. Step 1 - Immediate action
2. Step 2 - Fix the underlying issue
3. Step 3 - Verify the fix

### Commands
```bash
# Useful diagnostic commands
docker compose logs <service>
curl http://localhost/health
```

### Escalation
- If unresolved after 15 minutes, escalate to: [TEAM/PERSON]
- Contact: [CONTACT INFO]

### Prevention
How to prevent this alert from firing in the future.

### Related Links
- [Link to relevant documentation]
- [Link to related alerts]
