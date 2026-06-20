-- Retention cohort analysis.
-- Run after sql/01_create_schema_duckdb.sql.
--
-- Retention is measured as a return app_open after signup. This avoids
-- counting activation-journey events as retention.

WITH ordered_activation AS (
    SELECT
        users.user_id,
        CASE WHEN COUNT(CASE WHEN events.event_name = 'booking_confirmed' THEN 1 END) > 0
            THEN 'Ativados'
            ELSE 'Não ativados'
        END AS activation_status
    FROM dim_users AS users
    LEFT JOIN fact_events AS events
        ON users.user_id = events.user_id
    GROUP BY users.user_id
),
activity AS (
    SELECT
        user_id,
        MAX(CASE WHEN event_name = 'app_open' AND days_since_signup = 1 THEN 1 ELSE 0 END) AS retained_d1,
        MAX(CASE WHEN event_name = 'app_open' AND days_since_signup = 7 THEN 1 ELSE 0 END) AS retained_d7,
        MAX(CASE WHEN event_name = 'app_open' AND days_since_signup = 30 THEN 1 ELSE 0 END) AS retained_d30
    FROM vw_events_enriched
    GROUP BY user_id
)
SELECT
    ordered_activation.activation_status,
    COUNT(users.user_id) AS users,
    ROUND(AVG(COALESCE(activity.retained_d1, 0)), 4) AS retention_d1,
    ROUND(AVG(COALESCE(activity.retained_d7, 0)), 4) AS retention_d7,
    ROUND(AVG(COALESCE(activity.retained_d30, 0)), 4) AS retention_d30
FROM dim_users AS users
LEFT JOIN ordered_activation
    ON users.user_id = ordered_activation.user_id
LEFT JOIN activity
    ON users.user_id = activity.user_id
GROUP BY ordered_activation.activation_status
ORDER BY ordered_activation.activation_status;

-- Monthly signup cohort retention by week.
WITH cohort_activity AS (
    SELECT
        users.user_id,
        STRFTIME(users.signup_date, '%Y-%m') AS signup_month,
        FLOOR(DATE_DIFF('day', users.signup_date, events.event_date) / 7) AS week_number
    FROM dim_users AS users
    LEFT JOIN fact_events AS events
        ON users.user_id = events.user_id
    WHERE events.event_date >= users.signup_date
      AND events.event_name = 'app_open'
      AND FLOOR(DATE_DIFF('day', users.signup_date, events.event_date) / 7) BETWEEN 0 AND 4
),
cohort_size AS (
    SELECT
        STRFTIME(signup_date, '%Y-%m') AS signup_month,
        COUNT(DISTINCT user_id) AS users_in_cohort
    FROM dim_users
    GROUP BY STRFTIME(signup_date, '%Y-%m')
)
SELECT
    activity.signup_month,
    CAST(activity.week_number AS INTEGER) AS week_number,
    COUNT(DISTINCT activity.user_id) AS active_users,
    cohort_size.users_in_cohort,
    ROUND(COUNT(DISTINCT activity.user_id) / NULLIF(cohort_size.users_in_cohort, 0), 4) AS retention_rate
FROM cohort_activity AS activity
LEFT JOIN cohort_size
    ON activity.signup_month = cohort_size.signup_month
GROUP BY activity.signup_month, activity.week_number, cohort_size.users_in_cohort
ORDER BY activity.signup_month, activity.week_number;
