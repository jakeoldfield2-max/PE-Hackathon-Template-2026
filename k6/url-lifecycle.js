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
    http_req_duration: ['p(95)<400'],  // 95% of requests should be < 400ms
    http_req_failed: ['rate<0.01'],    // Error rate should be < 1%
  },
};

// =============================================================================
// TEST SCENARIO: URL Lifecycle (Create → Edit → Delete)
//
// Simulates a complete URL lifecycle:
// 1. POST /users   - Create a new user account
// 2. POST /shorten - Create a new shortened URL
// 3. POST /update  - Edit the URL (change title)
// 4. POST /delete  - Delete the URL
// =============================================================================
export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // Generate unique identifiers for this iteration
  const uniqueId = `${__VU}_${__ITER}_${Date.now()}`;
  const urlTitle = `Test URL ${uniqueId}`;

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
  // Step 2: Create a URL
  // -------------------------------------------------------------------------
  const createUrlPayload = JSON.stringify({
    user_id: userId,
    original_url: `https://example.com/original/${uniqueId}`,
    title: urlTitle,
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

  const urlId = JSON.parse(createRes.body).id;

  sleep(0.5); // Brief pause between operations

  // -------------------------------------------------------------------------
  // Step 3: Edit the URL (update the title)
  // -------------------------------------------------------------------------
  const updatedTitle = `Updated ${urlTitle}`;
  const updatePayload = JSON.stringify({
    user_id: userId,
    url_id: urlId,
    field: 'title',
    new_value: updatedTitle,
  });

  const updateRes = http.post(`${BASE_URL}/update`, updatePayload, { headers });

  const updateSuccess = check(updateRes, {
    'update url: status is 200': (r) => r.status === 200,
    'update url: confirms update': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.message === 'URL updated successfully';
      } catch {
        return false;
      }
    },
  });

  if (!updateSuccess) {
    console.log(`URL update failed: ${updateRes.status} - ${updateRes.body}`);
  }

  sleep(0.5); // Brief pause between operations

  // -------------------------------------------------------------------------
  // Step 4: Delete the URL
  // -------------------------------------------------------------------------
  const deletePayload = JSON.stringify({
    user_id: userId,
    title: updatedTitle,  // Use the updated title since we changed it
  });

  const deleteRes = http.post(`${BASE_URL}/delete`, deletePayload, { headers });

  check(deleteRes, {
    'delete url: status is 200': (r) => r.status === 200,
    'delete url: confirms deletion': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.message === 'URL deleted successfully';
      } catch {
        return false;
      }
    },
  });

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
  console.log(`Starting URL Lifecycle test with ${VIRTUAL_USERS} virtual users for ${TEST_DURATION}`);
  console.log('Flow: Create User → Create URL → Edit URL → Delete URL');
}

export function teardown() {
  console.log('Test complete. Run cleanup.sql to remove test users from the database.');
  console.log('Note: URLs are deleted during the test, but test users remain.');
}
