# k6 Load Testing Scripts

> Stress test URLPulse by simulating realistic user behavior under load.

---

## Scripts

| Script | Description | Default VUs | Status |
|--------|-------------|-------------|--------|
| `user-signup.js` | Simulates users creating accounts | 50 | Ready |
| `user-and-url.js` | Simulates users signing up and shortening a URL | 50 | Ready |
| `url-lifecycle.js` | Full URL lifecycle: create → edit → delete | 50 | Ready |
| `url-redirect.js` | Simulates users clicking shortened URLs | - | Planned |

---

## user-signup.js

Simulates new users signing up for the service.

**What it does:**
1. `POST /users` - Creates a new user account with username `k6_user_xxx`
2. `GET /users` - Fetches the user list (tests Redis caching under load)
3. Sleeps 1 second (simulates think time)
4. Repeats for the test duration

**Configuration (edit at top of file):**
```javascript
const VIRTUAL_USERS = 50;              // Concurrent users
const TEST_DURATION = '1m';            // Test length
const BASE_URL = 'http://localhost';   // Target server
```

**Run:**
```bash
k6 run k6/user-signup.js
```

**Success criteria:**
- 95th percentile latency < 200ms
- Error rate < 1%

---

## user-and-url.js

Simulates a complete user journey: signup and URL shortening.

**What it does:**
1. `POST /users` - Creates a new user account with username `k6_user_xxx`
2. `POST /shorten` - Submits a URL to be shortened using the new user's ID
3. Verifies the response contains a `short_code` and `short_url`
4. Sleeps 1 second (simulates think time)
5. Repeats for the test duration

**Configuration (edit at top of file):**
```javascript
const VIRTUAL_USERS = 50;              // Concurrent users
const TEST_DURATION = '1m';            // Test length
const BASE_URL = 'http://localhost';   // Target server
```

**Run:**
```bash
k6 run k6/user-and-url.js
```

**Success criteria:**
- 95th percentile latency < 300ms
- Error rate < 1%

---

## url-lifecycle.js

Simulates a complete URL lifecycle: create, edit, and delete.

**What it does:**
1. `POST /users` - Creates a new user account
2. `POST /shorten` - Creates a shortened URL
3. `POST /update` - Edits the URL (changes the title)
4. `POST /delete` - Deletes the URL
5. Sleeps, then repeats

**Configuration (edit at top of file):**
```javascript
const VIRTUAL_USERS = 50;              // Concurrent users
const TEST_DURATION = '1m';            // Test length
const BASE_URL = 'http://localhost';   // Target server
```

**Run:**
```bash
k6 run k6/url-lifecycle.js
```

**Success criteria:**
- 95th percentile latency < 400ms
- Error rate < 1%

**Note:** URLs are deleted during the test itself, so only test users remain for cleanup.

---

## Cleanup

After running tests, remove test data from the database:

```bash
# Docker (Linux/macOS)
docker compose exec postgres psql -U postgres -d hackathon_db -f /dev/stdin < k6/cleanup.sql

# Docker (Windows PowerShell)
Get-Content k6/cleanup.sql | docker compose exec -T postgres psql -U postgres -d hackathon_db

# Local PostgreSQL
psql -U postgres -d hackathon_db -f k6/cleanup.sql
```

Test users are identified by the `k6_user_` prefix and can be safely deleted without affecting real data.

---

## Viewing Results

### Terminal Output

k6 prints a summary after each test:

```
http_req_duration..............: avg=45ms  p(95)=150ms
http_req_failed................: 0.00%
http_reqs......................: 5000   83.33/s
vus............................: 50     min=50  max=50
```

### Grafana Dashboard

Monitor real-time metrics while tests run:

1. Open http://localhost:3000
2. Watch request rate, latency, and error rate
3. Compare against thresholds in `docs/CAPACITY.md`

---

## Quick Reference

```bash
# Check service is running
curl http://localhost/health

# Check current user count
curl http://localhost/stats

# Run user signup test
k6 run k6/user-signup.js

# Clean up test data (Windows PowerShell)
Get-Content k6/cleanup.sql | docker compose exec -T postgres psql -U postgres -d hackathon_db
```
