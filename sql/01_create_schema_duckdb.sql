-- Creates analytical tables from the synthetic CSV files.
-- Engine: DuckDB

CREATE OR REPLACE TABLE dim_users AS
SELECT
    user_id,
    CAST(signup_date AS DATE) AS signup_date,
    persona,
    region,
    acquisition_channel,
    platform
FROM read_csv_auto('data/generated/users.csv');

CREATE OR REPLACE TABLE fact_events AS
SELECT
    event_id,
    user_id,
    CAST(event_timestamp AS TIMESTAMP) AS event_timestamp,
    CAST(event_timestamp AS DATE) AS event_date,
    event_name,
    session_id,
    platform,
    acquisition_channel,
    opportunity_id,
    category
FROM read_csv_auto('data/generated/events.csv');

CREATE OR REPLACE TABLE fact_marketplace_actions AS
SELECT
    opportunity_id,
    category,
    CAST(created_at AS TIMESTAMP) AS created_at,
    host_user_id,
    guest_user_id,
    CAST(invitation_sent_at AS TIMESTAMP) AS invitation_sent_at,
    CAST(booking_confirmed_at AS TIMESTAMP) AS booking_confirmed_at,
    status
FROM read_csv_auto('data/generated/marketplace_actions.csv');

CREATE OR REPLACE VIEW vw_events_enriched AS
SELECT
    events.*,
    users.signup_date,
    users.persona,
    users.region,
    DATE_DIFF('day', users.signup_date, events.event_date) AS days_since_signup
FROM fact_events AS events
LEFT JOIN dim_users AS users
    ON events.user_id = users.user_id;
