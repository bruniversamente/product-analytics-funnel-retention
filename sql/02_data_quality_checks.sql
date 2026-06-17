-- Data quality checks for the product analytics model.
-- Run after sql/01_create_schema_duckdb.sql.

-- 1. Duplicated event IDs
SELECT
    event_id,
    COUNT(*) AS occurrences
FROM fact_events
GROUP BY event_id
HAVING COUNT(*) > 1;

-- 2. Events without a valid user
SELECT
    events.event_id,
    events.user_id,
    events.event_name
FROM fact_events AS events
LEFT JOIN dim_users AS users
    ON events.user_id = users.user_id
WHERE users.user_id IS NULL;

-- 3. Events outside the approved taxonomy
SELECT DISTINCT event_name
FROM fact_events
WHERE event_name NOT IN (
    'app_open',
    'signup_completed',
    'profile_completed',
    'search_performed',
    'opportunity_viewed',
    'invitation_sent',
    'booking_confirmed'
);

-- 4. Opportunity events missing opportunity ID
SELECT
    event_id,
    user_id,
    event_name,
    event_timestamp
FROM fact_events
WHERE event_name IN ('search_performed', 'opportunity_viewed', 'invitation_sent', 'booking_confirmed')
  AND (opportunity_id IS NULL OR opportunity_id = '');

-- 5. Events before signup date
SELECT
    events.event_id,
    events.user_id,
    events.event_timestamp,
    users.signup_date
FROM fact_events AS events
LEFT JOIN dim_users AS users
    ON events.user_id = users.user_id
WHERE CAST(events.event_timestamp AS DATE) < users.signup_date;

-- 6. Row count summary
SELECT 'dim_users' AS table_name, COUNT(*) AS row_count FROM dim_users
UNION ALL
SELECT 'fact_events', COUNT(*) FROM fact_events
UNION ALL
SELECT 'fact_marketplace_actions', COUNT(*) FROM fact_marketplace_actions;
