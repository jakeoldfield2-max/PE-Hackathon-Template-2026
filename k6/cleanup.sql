-- =============================================================================
-- k6 Load Test Cleanup Script
-- =============================================================================
-- Removes all test data created by k6 load tests.
-- Test users are identified by the 'k6_user_' prefix.
-- Also cleans up related URLs and events.
--
-- Usage (Docker - Linux/macOS):
--   docker compose exec postgres psql -U postgres -d hackathon_db -f /dev/stdin < k6/cleanup.sql
--
-- Usage (Docker - Windows PowerShell):
--   Get-Content k6/cleanup.sql | docker compose exec -T postgres psql -U postgres -d hackathon_db
--
-- Usage (Local PostgreSQL):
--   psql -U postgres -d hackathon_db -f k6/cleanup.sql
-- =============================================================================

-- Show counts before cleanup
SELECT '=== BEFORE CLEANUP ===' AS status;
SELECT
    (SELECT COUNT(*) FROM users) AS total_users,
    (SELECT COUNT(*) FROM users WHERE username LIKE 'k6_user_%') AS k6_users,
    (SELECT COUNT(*) FROM urls) AS total_urls,
    (SELECT COUNT(*) FROM events) AS total_events;

-- Delete in order: events -> urls -> users (respects foreign keys)
-- Step 1: Delete events linked to k6 test users
DELETE FROM events
WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'k6_user_%');

-- Step 2: Delete urls linked to k6 test users
DELETE FROM urls
WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'k6_user_%');

-- Step 3: Delete k6 test users
DELETE FROM users WHERE username LIKE 'k6_user_%';

-- Show counts after cleanup
SELECT '=== AFTER CLEANUP ===' AS status;
SELECT
    (SELECT COUNT(*) FROM users) AS total_users,
    (SELECT COUNT(*) FROM users WHERE username LIKE 'k6_user_%') AS k6_users,
    (SELECT COUNT(*) FROM urls) AS total_urls,
    (SELECT COUNT(*) FROM events) AS total_events;
