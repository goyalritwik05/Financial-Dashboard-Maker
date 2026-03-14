from pathlib import Path

from src.financial_dashboard.config import PROJECT_ROOT
from src.financial_dashboard.pipeline import run_pipeline


def test_pipeline_runs_smoke() -> None:
    db_path = PROJECT_ROOT / "test_financial_dashboard.db"
    if db_path.exists():
        db_path.unlink()

    result = run_pipeline(
        csv_path=PROJECT_ROOT / "sample_data" / "sample_bank_statement.csv",
        db_path=db_path,
    )

    assert result["ingestion"].rows_inserted > 0
    assert result["forecast_rows"] >= 1
