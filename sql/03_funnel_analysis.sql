-- Ordered activation funnel analysis.
-- Run after sql/01_create_schema_duckdb.sql.
--
-- Why ordered?
-- A simple count of users per event can overstate conversion because it does
-- not prove that the user followed the intended journey. This query counts a
-- user at each step only when the previous step happened earlier in time.

WITH step_1 AS (
    SELECT
        users.user_id,
        users.acquisition_channel,
        users.platform,
        users.persona,
        users.region,
        users.signup_date,
        MIN(events.event_timestamp) AS app_open_at
    FROM dim_users AS users
    LEFT JOIN fact_events AS events
        ON users.user_id = events.user_id
        AND events.event_name = 'app_open'
    GROUP BY
        users.user_id,
        users.acquisition_channel,
        users.platform,
        users.persona,
        users.region,
        users.signup_date
),
step_2 AS (
    SELECT
        step_1.*,
        MIN(events.event_timestamp) AS signup_completed_at
    FROM step_1
    LEFT JOIN fact_events AS events
        ON step_1.user_id = events.user_id
        AND events.event_name = 'signup_completed'
        AND events.event_timestamp >= step_1.app_open_at
    GROUP BY ALL
),
step_3 AS (
    SELECT
        step_2.*,
        MIN(events.event_timestamp) AS profile_completed_at
    FROM step_2
    LEFT JOIN fact_events AS events
        ON step_2.user_id = events.user_id
        AND events.event_name = 'profile_completed'
        AND events.event_timestamp >= step_2.signup_completed_at
    GROUP BY ALL
),
step_4 AS (
    SELECT
        step_3.*,
        MIN(events.event_timestamp) AS search_performed_at
    FROM step_3
    LEFT JOIN fact_events AS events
        ON step_3.user_id = events.user_id
        AND events.event_name = 'search_performed'
        AND events.event_timestamp >= step_3.profile_completed_at
    GROUP BY ALL
),
step_5 AS (
    SELECT
        step_4.*,
        MIN(events.event_timestamp) AS opportunity_viewed_at
    FROM step_4
    LEFT JOIN fact_events AS events
        ON step_4.user_id = events.user_id
        AND events.event_name = 'opportunity_viewed'
        AND events.event_timestamp >= step_4.search_performed_at
    GROUP BY ALL
),
step_6 AS (
    SELECT
        step_5.*,
        MIN(events.event_timestamp) AS invitation_sent_at
    FROM step_5
    LEFT JOIN fact_events AS events
        ON step_5.user_id = events.user_id
        AND events.event_name = 'invitation_sent'
        AND events.event_timestamp >= step_5.opportunity_viewed_at
    GROUP BY ALL
),
user_ordered_funnel AS (
    SELECT
        step_6.*,
        MIN(events.event_timestamp) AS booking_confirmed_at
    FROM step_6
    LEFT JOIN fact_events AS events
        ON step_6.user_id = events.user_id
        AND events.event_name = 'booking_confirmed'
        AND events.event_timestamp >= step_6.invitation_sent_at
    GROUP BY ALL
),
steps AS (
    SELECT 1 AS step_order, 'Abertura do app' AS step_label, COUNT(app_open_at) AS users_at_step FROM user_ordered_funnel
    UNION ALL SELECT 2, 'Cadastro concluído', COUNT(signup_completed_at) FROM user_ordered_funnel
    UNION ALL SELECT 3, 'Perfil completo', COUNT(profile_completed_at) FROM user_ordered_funnel
    UNION ALL SELECT 4, 'Busca realizada', COUNT(search_performed_at) FROM user_ordered_funnel
    UNION ALL SELECT 5, 'Oportunidade vista', COUNT(opportunity_viewed_at) FROM user_ordered_funnel
    UNION ALL SELECT 6, 'Convite enviado', COUNT(invitation_sent_at) FROM user_ordered_funnel
    UNION ALL SELECT 7, 'Reserva confirmada', COUNT(booking_confirmed_at) FROM user_ordered_funnel
),
calc AS (
    SELECT
        step_order,
        step_label,
        users_at_step,
        FIRST_VALUE(users_at_step) OVER (ORDER BY step_order) AS first_step_users,
        LAG(users_at_step) OVER (ORDER BY step_order) AS previous_step_users
    FROM steps
)
SELECT
    step_order,
    step_label,
    users_at_step,
    ROUND(users_at_step / NULLIF(first_step_users, 0), 4) AS conversion_from_start,
    ROUND(users_at_step / NULLIF(previous_step_users, 0), 4) AS conversion_from_previous,
    ROUND(1 - users_at_step / NULLIF(previous_step_users, 0), 4) AS loss_from_previous
