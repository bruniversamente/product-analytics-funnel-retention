"""Run the project SQL scripts with DuckDB.

Usage:
    python scripts/run_sql.py
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "product_analytics.duckdb"
SQL_FILES = [
    ROOT / "sql" / "01_create_schema_duckdb.sql",
    ROOT / "sql" / "02_data_quality_checks.sql",
    ROOT / "sql" / "03_funnel_analysis.sql",
    ROOT / "sql" / "04_retention_cohorts.sql",
    ROOT / "sql" / "05_marketplace_metrics.sql",
]


def main():
    con = duckdb.connect(str(DB_PATH))
    for sql_file in SQL_FILES:
        print(f"\n--- Running {sql_file.name} ---")
        sql = sql_file.read_text(encoding="utf-8")
        result = con.execute(sql)
        try:
            print(result.fetchdf())
        except Exception:
            print("Script executed.")
    con.close()
    print(f"\nDatabase created at: {DB_PATH}")


if __name__ == "__main__":
    main()
