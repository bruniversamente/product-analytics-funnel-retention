-- Marketplace efficiency metrics.
-- Run after sql/01_create_schema_duckdb.sql.

-- Opportunity status by category
SELECT
    category,
    status,
    COUNT(*) AS opportunities
FROM fact_marketplace_actions
GROUP BY category, status
ORDER BY category, status;

-- Confirmation rate by category
SELECT
    category,
    COUNT(*) AS opportunities,
    COUNT(CASE WHEN invitation_sent_at IS NOT NULL THEN 1 END) AS invitations_sent,
    COUNT(CASE WHEN booking_confirmed_at IS NOT NULL THEN 1 END) AS confirmed_bookings,
    ROUND(
        COUNT(CASE WHEN booking_confirmed_at IS NOT NULL THEN 1 END)
        / NULLIF(COUNT(CASE WHEN invitation_sent_at IS NOT NULL THEN 1 END), 0),
        4
    ) AS confirmation_rate
FROM fact_marketplace_actions
GROUP BY category
ORDER BY confirmation_rate DESC NULLS LAST;

-- Time to confirmation
SELECT
    opportunity_id,
    category,
    invitation_sent_at,
    booking_confirmed_at,
    DATE_DIFF('hour', invitation_sent_at, booking_confirmed_at) AS time_to_confirmation_hours
FROM fact_marketplace_actions
WHERE invitation_sent_at IS NOT NULL
  AND booking_confirmed_at IS NOT NULL
ORDER BY time_to_confirmation_hours;

-- Marketplace summary
SELECT
    COUNT(*) AS total_opportunities,
    COUNT(CASE WHEN invitation_sent_at IS NOT NULL THEN 1 END) AS invitations_sent,
    COUNT(CASE WHEN booking_confirmed_at IS NOT NULL THEN 1 END) AS confirmed_bookings,
    ROUND(
        COUNT(CASE WHEN booking_confirmed_at IS NOT NULL THEN 1 END)
        / NULLIF(COUNT(CASE WHEN invitation_sent_at IS NOT NULL THEN 1 END), 0),
        4
    ) AS confirmation_rate,
    ROUND(AVG(DATE_DIFF('hour', invitation_sent_at, booking_confirmed_at)), 2) AS avg_time_to_confirmation_hours
FROM fact_marketplace_actions
WHERE invitation_sent_at IS NOT NULL;
