from pathlib import Path

from .ingest import IngestionResult, ingest_csv
from .ml import detect_anomalies, run_forecast


def run_pipeline(csv_path: Path, db_path: Path) -> dict:
    ingestion: IngestionResult = ingest_csv(csv_path=csv_path, db_path=db_path)
    forecast = run_forecast(db_path=db_path)
    anomalies = detect_anomalies(db_path=db_path)

    return {
        "ingestion": ingestion,
        "forecast_rows": int(len(forecast)),
        "anomalies": int(len(anomalies)),
    }
