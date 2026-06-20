"""Run the project SQL scripts with DuckDB.

Usage:
    python scripts/run_sql.py
"""

from pathlib import Path

import duckdb

from generate_product_events import main as generate_product_events

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "product_analytics.duckdb"
SQL_FILES = [
    ROOT / "sql" / "01_create_schema_duckdb.sql",
    ROOT / "sql" / "02_data_quality_checks.sql",
    ROOT / "sql" / "03_funnel_analysis.sql",
    ROOT / "sql" / "04_retention_cohorts.sql",
    ROOT / "sql" / "05_marketplace_metrics.sql",
]


def uncommented_prefix(statement: str) -> str:
    lines = []
    for line in statement.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        lines.append(stripped)
    return "\n".join(lines).lower()


def run_sql_file(connection, sql_file: Path) -> None:
    print(f"\n--- Running {sql_file.name} ---")
    sql = sql_file.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]

    for index, statement in enumerate(statements, start=1):
        result = connection.execute(statement)
        prefix = uncommented_prefix(statement)
        if prefix.startswith(("select", "with")):
            print(f"\nQuery {index}")
            print(result.fetchdf())


def main():
    generate_product_events()
    con = duckdb.connect(str(DB_PATH))
    try:
        for sql_file in SQL_FILES:
            run_sql_file(con, sql_file)
    finally:
        con.close()
    print(f"\nDatabase created at: {DB_PATH}")


if __name__ == "__main__":
    main()
