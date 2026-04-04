import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

// Scalability Silver: 200 concurrent users, staged ramp
// Target: p95 < 3s, error rate < 5%

const errorRate = new Rate("errors");
const cacheHits = new Rate("cache_hits");

const BASE_URL = __ENV.BASE_URL || "http://localhost";
const JSON_HEADERS = { headers: { "Content-Type": "application/json" } };

export const options = {
  stages: [
    { duration: "15s", target: 50 },   // Warm up
    { duration: "30s", target: 200 },  // Ramp to 200
    { duration: "30s", target: 200 },  // Hold at 200
    { duration: "15s", target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<3000"],
    errors: ["rate<0.05"],
  },
};

export function setup() {
  const res = http.post(`${BASE_URL}/seed`);
  check(res, { "seed succeeded": (r) => r.status === 200 });

  const users = http.get(`${BASE_URL}/users`);
  const parsed = JSON.parse(users.body);
  const userId = parsed && parsed.length > 0 ? parsed[0].id : 1;
  return { userId };
}

export default function (data) {
  const rand = Math.random();
  let res;

  if (rand < 0.30) {
    // GET /users (cached — high read traffic)
    res = http.get(`${BASE_URL}/users`);
  } else if (rand < 0.50) {
    // GET /stats
    res = http.get(`${BASE_URL}/stats`);
  } else if (rand < 0.65) {
    // GET /health
    res = http.get(`${BASE_URL}/health`);
  } else if (rand < 0.75) {
    // GET /ready
    res = http.get(`${BASE_URL}/ready`);
  } else if (rand < 0.80) {
    // GET /users/<id>
    res = http.get(`${BASE_URL}/users/${data.userId}`);
  } else if (rand < 0.92) {
    // POST /shorten — core feature
    const payload = JSON.stringify({
      user_id: data.userId,
      original_url: `https://example.com/scale/${Date.now()}/${Math.floor(Math.random() * 100000)}`,
      title: `scale-${__VU}-${__ITER}`,
    });
    res = http.post(`${BASE_URL}/shorten`, payload, JSON_HEADERS);
  } else {
    // POST /users — create user (write traffic)
    const payload = JSON.stringify({
      username: `scale_${Date.now()}_${Math.floor(Math.random() * 100000)}`,
      email: `scale_${Date.now()}@test.com`,
    });
    res = http.post(`${BASE_URL}/users`, payload, JSON_HEADERS);
  }

  const success = check(res, {
    "status is 2xx": (r) => r.status >= 200 && r.status < 300,
    "response time < 3s": (r) => r.timings.duration < 3000,
  });

  errorRate.add(!success);

  if (res.headers["X-Cache"] === "HIT") {
    cacheHits.add(1);
  } else {
    cacheHits.add(0);
  }

  sleep(0.3);
}
