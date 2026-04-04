import http from 'k6/http';
import { check, sleep } from 'k6';

// =============================================================================
// CONFIGURATION - Adjust these values as needed
// =============================================================================
const VIRTUAL_USERS = 50;        // Number of concurrent users
const TEST_DURATION = '1m';      // How long the test runs (e.g., '30s', '1m', '5m')
const BASE_URL = 'http://localhost';  // Target URL (Docker: localhost, Local: localhost:5000)

// =============================================================================
// TEST OPTIONS
// =============================================================================
export const options = {
  vus: VIRTUAL_USERS,
  duration: TEST_DURATION,
  thresholds: {
    http_req_duration: ['p(95)<200'],  // 95% of requests should be < 200ms
    http_req_failed: ['rate<0.01'],    // Error rate should be < 1%
  },
};

// =============================================================================
// TEST SCENARIO: User Signup
//
// Simulates users signing up for the service:
// 1. POST /users - Create a new user account (k6_user_xxx)
// 2. GET /users  - Fetch the user list (tests caching)
// =============================================================================
export default function () {
  // Generate unique test user credentials
  const uniqueId = `${__VU}_${__ITER}_${Date.now()}`;
  const payload = JSON.stringify({
    username: `k6_user_${uniqueId}`,
    email: `k6_user_${uniqueId}@loadtest.local`,
  });

  const headers = { 'Content-Type': 'application/json' };

  // Step 1: Sign up - Create a new user
  const signupRes = http.post(`${BASE_URL}/users`, payload, { headers });
  check(signupRes, {
    'signup: status is 201': (r) => r.status === 201,
    'signup: response has user id': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.id !== undefined;
      } catch {
        return false;
      }
    },
  });

  // Step 2: Fetch users list (tests Redis caching under load)
  const listRes = http.get(`${BASE_URL}/users`);
  check(listRes, {
    'list users: status is 200': (r) => r.status === 200,
  });

  // Simulate user think time between actions
  sleep(1);
}

// =============================================================================
// LIFECYCLE HOOKS
// =============================================================================
export function setup() {
  // Verify the service is running before starting the test
  const healthRes = http.get(`${BASE_URL}/health`);
  if (healthRes.status !== 200) {
    throw new Error(`Service not healthy! Status: ${healthRes.status}`);
  }
  console.log(`Starting User Signup test with ${VIRTUAL_USERS} virtual users for ${TEST_DURATION}`);
}

export function teardown() {
  console.log('Test complete. Run cleanup.sql to remove test users from the database.');
}
