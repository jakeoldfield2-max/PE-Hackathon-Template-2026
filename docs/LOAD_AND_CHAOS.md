# Load Testing & Chaos Engineering

> How to stress-test URLPulse and prove it handles failure gracefully.

---

## Prerequisites

- **k6** — `brew install k6` (macOS) or [install guide](https://grafana.com/docs/k6/latest/set-up/install-k6/)
- **Running app** — either Docker locally (`docker compose up -d --build`) or hosted on GCP VM

```bash
# Get your VM's external IP (skip if testing locally)
VM_IP=$(gcloud compute addresses describe urlpulse-ip --region=us-central1 --format='value(address)')

# Set target — pick one
TARGET=http://localhost        # Local Docker
TARGET=http://$VM_IP           # Hosted VM
```

---

## Load Testing (k6)

Three tiers of progressively harder load tests. Run against your hosted VM for realistic results.

### Setup

```bash
# Seed data first — load tests need existing users and URLs
curl -X POST $TARGET/seed

# Open Grafana to watch metrics live during the test
# http://$TARGET:3000  (or http://localhost:3000 for local)
```

### Run Tests

Run in order — each tier increases pressure on the system:

```bash
k6 run --env BASE_URL=$TARGET tests/load/baseline.js   # Bronze
k6 run --env BASE_URL=$TARGET tests/load/scale.js      # Silver
k6 run --env BASE_URL=$TARGET tests/load/tsunami.js    # Gold
```

### Tier Breakdown

| Tier | File | VUs | Duration | Thresholds |
|------|------|-----|----------|------------|
| **Bronze** | `baseline.js` | 50 | 60s flat | p95 < 3s, errors < 10% |
| **Silver** | `scale.js` | 200 | Staged ramp (15s→50, 30s→200, 30s hold, 15s→0) | p95 < 3s, errors < 5% |
| **Gold** | `tsunami.js` | 500 | Staged ramp (15s→100, 30s→500, 30s hold, 15s→0) | p95 < 5s, errors < 5%, cache hits > 90% |

### What Each Tier Tests

- **Bronze (baseline.js)** — Can the system handle normal traffic? Hits `/health`, `/users`, `/stats`, `/ready`, and `POST /shorten`. Validates basic functionality under concurrent load.

- **Silver (scale.js)** — Can the system handle growth? Adds write traffic (`POST /users` at 8%, `GET /users/<id>` at 5%) and ramps to 200 concurrent users. Tests connection pooling and cache effectiveness.

- **Gold (tsunami.js)** — Can the system survive a traffic spike? 500 concurrent users with 40% traffic to `/users` for cache validation. Requires >90% cache hit rate to pass. Tests Redis under pressure and PostgreSQL connection limits.

### What to Watch

- **k6 terminal** — p95 latency, error rate, requests/sec
- **Grafana** — Traffic spike in real-time, latency distribution, cache hit ratio
- **After load stops** — System should recover to baseline metrics within ~30s

### Interpreting Results

| Metric | Good | Warning | Bad |
|--------|------|---------|-----|
| p95 latency | < 1s | 1-3s | > 3s |
| Error rate | 0% | < 5% | > 10% |
| Requests/sec | > 100 | 50-100 | < 50 |
| Cache hit rate | > 90% | 70-90% | < 70% |

If tests fail, see [CAPACITY.md](CAPACITY.md) for bottleneck analysis and scaling strategies.

---

## Chaos Engineering

Break the system on purpose to prove it recovers. All tests auto-recover — containers have `restart: always`.

### Local vs Remote

The chaos script supports two modes:

```bash
# Local — runs docker commands directly against your local Docker stack
./scripts/chaos.sh kill-one
./scripts/chaos.sh full-demo

# Remote — SSHes into the GCP VM for docker commands, curls the VM IP
./scripts/chaos.sh --remote kill-one
./scripts/chaos.sh --remote full-demo
```

**Important:** Without `--remote`, all chaos tests (including `error-flood`) target `http://localhost`. If you want to trigger alerts on the hosted VM, you **must** use `--remote`. Running locally only affects your local stack and won't trigger Discord alerts on the hosted VM.

### Individual Tests

| Command | What Breaks | What to Expect |
|---------|-------------|----------------|
| `./scripts/chaos.sh [--remote] kill-one` | 1 of 3 app instances | Other 2 keep serving — `/health` still returns 200 |
| `./scripts/chaos.sh [--remote] kill-db` | PostgreSQL | `/health` = 200 (alive), `/ready` = 503 (not ready) |
| `./scripts/chaos.sh [--remote] kill-redis` | Redis cache | App still works, just slower — serves from DB directly |
| `./scripts/chaos.sh [--remote] error-flood` | Sends 200 bad requests | Triggers HighErrorRate alert → Discord (~60s) |
| `./scripts/chaos.sh [--remote] high-latency` | Sustained slow requests | Triggers HighLatency alert → Discord (~2m) |
| `./scripts/chaos.sh [--remote] high-memory` | Allocate resident memory | Triggers HighMemoryUsage alert → Discord (~2m) |
| `./scripts/chaos.sh [--remote] kill-all` | All 3 app instances | Total outage → ServiceDown alert on Discord (~60-90s) |

### Full Demo

Runs all chaos tests sequentially with colored output:

```bash
./scripts/chaos.sh full-demo            # Local
./scripts/chaos.sh --remote full-demo   # Remote VM
```

### Stage Demo (Recommended)

For a live presentation, use the dedicated orchestration script. It runs preflight checks, seeds data, then executes a full break-and-recover story including a complete outage.

```bash
./scripts/demo_break_system.sh
./scripts/demo_break_system.sh --remote
```

What it runs in order:

1. `kill-one` (prove no single-instance failure)
2. `high-latency` (prove slow-request alerting)
3. `kill-redis` (prove graceful degradation)
4. `high-memory` (prove resident-memory alerting)
5. `kill-db` (prove health vs readiness behavior)
6. `error-flood` (trigger HighErrorRate alert)
7. `kill-all` (force full outage + automatic recovery)

Optional:

```bash
./scripts/demo_break_system.sh --remote --skip-seed
```

Use `--skip-seed` if your data is already prepared and you want a faster run.

**Demo flow:** kill instance → kill Redis → kill DB → error flood.

### What Each Test Proves

#### kill-one — Horizontal Scaling
Stops 1 of 3 app instances. Nginx detects the instance is down and routes traffic to the surviving 2. The stopped instance restarts automatically via Docker.
- **Proves:** No single point of failure at the app layer
- **Watch:** `/health` returns 200 the entire time

#### kill-db — Health vs Readiness
Stops PostgreSQL. The app process is still alive (`/health` = 200) but can't serve data (`/ready` = 503). This distinction lets load balancers stop routing traffic to instances that can't fulfill requests.
- **Proves:** Liveness and readiness are separate concerns
- **Watch:** `/health` stays 200, `/ready` drops to 503, then recovers when DB restarts

#### kill-redis — Graceful Degradation
Stops Redis. The app detects cache failure and falls through to querying PostgreSQL directly. Response times increase but no errors occur.
- **Proves:** Cache is an optimization, not a dependency
- **Watch:** `/users` still returns 200, but `X-Cache` header disappears

#### error-flood — Alerting Pipeline
Sends 200 requests to a non-existent endpoint, generating a spike in error rate. Prometheus detects the rate exceeds the 10% threshold and fires a HighErrorRate alert through Alertmanager to Discord.
- **Proves:** Monitoring → alerting → notification pipeline works end-to-end
- **Watch:** Discord channel for the alert (~60s after flood), Prometheus alerts page at `:9090/alerts`

#### kill-all — Full Outage and Recovery
Stops all 3 app instances. The system is completely down. Prometheus detects all targets are unreachable and fires a ServiceDown alert. After 30s, instances are restarted and the system recovers.
- **Proves:** Alerting fires on outage, system self-heals
- **Watch:** Discord for ServiceDown alert, then all instances come back up

---

## Recommended Demo Order

For the best demo flow, run load tests first, then chaos:

1. **Seed data** — `curl -X POST $TARGET/seed`
2. **Open Grafana** — watch metrics live during all tests
3. **Bronze load test** — prove system handles normal traffic
4. **Gold load test** — push to the limit, show it survives
5. **kill-one** — kill an instance during/after load, show it keeps serving
6. **kill-redis** — show graceful degradation
7. **kill-db** — show health vs readiness
8. **error-flood** — trigger alerts, show Discord notification

This tells the full story: handles load → survives failures → recovers automatically → alerts when things break.

---

## Further Reading

- [CAPACITY.md](CAPACITY.md) — Benchmark results, bottleneck analysis, scaling roadmap
- [FAILURE_MODES.md](FAILURE_MODES.md) — Every failure scenario with impact and recovery details
- [INCIDENT_POSTMORTEM.md](INCIDENT_POSTMORTEM.md) — INC-001: Redis OOM cache miss storm
