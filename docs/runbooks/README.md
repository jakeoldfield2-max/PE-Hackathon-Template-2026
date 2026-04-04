# Production Runbooks

This folder contains runbooks for responding to production alerts. Each runbook provides step-by-step guidance for diagnosing and resolving specific alert conditions.

## How Runbooks Connect to Alerts

The alerting pipeline works as follows:

```
Prometheus          Alertmanager         Webhook Adapter        Discord
(detects issue) --> (routes alert) -->  (formats message) -->  (notification)
     |                                         |
     |                                         |
alerts.yml                              webhook-adapter.py
(defines alerts                         (reads annotations
 with annotations)                       and formats them)
```

### Where Runbooks Are Defined

Runbooks are linked to alerts in **`prometheus/alerts.yml`**. Each alert has an `annotations` section that includes:

```yaml
- alert: ServiceDown
  expr: up{job="urlpulse"} == 0
  for: 15s
  labels:
    severity: critical
  annotations:
    summary: "Brief description"
    description: "Detailed description with {{ $labels.instance }}"
    impact: "What is affected"
    runbook: "docs/runbooks/SERVICE_DOWN.md"    # <-- Runbook link
    action: "Immediate steps to take"
```

### How Annotations Appear in Discord

When an alert fires, the webhook adapter (`alertmanager/webhook-adapter.py`) extracts these annotations and formats them into a Discord message:

```
🔴 **FIRING** 🚨 **ServiceDown**
> URLPulse instance down
> Instance app-1:5000 is unreachable.
> **Instance:** `app-1:5000`
> **Impact:** Reduced capacity. Traffic shifted to remaining instances.
> **Action:** 1. Check logs: docker compose logs app-1 --tail 50...
> **Runbook:** `docs/runbooks/SERVICE_DOWN.md`
```

---

## Adding a New Runbook

### Step 1: Create the Runbook File

Create a new markdown file in this folder following the template:

```bash
cp docs/runbooks/TEMPLATE.md docs/runbooks/YOUR_ALERT_NAME.md
```

Edit the file with:
- Summary of what the alert means
- Possible causes
- Diagnosis steps with commands
- Resolution steps
- Escalation path
- Prevention measures

### Step 2: Add the Alert to Prometheus

Edit **`prometheus/alerts.yml`** to add your new alert:

```yaml
- alert: YourAlertName
  expr: your_prometheus_expression > threshold
  for: 2m
  labels:
    severity: warning  # or critical
    service: urlpulse
  annotations:
    summary: "Short summary"
    description: "Detailed description. Current value: {{ $value }}"
    impact: "What happens when this fires"
    runbook: "docs/runbooks/YOUR_ALERT_NAME.md"
    action: "1. First step  2. Second step  3. Third step"
```

### Step 3: Reload Prometheus

After editing alerts.yml, reload the configuration:

```bash
# Option 1: Hot reload (no restart needed)
curl -X POST http://localhost:9090/-/reload

# Option 2: Restart Prometheus
docker compose restart prometheus
```

### Step 4: Test Your Alert

You can test by temporarily lowering the threshold or manually sending a test alert:

```bash
curl -X POST "http://localhost:9093/api/v2/alerts" \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "YourAlertName", "severity": "warning"},
    "annotations": {
      "summary": "Test alert",
      "description": "Testing the new alert",
      "impact": "None - this is a test",
      "runbook": "docs/runbooks/YOUR_ALERT_NAME.md",
      "action": "No action needed - test only"
    }
  }]'
```

---

## Available Annotations

| Annotation | Required | Description |
|------------|----------|-------------|
| `summary` | Yes | One-line summary of the alert |
| `description` | Yes | Detailed description, can include template variables |
| `impact` | Recommended | What is affected when this alert fires |
| `runbook` | Recommended | Path to the runbook file |
| `action` | Recommended | Immediate steps to take (shown only when FIRING) |

### Template Variables

You can use Prometheus template variables in annotations:

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{{ $labels.instance }}` | Instance that triggered alert | `app-1:5000` |
| `{{ $labels.job }}` | Job name | `urlpulse` |
| `{{ $value }}` | Current metric value | `0.15` |
| `{{ $value \| humanizePercentage }}` | Value as percentage | `15%` |
| `{{ $value \| humanizeDuration }}` | Value as duration | `2m 30s` |
| `{{ $value \| humanize1024 }}` | Value with SI prefix | `512Mi` |

---

## Current Runbooks

| Alert | Severity | Runbook |
|-------|----------|---------|
| ServiceDown | Critical | [SERVICE_DOWN.md](./SERVICE_DOWN.md) |
| HighErrorRate | Warning | [HIGH_ERROR_RATE.md](./HIGH_ERROR_RATE.md) |
| HighLatency | Warning | [HIGH_LATENCY.md](./HIGH_LATENCY.md) |
| HighMemoryUsage | Warning | [HIGH_MEMORY_USAGE.md](./HIGH_MEMORY_USAGE.md) |

---

## File Structure

```
docs/runbooks/
├── README.md              # This file
├── TEMPLATE.md            # Template for new runbooks
├── SERVICE_DOWN.md        # ServiceDown alert runbook
├── HIGH_ERROR_RATE.md     # HighErrorRate alert runbook
├── HIGH_LATENCY.md        # HighLatency alert runbook
└── HIGH_MEMORY_USAGE.md   # HighMemoryUsage alert runbook
```
