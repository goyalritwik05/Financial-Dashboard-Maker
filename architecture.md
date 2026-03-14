# Architecture

## Overview
The system follows a SQL-first analytics pipeline:
1. CSV upload/input
2. Parsing and cleaning in Python
3. Transaction persistence in SQL tables
4. SQL view-based aggregation
5. ML prediction and anomaly scoring
6. Dashboard presentation

## Components
- `ingest.py`: validation, normalization, deduplication, category tagging.
- `db.py` + `sql/schema.sql`: database bootstrap and schema.
- `analytics.py`: SQL query access and insight generation.
- `ml.py`: forecast + anomaly modules.
- `app.py`: Streamlit frontend.

## Security Boundaries
- Input file validation and type/size checks.
- Parameterized SQL statements.
- Deterministic transaction hashing for duplicate prevention.
