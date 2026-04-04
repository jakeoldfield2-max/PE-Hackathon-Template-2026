import http from 'k6/http';
import { check, sleep } from 'k6';

// =============================================================================
// CONFIGURATION - Adjust these values as needed
// =============================================================================
const VIRTUAL_USERS = 800;       // Number of concurrent users
const TEST_DURATION = '1m';      // How long the test runs (e.g., '30s', '1m', '5m')
const BASE_URL = 'http://localhost';  // Target URL (Docker: localhost, Local: localhost:5000)

// =============================================================================
// TEST OPTIONS
// =============================================================================
export const options = {
  stages: [
    { duration: '10s', target: VIRTUAL_USERS },  // Ramp up to target VUs over 10s
    { duration: '50s', target: VIRTUAL_USERS },  // Stay at target VUs for 50s
  ],
  thresholds: {
    http_req_duration: ['p(95)<300'],  // 95% of requests should be < 300ms
    http_req_failed: ['rate<0.04'],    // Error rate should be < 4%
  },
};

// =============================================================================
// TEST SCENARIO: User Signup + URL Shortening
//
// Simulates a complete user journey:
// 1. POST /users   - Create a new user account
// 2. POST /shorten - Submit a URL to be shortened
// 3. Verify the shortened URL is returned
// =============================================================================
export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // Generate unique identifiers for this iteration
  const uniqueId = `${__VU}_${__ITER}_${Date.now()}`;

  // -------------------------------------------------------------------------
  // Step 1: Sign up - Create a new user
  // -------------------------------------------------------------------------
  const userPayload = JSON.stringify({
    username: `k6_user_${uniqueId}`,
    email: `k6_user_${uniqueId}@loadtest.local`,
  });

  const signupRes = http.post(`${BASE_URL}/users`, userPayload, { headers });

  const signupSuccess = check(signupRes, {
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

  // If signup failed, skip the rest of this iteration
  if (!signupSuccess) {
    console.log(`Signup failed: ${signupRes.status} - ${signupRes.body}`);
    return;
  }

  // Extract user ID from response
  const userId = JSON.parse(signupRes.body).id;

  // -------------------------------------------------------------------------
  // Step 2: Shorten URL - Submit a URL to be shortened
  // -------------------------------------------------------------------------
  const urlPayload = JSON.stringify({
    user_id: userId,
    original_url: `https://example.com/page/${uniqueId}`,
    title: `Test URL ${uniqueId}`,
  });

  const shortenRes = http.post(`${BASE_URL}/shorten`, urlPayload, { headers });

  check(shortenRes, {
    'shorten: status is 201': (r) => r.status === 201,
    'shorten: response has short_code': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.short_code !== undefined && body.short_code.length > 0;
      } catch {
        return false;
      }
    },
    'shorten: response has short_url': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.short_url !== undefined && body.short_url.includes('http');
      } catch {
        return false;
      }
    },
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
  console.log(`Starting User + URL test with ${VIRTUAL_USERS} virtual users for ${TEST_DURATION}`);
}

export function teardown() {
  console.log('Test complete. Run cleanup.sql to remove test data from the database.');
}
