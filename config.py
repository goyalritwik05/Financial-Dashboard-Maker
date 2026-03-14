from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "financial_dashboard.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
MAX_UPLOAD_MB = 10
