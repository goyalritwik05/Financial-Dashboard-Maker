# Financial-Dashboard-Maker
Financial Dashboard Maker analyzes bank statement CSV files using Python, SQLite, Pandas, and Streamlit. It cleans and stores data in a SQL database and visualizes spending trends, expense categories, and financial insights
# Financial Dashboard Maker

SQL-first software to ingest monthly bank statement CSVs, clean and standardize transactions, store them in a relational database, and generate dashboards, insights, and ML-based projections.

## Highlights
- SQL-centric DBMS implementation (schema, indexes, constraints, views, trigger-based audit logging).
- Flexible CSV ingestion for different bank statement formats.
- Streamlit dashboard with KPIs, trends, category analysis, and anomaly view.
- ML layer for forecast + anomaly detection, persisted back into SQL tables.

## Tech Stack
- Python 3.11+
- SQLite (portable DB backend)
- Pandas
- Scikit-learn
- Streamlit

## Repository Structure
```text
.
├── app.py
├── sql/schema.sql
├── src/financial_dashboard/
├── scripts/run_pipeline.py
├── sample_data/
├── tests/
├── docs/
└── .github/
```

## Quick Start
```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. streamlit run app.py
```

## CLI Ingestion
```bash
PYTHONPATH=. python3 scripts/run_pipeline.py sample_data/sample_bank_statement.csv
```

## SQL Design Focus
See detailed DBMS documentation in:
- `docs/database-design.md`
- `docs/architecture.md`
- `docs/pipeline.md`

## Project Status
Active and ready for academic demonstration / portfolio publishing.

## License
MIT (see `LICENSE`).
