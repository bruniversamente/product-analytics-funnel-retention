"""Build reviewed outputs and a static dashboard for the Playzone case.

Usage:
    python scripts/build_outputs.py

The script regenerates synthetic data, builds a DuckDB model, exports reviewed
CSV extracts, writes an executive findings note, and creates a portable HTML
dashboard for recruiters and hiring managers.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from generate_product_events import main as generate_product_events

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "generated"
OUTPUT_DIR = ROOT / "outputs"
DASHBOARD_DIR = ROOT / "dashboard"
DB_PATH = ROOT / "product_analytics.duckdb"


def sql_path(path: Path) -> str:
    return path.resolve().as_posix()


def pct(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def fmt_num(value: float | int | None, decimals: int = 0) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):,.{decimals}f}"


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    DASHBOARD_DIR.mkdir(exist_ok=True)


def create_model(con: duckdb.DuckDBPyConnection) -> None:
    users_csv = DATA_DIR / "users.csv"
    events_csv = DATA_DIR / "events.csv"
    marketplace_csv = DATA_DIR / "marketplace_actions.csv"

    con.execute(
        f"""
        CREATE OR REPLACE TABLE dim_users AS
        SELECT
            user_id,
            CAST(signup_date AS DATE) AS signup_date,
            persona,
            region,
            acquisition_channel,
            platform
        FROM read_csv_auto('{sql_path(users_csv)}', all_varchar = true);

        CREATE OR REPLACE TABLE fact_events AS
        SELECT
            event_id,
            user_id,
            TRY_CAST(event_timestamp AS TIMESTAMP) AS event_timestamp,
            TRY_CAST(event_timestamp AS DATE) AS event_date,
            event_name,
            session_id,
            platform,
            acquisition_channel,
            NULLIF(opportunity_id, '') AS opportunity_id,
            NULLIF(category, '') AS category
        FROM read_csv_auto('{sql_path(events_csv)}', all_varchar = true);

        CREATE OR REPLACE TABLE fact_marketplace_actions AS
        SELECT
            opportunity_id,
            category,
            TRY_CAST(created_at AS TIMESTAMP) AS created_at,
            NULLIF(host_user_id, '') AS host_user_id,
            NULLIF(guest_user_id, '') AS guest_user_id,
            TRY_CAST(NULLIF(invitation_sent_at, '') AS TIMESTAMP) AS invitation_sent_at,
            TRY_CAST(NULLIF(booking_confirmed_at, '') AS TIMESTAMP) AS booking_confirmed_at,
            status
        FROM read_csv_auto('{sql_path(marketplace_csv)}', all_varchar = true);

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
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE user_ordered_funnel AS
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
        )
        SELECT
            step_6.*,
            MIN(events.event_timestamp) AS booking_confirmed_at
        FROM step_6
        LEFT JOIN fact_events AS events
            ON step_6.user_id = events.user_id
            AND events.event_name = 'booking_confirmed'
            AND events.event_timestamp >= step_6.invitation_sent_at
        GROUP BY ALL;
        """
    )


def query_outputs(con: duckdb.DuckDBPyConnection) -> dict[str, object]:
    outputs: dict[str, object] = {}

    outputs["kpi_summary"] = con.execute(
        """
        WITH base AS (
            SELECT
                COUNT(*) AS total_users,
                COUNT(app_open_at) AS app_open_users,
                COUNT(signup_completed_at) AS signup_users,
                COUNT(profile_completed_at) AS profile_users,
                COUNT(search_performed_at) AS search_users,
                COUNT(opportunity_viewed_at) AS opportunity_view_users,
                COUNT(invitation_sent_at) AS invitation_users,
                COUNT(booking_confirmed_at) AS activated_users,
                ROUND(COUNT(booking_confirmed_at) / NULLIF(COUNT(app_open_at), 0), 4) AS activation_rate,
                ROUND(AVG(DATE_DIFF('hour', app_open_at, booking_confirmed_at)), 2) AS avg_hours_to_activation
            FROM user_ordered_funnel
        ),
        marketplace AS (
            SELECT
                COUNT(*) AS opportunities_created,
                COUNT(invitation_sent_at) AS opportunities_invited,
                COUNT(booking_confirmed_at) AS confirmed_bookings,
                ROUND(COUNT(booking_confirmed_at) / NULLIF(COUNT(invitation_sent_at), 0), 4) AS confirmation_rate,
                ROUND(AVG(DATE_DIFF('hour', invitation_sent_at, booking_confirmed_at)), 2) AS avg_hours_to_confirmation
            FROM fact_marketplace_actions
        )
        SELECT * FROM base CROSS JOIN marketplace;
        """
    ).fetchdf()

    outputs["ordered_funnel"] = con.execute(
        """
        WITH steps AS (
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
        """
    ).fetchdf()

    outputs["funnel_by_channel"] = con.execute(
        """
        WITH channel_steps AS (
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
        """
    ).fetchdf()

    outputs["retention_by_activation"] = con.execute(
        """
        WITH activity AS (
            SELECT
                user_id,
                MAX(CASE WHEN event_name = 'app_open' AND days_since_signup = 1 THEN 1 ELSE 0 END) AS retained_d1,
                MAX(CASE WHEN event_name = 'app_open' AND days_since_signup = 7 THEN 1 ELSE 0 END) AS retained_d7,
                MAX(CASE WHEN event_name = 'app_open' AND days_since_signup = 30 THEN 1 ELSE 0 END) AS retained_d30
            FROM vw_events_enriched
            GROUP BY user_id
        )
        SELECT
            CASE WHEN funnel.booking_confirmed_at IS NOT NULL THEN 'Ativados' ELSE 'Não ativados' END AS activation_status,
            COUNT(users.user_id) AS users,
            ROUND(AVG(COALESCE(activity.retained_d1, 0)), 4) AS retention_d1,
            ROUND(AVG(COALESCE(activity.retained_d7, 0)), 4) AS retention_d7,
            ROUND(AVG(COALESCE(activity.retained_d30, 0)), 4) AS retention_d30
        FROM dim_users AS users
        LEFT JOIN user_ordered_funnel AS funnel
            ON users.user_id = funnel.user_id
        LEFT JOIN activity
            ON users.user_id = activity.user_id
        GROUP BY activation_status
        ORDER BY activation_status;
        """
    ).fetchdf()

    outputs["cohort_retention"] = con.execute(
        """
        WITH cohort_activity AS (
            SELECT
                users.user_id,
                STRFTIME(users.signup_date, '%Y-%m') AS signup_month,
                FLOOR(DATE_DIFF('day', users.signup_date, events.event_date) / 7) AS week_number
            FROM dim_users AS users
            LEFT JOIN fact_events AS events
                ON users.user_id = events.user_id
            WHERE events.event_date >= users.signup_date
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
        """
    ).fetchdf()

    outputs["marketplace_category_metrics"] = con.execute(
        """
        SELECT
            category,
            COUNT(*) AS opportunities,
            COUNT(invitation_sent_at) AS invitations_sent,
            COUNT(booking_confirmed_at) AS confirmed_bookings,
            ROUND(COUNT(booking_confirmed_at) / NULLIF(COUNT(invitation_sent_at), 0), 4) AS confirmation_rate,
            ROUND(AVG(DATE_DIFF('hour', invitation_sent_at, booking_confirmed_at)), 2) AS avg_hours_to_confirmation
        FROM fact_marketplace_actions
        GROUP BY category
        ORDER BY confirmation_rate DESC NULLS LAST, opportunities DESC;
        """
    ).fetchdf()

    outputs["data_quality_summary"] = con.execute(
        """
        SELECT 'duplicate_event_id' AS rule_name, 'Critical' AS severity, COUNT(*) AS failed_records
        FROM (
            SELECT event_id FROM fact_events GROUP BY event_id HAVING COUNT(*) > 1
        )
        UNION ALL
        SELECT 'event_without_valid_user', 'Critical', COUNT(*)
        FROM fact_events AS events
        LEFT JOIN dim_users AS users
            ON events.user_id = users.user_id
        WHERE users.user_id IS NULL
        UNION ALL
        SELECT 'event_outside_taxonomy', 'Critical', COUNT(*)
        FROM fact_events
        WHERE event_name NOT IN (
            'app_open',
            'signup_completed',
            'profile_completed',
            'search_performed',
            'opportunity_viewed',
            'invitation_sent',
            'booking_confirmed'
        )
        UNION ALL
        SELECT 'opportunity_event_missing_id', 'Warning', COUNT(*)
        FROM fact_events
        WHERE event_name IN ('search_performed', 'opportunity_viewed', 'invitation_sent', 'booking_confirmed')
          AND opportunity_id IS NULL
        UNION ALL
        SELECT 'event_before_signup', 'Critical', COUNT(*)
        FROM fact_events AS events
        LEFT JOIN dim_users AS users
            ON events.user_id = users.user_id
        WHERE CAST(events.event_timestamp AS DATE) < users.signup_date
        UNION ALL
        SELECT 'booking_before_invitation', 'Critical', COUNT(*)
        FROM fact_marketplace_actions
        WHERE booking_confirmed_at < invitation_sent_at;
        """
    ).fetchdf()

    return outputs


def write_outputs(outputs: dict[str, object]) -> None:
    for name, frame in outputs.items():
        frame.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)

    dashboard_data = {
        name: json.loads(frame.to_json(orient="records"))
        for name, frame in outputs.items()
    }
    (OUTPUT_DIR / "dashboard_data.json").write_text(
        json.dumps(dashboard_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_findings(dashboard_data)
    write_dashboard(dashboard_data)


def write_findings(data: dict[str, list[dict[str, object]]]) -> None:
    kpis = data["kpi_summary"][0]
    funnel = data["ordered_funnel"]
    channel_rows = data["funnel_by_channel"]
    category_rows = data["marketplace_category_metrics"]
    dq_rows = data["data_quality_summary"]

    drop_rows = [row for row in funnel if row["step_order"] != 1]
    biggest_drop = max(drop_rows, key=lambda row: row.get("loss_from_previous") or 0)

    final_channel_rows = [
        row for row in channel_rows if row["step_label"] == "Reserva confirmada"
    ]
    best_channel = max(
        final_channel_rows, key=lambda row: row.get("conversion_from_start") or 0
    )
    worst_channel = min(
        final_channel_rows, key=lambda row: row.get("conversion_from_start") or 0
    )

    best_category = max(
        category_rows, key=lambda row: row.get("confirmation_rate") or 0
    )
    critical_failures = sum(
        int(row["failed_records"])
        for row in dq_rows
        if row["severity"] == "Critical"
    )
    step_labels_en = {
        "Abertura do app": "App open",
        "Cadastro concluído": "Signup completed",
        "Perfil completo": "Profile completed",
        "Busca realizada": "Search performed",
        "Oportunidade vista": "Opportunity viewed",
        "Convite enviado": "Invitation sent",
        "Reserva confirmada": "Booking confirmed",
    }
    biggest_drop_label_en = step_labels_en.get(
        str(biggest_drop["step_label"]), str(biggest_drop["step_label"])
    )

    body_pt = f"""# Achados executivos - Playzone Product Analytics

## Resumo de decisão

O maior ganho mensurável da Playzone não está apenas em trazer mais usuários para o topo do funil. O problema principal está no caminho entre descobrir uma oportunidade, enviar convite e confirmar a reserva. O funil ordenado mostra que {pct(kpis["activation_rate"])} dos usuários que abrem o produto chegam ao momento de valor. A maior perda acontece em **{biggest_drop["step_label"]}**, etapa em que {pct(biggest_drop["loss_from_previous"])} dos usuários caem em relação à etapa anterior.

## O que os dados mostram

- Usuários analisados: {fmt_num(kpis["total_users"])}
- Taxa de ativação ordenada: {pct(kpis["activation_rate"])}
- Reservas confirmadas: {fmt_num(kpis["confirmed_bookings"])}
- Taxa de confirmação após convite: {pct(kpis["confirmation_rate"])}
- Tempo médio entre convite e confirmação: {fmt_num(kpis["avg_hours_to_confirmation"], 1)} horas
- Melhor canal por ativação ordenada: {best_channel["acquisition_channel"]} ({pct(best_channel["conversion_from_start"])})
- Canal mais fraco por ativação ordenada: {worst_channel["acquisition_channel"]} ({pct(worst_channel["conversion_from_start"])})
- Categoria mais forte depois do convite: {best_category["category"]} ({pct(best_category["confirmation_rate"])})
- Falhas críticas de qualidade de dados: {critical_failures}

## Recomendações de produto

1. Priorizar a queda em **{biggest_drop["step_label"]}** antes de aumentar investimento em aquisição.
2. Comparar canais de aquisição usando {best_channel["acquisition_channel"]} como referência de ativação e investigar a promessa/onboarding de {worst_channel["acquisition_channel"]}.
3. Tratar reserva confirmada como definição de ativação e monitorar retenção D1, D7 e D30 separando usuários ativados e não ativados.
4. Usar liquidez por categoria para decidir onde melhorar oferta, lembretes, recomendação ou disponibilidade.
5. Manter as checagens de qualidade antes de apresentar métricas de ativação para liderança.

## Evidências geradas

- `outputs/kpi_summary.csv`
- `outputs/ordered_funnel.csv`
- `outputs/funnel_by_channel.csv`
- `outputs/retention_by_activation.csv`
- `outputs/cohort_retention.csv`
- `outputs/marketplace_category_metrics.csv`
- `outputs/data_quality_summary.csv`
- `dashboard/playzone_product_analytics_dashboard.html`
"""

    body_en = f"""# Executive findings - Playzone Product Analytics

## Decision summary

Playzone's largest measurable gain is not only bringing more users into the top of the funnel. The main issue is the path between discovering an opportunity, sending an invitation and confirming a booking. The ordered funnel shows that {pct(kpis["activation_rate"])} of users who open the product reach the value moment. The largest drop happens at **{biggest_drop_label_en}**, where {pct(biggest_drop["loss_from_previous"])} of users are lost from the previous step.

## What the data shows

- Users analyzed: {fmt_num(kpis["total_users"])}
- Ordered activation rate: {pct(kpis["activation_rate"])}
- Confirmed bookings: {fmt_num(kpis["confirmed_bookings"])}
- Confirmation rate after invitation: {pct(kpis["confirmation_rate"])}
- Average time from invitation to confirmation: {fmt_num(kpis["avg_hours_to_confirmation"], 1)} hours
- Best channel by ordered activation: {best_channel["acquisition_channel"]} ({pct(best_channel["conversion_from_start"])})
- Weakest channel by ordered activation: {worst_channel["acquisition_channel"]} ({pct(worst_channel["conversion_from_start"])})
- Strongest category after invitation: {best_category["category"]} ({pct(best_category["confirmation_rate"])})
- Critical data quality failures: {critical_failures}

## Product recommendations

1. Prioritize the drop at **{biggest_drop_label_en}** before increasing acquisition investment.
2. Compare acquisition channels using {best_channel["acquisition_channel"]} as the activation benchmark and investigate the promise/onboarding of {worst_channel["acquisition_channel"]}.
3. Treat confirmed booking as the activation definition and monitor D1, D7 and D30 retention separately for activated and non-activated users.
4. Use category liquidity to decide where to improve offer, reminders, recommendations or availability.
5. Keep quality checks in place before presenting activation metrics to leadership.

## Generated evidence

- `outputs/kpi_summary.csv`
- `outputs/ordered_funnel.csv`
- `outputs/funnel_by_channel.csv`
- `outputs/retention_by_activation.csv`
- `outputs/cohort_retention.csv`
- `outputs/marketplace_category_metrics.csv`
- `outputs/data_quality_summary.csv`
- `dashboard/playzone_product_analytics_dashboard.html`
"""

    (OUTPUT_DIR / "executive_findings.md").write_text(body_en, encoding="utf-8")
    (OUTPUT_DIR / "executive_findings.pt-BR.md").write_text(body_pt, encoding="utf-8")


def write_dashboard(data: dict[str, list[dict[str, object]]]) -> None:
    dashboard_json = json.dumps(data, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Playzone Product Analytics Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #18202f;
      --muted: #667085;
      --line: #d9dee7;
      --blue: #2563eb;
      --teal: #0891b2;
      --green: #16a34a;
      --amber: #d97706;
      --red: #dc2626;
      --shadow: 0 18px 45px rgba(24, 32, 47, 0.09);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }}
    .hero-copy, .panel, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .hero-copy {{
      padding: 26px;
      min-height: 220px;
    }}
    .eyebrow {{
      color: var(--teal);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 8px 0 10px;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1.02;
      letter-spacing: 0;
    }}
    .hero-copy p {{
      margin: 0;
      max-width: 780px;
      color: var(--muted);
      font-size: 16px;
    }}
    .hero-side {{
      padding: 18px;
      display: grid;
      gap: 12px;
    }}
    .decision {{
      border-left: 4px solid var(--blue);
      padding-left: 14px;
    }}
    .decision strong {{
      display: block;
      margin-bottom: 4px;
      font-size: 16px;
    }}
    .grid {{
      display: grid;
      gap: 16px;
    }}
    .kpi-grid {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 16px;
    }}
    .card {{
      padding: 18px;
      min-height: 126px;
    }}
    .card small {{
      display: block;
      color: var(--muted);
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .card strong {{
      display: block;
      font-size: 30px;
      line-height: 1;
      letter-spacing: 0;
    }}
    .card span {{
      display: block;
      margin-top: 10px;
      color: var(--muted);
    }}
    .two-col {{
      grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
      margin-bottom: 16px;
    }}
    .panel {{
      padding: 20px;
      min-width: 0;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 14px;
    }}
    h2 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .note {{
      color: var(--muted);
      font-size: 13px;
    }}
    .funnel {{
      display: grid;
      gap: 10px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 148px minmax(140px, 1fr) 86px;
      gap: 12px;
      align-items: center;
    }}
    .bar-label {{
      font-weight: 700;
    }}
    .track {{
      height: 22px;
      background: #eef2f7;
      border-radius: 5px;
      overflow: hidden;
      border: 1px solid #e5e7eb;
    }}
    .fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--blue), var(--teal));
      border-radius: 5px;
    }}
    .bar-value {{
      text-align: right;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }}
    .channel-bars {{
      display: grid;
      gap: 12px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .legend span::before {{
      content: "";
      display: inline-block;
      width: 9px;
      height: 9px;
      margin-right: 6px;
      border-radius: 2px;
      background: var(--blue);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid #e8ecf2;
      text-align: left;
      white-space: nowrap;
    }}
    th {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    td.num, th.num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .heatmap {{
      display: grid;
      grid-template-columns: 90px repeat(5, minmax(48px, 1fr));
      gap: 6px;
      align-items: center;
    }}
    .heatmap div {{
      min-height: 34px;
      border-radius: 5px;
      display: grid;
      place-items: center;
      font-size: 12px;
      color: #172033;
      background: #eef2f7;
    }}
    .heatmap .head, .heatmap .month {{
      background: transparent;
      color: var(--muted);
      font-weight: 800;
    }}
    .sources {{
      margin-top: 16px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 920px) {{
      main {{ padding: 16px; }}
      .hero, .two-col, .kpi-grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 6px; }}
      .bar-value {{ text-align: left; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Product Analytics Case | Playzone</div>
        <h1>Funil, retenção e liquidez do marketplace</h1>
        <p>Dashboard estático e reprodutível para avaliar se usuários chegam ao momento de valor: convite enviado e reserva confirmada em uma plataforma de experiências, jogos e atividades.</p>
      </div>
      <aside class="hero-side panel">
        <div class="decision">
          <strong>Leitura executiva</strong>
          <span id="decisionText">Carregando síntese...</span>
        </div>
        <div class="note">Fonte: dados sintéticos gerados por Python, modelados em DuckDB e exportados em CSV. A lógica do funil usa ordem temporal por usuário.</div>
      </aside>
    </section>

    <section class="grid kpi-grid" id="kpis"></section>

    <section class="grid two-col">
      <div class="panel">
        <div class="panel-header">
          <h2>Funil ordenado de ativação</h2>
          <span class="note">Usuários únicos por etapa</span>
        </div>
        <div class="funnel" id="funnel"></div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h2>Ativação por canal</h2>
          <span class="note">Conversão até reserva confirmada</span>
        </div>
        <div class="channel-bars" id="channels"></div>
      </div>
    </section>

    <section class="grid two-col">
      <div class="panel">
        <div class="panel-header">
          <h2>Retenção por ativação</h2>
          <span class="note">D1, D7 e D30</span>
        </div>
        <table id="retentionTable"></table>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h2>Liquidez por categoria</h2>
          <span class="note">Confirmações após convite</span>
        </div>
        <table id="categoryTable"></table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Cohorts semanais de retenção</h2>
        <span class="note">Semana 0 a 4 após cadastro</span>
      </div>
      <div class="heatmap" id="cohortHeatmap"></div>
    </section>

    <section class="sources">
      <strong>Metodologia:</strong> a ativação é definida como `booking_confirmed` após a sequência `app_open -> signup_completed -> profile_completed -> search_performed -> opportunity_viewed -> invitation_sent`. O dashboard foi gerado por `scripts/build_outputs.py`; os extratos revisados ficam em `outputs/`.
    </section>
  </main>

  <script id="dashboardData" type="application/json">{dashboard_json}</script>
  <script>
    const data = JSON.parse(document.getElementById("dashboardData").textContent);
    const fmt = new Intl.NumberFormat("pt-BR");
    const pct = (v) => `${{(Number(v || 0) * 100).toFixed(1).replace(".", ",")}}%`;
    const num = (v) => fmt.format(Number(v || 0));
    const kpi = data.kpi_summary[0];

    const funnel = data.ordered_funnel;
    const biggestDrop = funnel.slice(1).sort((a, b) => Number(b.loss_from_previous || 0) - Number(a.loss_from_previous || 0))[0];
    document.getElementById("decisionText").textContent =
      `A ativação ordenada está em ${{pct(kpi.activation_rate)}}. O maior vazamento está em "${{biggestDrop.step_label}}", com perda de ${{pct(biggestDrop.loss_from_previous)}} frente à etapa anterior.`;

    const kpis = [
      ["Usuários", num(kpi.total_users), "Base sintética revisada"],
      ["Ativação", pct(kpi.activation_rate), "Reserva confirmada no funil ordenado"],
      ["Confirmações", num(kpi.confirmed_bookings), "Reservas confirmadas no marketplace"],
      ["Liquidez", pct(kpi.confirmation_rate), "Confirmações após convite"]
    ];
    document.getElementById("kpis").innerHTML = kpis.map(([label, value, sub]) => `
      <article class="card"><small>${{label}}</small><strong>${{value}}</strong><span>${{sub}}</span></article>
    `).join("");

    const maxUsers = Number(funnel[0].users_at_step);
    document.getElementById("funnel").innerHTML = funnel.map((row) => {{
      const width = Math.max(2, Number(row.users_at_step) / maxUsers * 100);
      return `<div class="bar-row">
        <div class="bar-label">${{row.step_order}}. ${{row.step_label}}</div>
        <div class="track"><div class="fill" style="width: ${{width}}%"></div></div>
        <div class="bar-value">${{num(row.users_at_step)}} · ${{pct(row.conversion_from_start)}}</div>
      </div>`;
    }}).join("");

    const finalChannelRows = data.funnel_by_channel
      .filter((row) => row.step_label === "Reserva confirmada")
      .sort((a, b) => Number(b.conversion_from_start || 0) - Number(a.conversion_from_start || 0));
    const maxChannel = Math.max(...finalChannelRows.map((row) => Number(row.conversion_from_start || 0)));
    document.getElementById("channels").innerHTML = finalChannelRows.map((row) => {{
      const width = Math.max(2, Number(row.conversion_from_start || 0) / maxChannel * 100);
      return `<div class="bar-row">
        <div class="bar-label">${{row.acquisition_channel}}</div>
        <div class="track"><div class="fill" style="width: ${{width}}%; background: linear-gradient(90deg, var(--green), var(--teal));"></div></div>
        <div class="bar-value">${{pct(row.conversion_from_start)}}</div>
      </div>`;
    }}).join("");

    function table(el, headers, rows) {{
      document.getElementById(el).innerHTML = `
        <thead><tr>${{headers.map((h) => `<th class="${{h.num ? "num" : ""}}">${{h.label}}</th>`).join("")}}</tr></thead>
        <tbody>${{rows.map((row) => `<tr>${{headers.map((h) => `<td class="${{h.num ? "num" : ""}}">${{h.format ? h.format(row[h.key]) : row[h.key]}}</td>`).join("")}}</tr>`).join("")}}</tbody>
      `;
    }}

    table("retentionTable", [
      {{ key: "activation_status", label: "Status" }},
      {{ key: "users", label: "Usuários", num: true, format: num }},
      {{ key: "retention_d1", label: "D1", num: true, format: pct }},
      {{ key: "retention_d7", label: "D7", num: true, format: pct }},
      {{ key: "retention_d30", label: "D30", num: true, format: pct }}
    ], data.retention_by_activation);

    table("categoryTable", [
      {{ key: "category", label: "Categoria" }},
      {{ key: "opportunities", label: "Oportunidades", num: true, format: num }},
      {{ key: "invitations_sent", label: "Convites", num: true, format: num }},
      {{ key: "confirmed_bookings", label: "Confirmações", num: true, format: num }},
      {{ key: "confirmation_rate", label: "Taxa", num: true, format: pct }}
    ], data.marketplace_category_metrics);

    const months = [...new Set(data.cohort_retention.map((row) => row.signup_month))];
    const weekLabels = [0, 1, 2, 3, 4];
    const byKey = new Map(data.cohort_retention.map((row) => [`${{row.signup_month}}-${{row.week_number}}`, row]));
    const heat = document.getElementById("cohortHeatmap");
    heat.innerHTML = `<div class="head">Cohort</div>${{weekLabels.map((w) => `<div class="head">S${{w}}</div>`).join("")}}` +
      months.map((month) => {{
        const cells = weekLabels.map((week) => {{
          const row = byKey.get(`${{month}}-${{week}}`);
          const value = Number(row?.retention_rate || 0);
          const alpha = 0.08 + value * 0.72;
          return `<div style="background: rgba(37, 99, 235, ${{alpha}})">${{pct(value)}}</div>`;
        }}).join("");
        return `<div class="month">${{month}}</div>${{cells}}`;
      }}).join("");
  </script>
</body>
</html>
"""
    pt_html = html
    replacements = [
        ('<html lang="pt-BR">', '<html lang="en">'),
        ("Funil, retenção e liquidez do marketplace", "Funnel, retention and marketplace liquidity"),
        (
            "Dashboard estático e reprodutível para avaliar se usuários chegam ao momento de valor: convite enviado e reserva confirmada em uma plataforma de experiências, jogos e atividades.",
            "Static reproducible dashboard to evaluate whether users reach the value moment: invitation sent and booking confirmed in an experiences, games and activities platform.",
        ),
        ("Leitura executiva", "Executive read"),
        ("Carregando síntese...", "Loading summary..."),
        (
            "Fonte: dados sintéticos gerados por Python, modelados em DuckDB e exportados em CSV. A lógica do funil usa ordem temporal por usuário.",
            "Source: synthetic data generated with Python, modeled in DuckDB and exported as CSV. Funnel logic uses chronological order by user.",
        ),
        ("Funil ordenado de ativação", "Ordered activation funnel"),
        ("Usuários únicos por etapa", "Unique users by step"),
        ("Ativação por canal", "Activation by channel"),
        ("Conversão até reserva confirmada", "Conversion to confirmed booking"),
        ("Retenção por ativação", "Retention by activation"),
        ("Liquidez por categoria", "Liquidity by category"),
        ("Confirmações após convite", "Confirmations after invitation"),
        ("Cohorts semanais de retenção", "Weekly retention cohorts"),
        ("Semana 0 a 4 após cadastro", "Weeks 0 to 4 after signup"),
        (
            "<strong>Metodologia:</strong> a ativação é definida como `booking_confirmed` após a sequência `app_open -> signup_completed -> profile_completed -> search_performed -> opportunity_viewed -> invitation_sent`. O dashboard foi gerado por `scripts/build_outputs.py`; os extratos revisados ficam em `outputs/`.",
            "<strong>Methodology:</strong> activation is defined as `booking_confirmed` after the sequence `app_open -> signup_completed -> profile_completed -> search_performed -> opportunity_viewed -> invitation_sent`. The dashboard is generated by `scripts/build_outputs.py`; reviewed extracts are available in `outputs/`.",
        ),
        ('new Intl.NumberFormat("pt-BR")', 'new Intl.NumberFormat("en-US")'),
        ('toFixed(1).replace(".", ",")', "toFixed(1)"),
        ("Abertura do app", "App open"),
        ("Cadastro concluído", "Signup completed"),
        ("Perfil completo", "Profile completed"),
        ("Busca realizada", "Search performed"),
        ("Oportunidade vista", "Opportunity viewed"),
        ("Convite enviado", "Invitation sent"),
        ("Reserva confirmada", "Booking confirmed"),
        ("Ativados", "Activated"),
        ("Não ativados", "Not activated"),
        (
            "A ativação ordenada está em ${{pct(kpi.activation_rate)}}. O maior vazamento está em \"${{biggestDrop.step_label}}\", com perda de ${{pct(biggestDrop.loss_from_previous)}} frente à etapa anterior.",
            "Ordered activation is ${{pct(kpi.activation_rate)}}. The largest leak is at \"${{biggestDrop.step_label}}\", with a ${{pct(biggestDrop.loss_from_previous)}} loss from the previous step.",
        ),
        (
            'A ativação ordenada está em ${pct(kpi.activation_rate)}. O maior vazamento está em "${biggestDrop.step_label}", com perda de ${pct(biggestDrop.loss_from_previous)} frente à etapa anterior.',
            'Ordered activation is ${pct(kpi.activation_rate)}. The largest leak is at "${biggestDrop.step_label}", with a ${pct(biggestDrop.loss_from_previous)} loss from the previous step.',
        ),
        ('["Usuários", num(kpi.total_users), "Base sintética revisada"]', '["Users", num(kpi.total_users), "Reviewed synthetic base"]'),
        ('["Ativação", pct(kpi.activation_rate), "Reserva confirmada no funil ordenado"]', '["Activation", pct(kpi.activation_rate), "Confirmed booking in the ordered funnel"]'),
        ('["Confirmações", num(kpi.confirmed_bookings), "Reservas confirmadas no marketplace"]', '["Confirmations", num(kpi.confirmed_bookings), "Confirmed marketplace bookings"]'),
        ('["Liquidez", pct(kpi.confirmation_rate), "Confirmações após convite"]', '["Liquidity", pct(kpi.confirmation_rate), "Confirmations after invitation"]'),
        ('["Ativação", pct(kpi.activation_rate), "Booking confirmed no funil ordenado"]', '["Activation", pct(kpi.activation_rate), "Confirmed booking in the ordered funnel"]'),
        ('["Liquidez", pct(kpi.confirmation_rate), "Confirmations after invitation"]', '["Liquidity", pct(kpi.confirmation_rate), "Confirmations after invitation"]'),
        ("Usuários", "Users"),
        ("Categoria", "Category"),
        ("Oportunidades", "Opportunities"),
        ("Convites", "Invites"),
        ("Confirmações", "Confirmations"),
        ("Taxa", "Rate"),
        ("S${{w}}", "W${{w}}"),
    ]
    en_html = pt_html
    for source, target in replacements:
        en_html = en_html.replace(source, target)

    (DASHBOARD_DIR / "playzone_product_analytics_dashboard_pt-BR.html").write_text(pt_html, encoding="utf-8")
    (DASHBOARD_DIR / "playzone_product_analytics_dashboard_en.html").write_text(en_html, encoding="utf-8")
    (DASHBOARD_DIR / "playzone_product_analytics_dashboard.html").write_text(en_html, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    generate_product_events()

    con = duckdb.connect(str(DB_PATH))
    try:
        create_model(con)
        outputs = query_outputs(con)
        write_outputs(outputs)
    finally:
        con.close()

    print(f"Outputs written to {OUTPUT_DIR}")
    print(f"Dashboard written to {DASHBOARD_DIR / 'playzone_product_analytics_dashboard.html'}")


if __name__ == "__main__":
    main()
