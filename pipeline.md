# Data Pipeline

## Ingestion Rules
- Required semantic fields:
  - date
  - description
  - amount OR debit/credit
- Accepts common alias headers (e.g., `Tran Date`, `PARTICULARS`, `DR`, `CR`, `BAL`).

## Cleaning Steps
- Parse delimiter and encoding robustly.
- Normalize dates and numeric values.
- Infer signed amount.
- Drop invalid/empty rows.
- Assign categories from keyword rules.
- Generate transaction hash and deduplicate.

## Outputs
- SQL transaction rows
- monthly summary views
- ML tables (`model_predictions`, `anomalies`)
