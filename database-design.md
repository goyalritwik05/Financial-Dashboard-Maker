# Database Design

## Core Tables
- `imports`: import job metadata.
- `transactions`: normalized transaction records.
- `audit_log`: trigger-based insert trail.
- `model_predictions`: ML forecast outputs.
- `anomalies`: anomaly detection outputs.

## SQL Features Used
- Constraints (`CHECK`, `FOREIGN KEY`, `UNIQUE`).
- Indexes for query performance on date, category, type, import id.
- Views:
  - `vw_monthly_summary`
  - `vw_category_expense`
  - `vw_cashflow_trend`
- Trigger:
  - `trg_audit_insert_transaction`

## Rationale
The design prioritizes traceability, performance for dashboard queries, and clear DBMS-centric implementation suitable for evaluation.
