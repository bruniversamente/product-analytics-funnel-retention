-- Activation funnel analysis.
-- Run after sql/01_create_schema_duckdb.sql.

WITH funnel_steps AS (
    SELECT 1 AS step_order, 'app_open' AS event_name, 'App open' AS step_label
    UNION ALL SELECT 2, 'signup_completed', 'Signup completed'
    UNION ALL SELECT 3, 'profile_completed', 'Profile completed'
    UNION ALL SELECT 4, 'search_performed', 'Search performed'
    UNION ALL SELECT 5, 'opportunity_viewed', 'Opportunity viewed'
    UNION ALL SELECT 6, 'invitation_sent', 'Invitation sent'
    UNION ALL SELECT 7, 'booking_confirmed', 'Booking confirmed'
),
step_users AS (
    SELECT
        steps.step_order,
        steps.step_label,
        COUNT(DISTINCT events.user_id) AS users_at_step
    FROM funnel_steps AS steps
    LEFT JOIN fact_events AS events
        ON steps.event_name = events.event_name
    GROUP BY steps.step_order, steps.step_label
),
with_previous AS (
    SELECT
        step_order,
        step_label,
        users_at_step,
        LAG(users_at_step) OVER (ORDER BY step_order) AS previous_step_users,
        FIRST_VALUE(users_at_step) OVER (ORDER BY step_order) AS first_step_users
    FROM step_users
)
SELECT
    step_order,
    step_label,
    users_at_step,
    ROUND(users_at_step / NULLIF(first_step_users, 0), 4) AS conversion_from_start,
    ROUND(users_at_step / NULLIF(previous_step_users, 0), 4) AS conversion_from_previous,
    ROUND(1 - users_at_step / NULLIF(previous_step_users, 0), 4) AS loss_from_previous
FROM with_previous
ORDER BY step_order;

-- Funnel by acquisition channel
WITH funnel_steps AS (
    SELECT 1 AS step_order, 'app_open' AS event_name, 'App open' AS step_label
    UNION ALL SELECT 2, 'signup_completed', 'Signup completed'
    UNION ALL SELECT 3, 'profile_completed', 'Profile completed'
    UNION ALL SELECT 4, 'search_performed', 'Search performed'
    UNION ALL SELECT 5, 'opportunity_viewed', 'Opportunity viewed'
    UNION ALL SELECT 6, 'invitation_sent', 'Invitation sent'
    UNION ALL SELECT 7, 'booking_confirmed', 'Booking confirmed'
)
SELECT
    users.acquisition_channel,
    steps.step_order,
    steps.step_label,
    COUNT(DISTINCT events.user_id) AS users_at_step
FROM funnel_steps AS steps
LEFT JOIN fact_events AS events
    ON steps.event_name = events.event_name
LEFT JOIN dim_users AS users
    ON events.user_id = users.user_id
GROUP BY users.acquisition_channel, steps.step_order, steps.step_label
ORDER BY users.acquisition_channel, steps.step_order;