FROM calc
ORDER BY step_order;

-- Ordered funnel by acquisition channel.
WITH step_1 AS (
    SELECT
        users.user_id,
        users.acquisition_channel,
        MIN(events.event_timestamp) AS app_open_at
    FROM dim_users AS users
    LEFT JOIN fact_events AS events
        ON users.user_id = events.user_id
        AND events.event_name = 'app_open'
    GROUP BY users.user_id, users.acquisition_channel
),
step_2 AS (
    SELECT step_1.*, MIN(events.event_timestamp) AS signup_completed_at
    FROM step_1
    LEFT JOIN fact_events AS events
        ON step_1.user_id = events.user_id
        AND events.event_name = 'signup_completed'
        AND events.event_timestamp >= step_1.app_open_at
    GROUP BY ALL
),
step_3 AS (
    SELECT step_2.*, MIN(events.event_timestamp) AS profile_completed_at
    FROM step_2
    LEFT JOIN fact_events AS events
        ON step_2.user_id = events.user_id
        AND events.event_name = 'profile_completed'
        AND events.event_timestamp >= step_2.signup_completed_at
    GROUP BY ALL
),
step_4 AS (
    SELECT step_3.*, MIN(events.event_timestamp) AS search_performed_at
    FROM step_3
    LEFT JOIN fact_events AS events
        ON step_3.user_id = events.user_id
        AND events.event_name = 'search_performed'
        AND events.event_timestamp >= step_3.profile_completed_at
    GROUP BY ALL
),
step_5 AS (
    SELECT step_4.*, MIN(events.event_timestamp) AS opportunity_viewed_at
    FROM step_4
    LEFT JOIN fact_events AS events
        ON step_4.user_id = events.user_id
        AND events.event_name = 'opportunity_viewed'
        AND events.event_timestamp >= step_4.search_performed_at
    GROUP BY ALL
),
step_6 AS (
    SELECT step_5.*, MIN(events.event_timestamp) AS invitation_sent_at
    FROM step_5
    LEFT JOIN fact_events AS events
        ON step_5.user_id = events.user_id
        AND events.event_name = 'invitation_sent'
        AND events.event_timestamp >= step_5.opportunity_viewed_at
    GROUP BY ALL
),
user_ordered_funnel AS (
    SELECT step_6.*, MIN(events.event_timestamp) AS booking_confirmed_at
    FROM step_6
    LEFT JOIN fact_events AS events
        ON step_6.user_id = events.user_id
        AND events.event_name = 'booking_confirmed'
        AND events.event_timestamp >= step_6.invitation_sent_at
    GROUP BY ALL
),
channel_steps AS (
    SELECT acquisition_channel, 1 AS step_order, 'Abertura do app' AS step_label, COUNT(app_open_at) AS users_at_step FROM user_ordered_funnel GROUP BY acquisition_channel
    UNION ALL SELECT acquisition_channel, 2, 'Cadastro concluído', COUNT(signup_completed_at) FROM user_ordered_funnel GROUP BY acquisition_channel
    UNION ALL SELECT acquisition_channel, 3, 'Perfil completo', COUNT(profile_completed_at) FROM user_ordered_funnel GROUP BY acquisition_channel
    UNION ALL SELECT acquisition_channel, 4, 'Busca realizada', COUNT(search_performed_at) FROM user_ordered_funnel GROUP BY acquisition_channel
    UNION ALL SELECT acquisition_channel, 5, 'Oportunidade vista', COUNT(opportunity_viewed_at) FROM user_ordered_funnel GROUP BY acquisition_channel
    UNION ALL SELECT acquisition_channel, 6, 'Convite enviado', COUNT(invitation_sent_at) FROM user_ordered_funnel GROUP BY acquisition_channel
    UNION ALL SELECT acquisition_channel, 7, 'Reserva confirmada', COUNT(booking_confirmed_at) FROM user_ordered_funnel GROUP BY acquisition_channel
),
starts AS (
    SELECT acquisition_channel, users_at_step AS start_users
    FROM channel_steps
    WHERE step_order = 1
)
SELECT
    channel_steps.acquisition_channel,
    channel_steps.step_order,
    channel_steps.step_label,
    channel_steps.users_at_step,
    ROUND(channel_steps.users_at_step / NULLIF(starts.start_users, 0), 4) AS conversion_from_start
FROM channel_steps
LEFT JOIN starts
    ON channel_steps.acquisition_channel = starts.acquisition_channel
ORDER BY channel_steps.acquisition_channel, channel_steps.step_order;
