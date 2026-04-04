import http from 'k6/http';
import { check, sleep } from 'k6';

// =============================================================================
// CONFIGURATION - Adjust these values as needed
// =============================================================================
const VIRTUAL_USERS = 600;       // Number of concurrent users
const TEST_DURATION = '1m';      // How long the test runs (e.g., '30s', '1m', '5m')
const BASE_URL = 'http://localhost';  // Target URL (Docker: localhost, Local: localhost:5000)
const CONCURRENT_RESOLVES = 5;   // Number of concurrent requests to resolve the same short URL

// =============================================================================
// TEST OPTIONS
// =============================================================================
export const options = {
  stages: [
    { duration: '15s', target: VIRTUAL_USERS },  // Ramp up to 200 VUs over 15s
    { duration: '45s', target: VIRTUAL_USERS },  // Stay at 200 VUs for 45s
  ],
  thresholds: {
    http_req_duration: ['p(95)<300'],  // 95% of requests should be < 300ms
    http_req_failed: ['rate<0.04'],    // Error rate should be < 4%
  },
};

// =============================================================================
// TEST SCENARIO: URL Creation + Concurrent Resolution
//
// Simulates:
// 1. POST /users   - Create a new user account
// 2. POST /shorten - Create a shortened URL, receive short_code
// 3. GET /<short_code>/info (x5 concurrent) - Resolve the short URL to original
//
// This tests how well the system handles multiple concurrent requests
// for the same resource (simulating a popular/viral short link).
// =============================================================================
export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // Generate unique identifiers for this iteration
  const uniqueId = `${__VU}_${__ITER}_${Date.now()}`;

  // -------------------------------------------------------------------------
  // Step 1: Create a user
  // -------------------------------------------------------------------------
  const userPayload = JSON.stringify({
    username: `k6_user_${uniqueId}`,
    email: `k6_user_${uniqueId}@loadtest.local`,
  });

  const signupRes = http.post(`${BASE_URL}/users`, userPayload, { headers });

  const signupSuccess = check(signupRes, {
    'create user: status is 201': (r) => r.status === 201,
  });

  if (!signupSuccess) {
    console.log(`User creation failed: ${signupRes.status} - ${signupRes.body}`);
    return;
  }

  const userId = JSON.parse(signupRes.body).id;

  // -------------------------------------------------------------------------
  // Step 2: Create a shortened URL
  // -------------------------------------------------------------------------
  const createUrlPayload = JSON.stringify({
    user_id: userId,
    original_url: `https://example.com/article/${uniqueId}`,
    title: `Test URL ${uniqueId}`,
  });

  const createRes = http.post(`${BASE_URL}/shorten`, createUrlPayload, { headers });

  const createSuccess = check(createRes, {
    'create url: status is 201': (r) => r.status === 201,
    'create url: has short_code': (r) => {
      try {
        return JSON.parse(r.body).short_code !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (!createSuccess) {
    console.log(`URL creation failed: ${createRes.status} - ${createRes.body}`);
    return;
  }

  const shortCode = JSON.parse(createRes.body).short_code;

  // -------------------------------------------------------------------------
  // Step 3: Resolve the short URL concurrently (5 simultaneous requests)
  // -------------------------------------------------------------------------
  // Build batch request array - all hitting the same short URL
  const batchRequests = [];
  for (let i = 0; i < CONCURRENT_RESOLVES; i++) {
    batchRequests.push(['GET', `${BASE_URL}/s/${shortCode}/info`, null, { tags: { name: 'resolve_url' } }]);
  }

  // Execute all requests concurrently
  const responses = http.batch(batchRequests);

  // Check all responses
  let allSuccessful = true;
  responses.forEach((res, index) => {
    const success = check(res, {
      [`resolve ${index + 1}: status is 200`]: (r) => r.status === 200,
      [`resolve ${index + 1}: returns original_url`]: (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.original_url !== undefined && body.original_url.includes('example.com');
        } catch {
          return false;
        }
      },
    });
    if (!success) allSuccessful = false;
  });

  if (!allSuccessful) {
    console.log(`Some resolve requests failed for short_code: ${shortCode}`);
  }

  // Simulate user think time before next iteration
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
  console.log(`Starting URL Resolve test with ${VIRTUAL_USERS} virtual users for ${TEST_DURATION}`);
  console.log(`Each iteration: Create URL → ${CONCURRENT_RESOLVES} concurrent resolve requests`);
}

export function teardown() {
  console.log('Test complete. Run cleanup.sql to remove test data from the database.');
}
