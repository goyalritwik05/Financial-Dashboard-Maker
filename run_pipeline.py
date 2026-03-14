from pathlib import Path
import argparse

from src.financial_dashboard.config import DB_PATH
from src.financial_dashboard.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest CSV and run SQL + ML pipeline")
    parser.add_argument("csv", type=Path, help="Path to banking statement CSV")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite DB path")
    args = parser.parse_args()

    result = run_pipeline(csv_path=args.csv, db_path=args.db)
    ing = result["ingestion"]

    print("Pipeline complete")
    print(f"Source file: {ing.source_file}")
    print(f"Rows read: {ing.rows_read}")
    print(f"Rows inserted: {ing.rows_inserted}")
    print(f"Duplicates skipped: {ing.duplicates_skipped}")
    print(f"Forecast rows: {result['forecast_rows']}")
    print(f"Anomalies: {result['anomalies']}")


if __name__ == "__main__":
    main()
