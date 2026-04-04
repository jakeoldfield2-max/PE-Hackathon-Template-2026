import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Scalability Gold: 500 concurrent users, staged ramp
// Target: p95 < 5s, error rate < 5%, cache hit > 90%

const errorRate = new Rate("errors");
const cacheHits = new Rate("cache_hits");
const dbLatency = new Trend("db_endpoint_latency");

const BASE_URL = __ENV.BASE_URL || "http://localhost";
const JSON_HEADERS = { headers: { "Content-Type": "application/json" } };

export const options = {
  stages: [
    { duration: "15s", target: 100 },  // Warm up
    { duration: "15s", target: 250 },  // Ramp
    { duration: "15s", target: 500 },  // Peak
    { duration: "30s", target: 500 },  // Hold at 500
    { duration: "15s", target: 0 },    // Cool down
  ],
  thresholds: {
    http_req_duration: ["p(95)<5000"],
    errors: ["rate<0.05"],
    cache_hits: ["rate>0.9"],
  },
};

export function setup() {
  const res = http.post(`${BASE_URL}/seed`);
  check(res, { "seed succeeded": (r) => r.status === 200 });

  const users = http.get(`${BASE_URL}/users`);
  const parsed = JSON.parse(users.body);
  const userId = parsed && parsed.length > 0 ? parsed[0].id : 1;

  // Warm the cache — hit cached endpoints before the test
  for (let i = 0; i < 10; i++) {
    http.get(`${BASE_URL}/users`);
    http.get(`${BASE_URL}/users/${userId}`);
  }

  return { userId };
}

export default function (data) {
  const rand = Math.random();
  let res;

  if (rand < 0.40) {
    // GET /users — heavy cache traffic to prove Redis effectiveness
    res = http.get(`${BASE_URL}/users`);
    dbLatency.add(res.timings.duration);
  } else if (rand < 0.55) {
    // GET /users/<id> (cached)
    res = http.get(`${BASE_URL}/users/${data.userId}`);
    dbLatency.add(res.timings.duration);
  } else if (rand < 0.70) {
    // GET /stats
    res = http.get(`${BASE_URL}/stats`);
  } else if (rand < 0.80) {
    // GET /health
    res = http.get(`${BASE_URL}/health`);
  } else if (rand < 0.88) {
    // GET /ready
    res = http.get(`${BASE_URL}/ready`);
  } else if (rand < 0.96) {
    // POST /shorten — core feature under load
    const payload = JSON.stringify({
      user_id: data.userId,
      original_url: `https://example.com/tsunami/${Date.now()}/${Math.floor(Math.random() * 100000)}`,
      title: `tsunami-${__VU}-${__ITER}`,
    });
    res = http.post(`${BASE_URL}/shorten`, payload, JSON_HEADERS);
  } else {
    // POST /users — write pressure + cache invalidation
    const payload = JSON.stringify({
      username: `tsunami_${Date.now()}_${Math.floor(Math.random() * 100000)}`,
      email: `tsunami_${Date.now()}@test.com`,
    });
    res = http.post(`${BASE_URL}/users`, payload, JSON_HEADERS);
  }

  const success = check(res, {
    "status is 2xx": (r) => r.status >= 200 && r.status < 300,
    "response time < 5s": (r) => r.timings.duration < 5000,
  });

  errorRate.add(!success);

  if (res.headers["X-Cache"] === "HIT") {
    cacheHits.add(1);
  } else {
    cacheHits.add(0);
  }

  sleep(0.2);
}
