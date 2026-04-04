import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Scalability Bronze: 50 concurrent users, 60s duration
// Target: p95 < 3s, error rate < 10%

const errorRate = new Rate("errors");
const cacheHits = new Rate("cache_hits");
const healthLatency = new Trend("health_latency");

const BASE_URL = __ENV.BASE_URL || "http://localhost";
const JSON_HEADERS = { headers: { "Content-Type": "application/json" } };

export const options = {
  vus: 50,
  duration: "60s",
  thresholds: {
    http_req_duration: ["p(95)<3000"],
    errors: ["rate<0.1"],
  },
};

export function setup() {
  // Seed demo data before test
  const res = http.post(`${BASE_URL}/seed`);
  check(res, { "seed succeeded": (r) => r.status === 200 });

  // Get a user ID for shorten requests
  const users = http.get(`${BASE_URL}/users`);
  const parsed = JSON.parse(users.body);
  const userId = parsed && parsed.length > 0 ? parsed[0].id : 1;
  return { userId };
}

export default function (data) {
  const rand = Math.random();
  let res;

  if (rand < 0.25) {
    // GET /health
    res = http.get(`${BASE_URL}/health`);
    healthLatency.add(res.timings.duration);
  } else if (rand < 0.50) {
    // GET /users (cached)
    res = http.get(`${BASE_URL}/users`);
  } else if (rand < 0.70) {
    // GET /stats
    res = http.get(`${BASE_URL}/stats`);
  } else if (rand < 0.85) {
    // GET /ready
    res = http.get(`${BASE_URL}/ready`);
  } else {
    // POST /shorten — core feature
    const payload = JSON.stringify({
      user_id: data.userId,
      original_url: `https://example.com/load-test/${Date.now()}/${Math.floor(Math.random() * 100000)}`,
      title: `loadtest-${__VU}-${__ITER}`,
    });
    res = http.post(`${BASE_URL}/shorten`, payload, JSON_HEADERS);
  }

  const success = check(res, {
    "status is 2xx": (r) => r.status >= 200 && r.status < 300,
    "response time < 3s": (r) => r.timings.duration < 3000,
  });

  errorRate.add(!success);

  // Track cache hits from X-Cache header
  if (res.headers["X-Cache"] === "HIT") {
    cacheHits.add(1);
  } else {
    cacheHits.add(0);
  }

  sleep(0.5);
}
