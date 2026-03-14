from pathlib import Path
import tempfile

import altair as alt
import pandas as pd
import streamlit as st

from src.financial_dashboard.analytics import (
    generate_insights,
    load_category_expense,
    load_monthly_summary,
    load_recent_transactions,
    load_top_merchants,
)
from src.financial_dashboard.config import DB_PATH, MAX_UPLOAD_MB
from src.financial_dashboard.db import get_connection, init_db
from src.financial_dashboard.pipeline import run_pipeline


st.set_page_config(page_title="Financial Dashboard Maker", layout="wide")

st.markdown(
    """
    <style>
    :root {
      --bg: #090d16;
      --panel: #121a29;
      --muted: #8ea2c8;
      --text: #eaf1ff;
      --accent: #4dd0e1;
      --accent2: #7c4dff;
      --success: #00c853;
      --danger: #ff5252;
    }

    .stApp {
      background:
        radial-gradient(circle at 15% 20%, rgba(124, 77, 255, 0.18), transparent 28%),
        radial-gradient(circle at 85% 5%, rgba(77, 208, 225, 0.16), transparent 24%),
        linear-gradient(140deg, #090d16 0%, #0f1726 50%, #0d1422 100%);
      color: var(--text);
    }

    section[data-testid="stSidebar"] {
      background: #0d1422;
      border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    h1, h2, h3, .stMarkdown, p, label {
      color: var(--text) !important;
    }

    .metric-card {
      background: linear-gradient(160deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 14px;
      padding: 14px;
      backdrop-filter: blur(4px);
    }

    .insight-box {
      background: rgba(77, 208, 225, 0.08);
      border: 1px solid rgba(77, 208, 225, 0.25);
      border-radius: 12px;
      padding: 10px 12px;
      margin-bottom: 8px;
      color: var(--text);
    }

    .subtle {
      color: var(--muted);
      font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

st.title("Financial Dashboard Maker")
st.caption("Dark-mode analytics workspace | SQL-backed insights + ML forecasting")

with st.sidebar:
    st.header("Import Statement")
    uploaded = st.file_uploader("Upload bank CSV", type=["csv"])
    run = st.button("Run Ingestion + Analytics", type="primary", use_container_width=True)
    clear = st.button("Clear Existing Data", use_container_width=True)
    st.markdown(f"<p class='subtle'>Max upload size: {MAX_UPLOAD_MB} MB</p>", unsafe_allow_html=True)

if clear:
    with get_connection(DB_PATH) as conn:
        conn.executescript(
            """
            DELETE FROM anomalies;
            DELETE FROM model_predictions;
            DELETE FROM audit_log;
            DELETE FROM transactions;
            DELETE FROM imports;
            """
        )
        conn.commit()
    st.success("Database cleared. Upload a CSV and run ingestion.")

if run and uploaded:
    if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
        st.error("File too large. Please upload a smaller CSV file.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = Path(tmp.name)

        try:
            result = run_pipeline(csv_path=tmp_path, db_path=DB_PATH)
            ingest = result["ingestion"]
            st.success(
                f"Imported {ingest.rows_inserted}/{ingest.rows_read} rows from {uploaded.name}. "
                f"Duplicates skipped: {ingest.duplicates_skipped}."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Import failed: {exc}")
            st.info("Tip: Ensure CSV has date + description + amount (or debit/credit) columns.")
elif run and not uploaded:
    st.error("Please select a CSV file before running ingestion.")

summary = load_monthly_summary(DB_PATH)
category = load_category_expense(DB_PATH)
recent = load_recent_transactions(DB_PATH, limit=30)
top_merchants = load_top_merchants(DB_PATH)
insights = generate_insights(DB_PATH)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
if summary.empty:
    for col, title in zip((kpi1, kpi2, kpi3, kpi4), ("Month", "Income", "Expense", "Net"), strict=False):
        with col:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.metric(title, "-")
            st.markdown("</div>", unsafe_allow_html=True)
    st.warning("No data yet. Upload a CSV to generate dashboard insights.")
    st.stop()
else:
    st.info("Showing data already stored in the local database. Use 'Clear Existing Data' for a fresh run.")

latest = summary.iloc[-1]
with kpi1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Latest Month", latest["month"])
    st.markdown("</div>", unsafe_allow_html=True)
with kpi2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Income", f"{latest['total_income']:.2f}")
    st.markdown("</div>", unsafe_allow_html=True)
with kpi3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Expense", f"{latest['total_expense']:.2f}")
    st.markdown("</div>", unsafe_allow_html=True)
with kpi4:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Net Cashflow", f"{latest['net_cashflow']:.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

summary_plot = summary.copy()
summary_plot["month"] = pd.to_datetime(summary_plot["month"] + "-01")
summary_long = summary_plot.melt(
    id_vars=["month"],
    value_vars=["total_income", "total_expense", "net_cashflow"],
    var_name="metric",
    value_name="amount",
)

st.subheader("Cashflow Trend")
line_chart = (
    alt.Chart(summary_long)
    .mark_line(point=True, strokeWidth=3)
    .encode(
        x=alt.X("month:T", title="Month"),
        y=alt.Y("amount:Q", title="Amount"),
        color=alt.Color(
            "metric:N",
            scale=alt.Scale(
                domain=["total_income", "total_expense", "net_cashflow"],
                range=["#4dd0e1", "#ff8a65", "#00c853"],
            ),
            legend=alt.Legend(title="Metric"),
        ),
        tooltip=["month:T", "metric:N", "amount:Q"],
    )
    .properties(height=320)
)
st.altair_chart(line_chart, use_container_width=True)

left, right = st.columns((1.2, 1))
with left:
    st.subheader("Category Spend (Latest Month)")
    latest_month = category["month"].max()
    latest_category = category[category["month"] == latest_month].copy()
    pie = (
        alt.Chart(latest_category)
        .mark_arc(innerRadius=55)
        .encode(
            theta=alt.Theta(field="expense", type="quantitative"),
            color=alt.Color("category:N", scale=alt.Scale(scheme="tealblues")),
            tooltip=["category:N", "expense:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(pie, use_container_width=True)

with right:
    st.subheader("Top Merchants")
    merchant_bar = (
        alt.Chart(top_merchants)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X("spend:Q", title="Spend"),
            y=alt.Y("merchant:N", sort="-x", title="Merchant"),
            color=alt.value("#7c4dff"),
            tooltip=["merchant:N", "spend:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(merchant_bar, use_container_width=True)

st.subheader("Insight Feed")
for item in insights:
    st.markdown(f"<div class='insight-box'>{item}</div>", unsafe_allow_html=True)

with get_connection(DB_PATH) as conn:
    pred = pd.read_sql_query(
        """
        SELECT target_month, predicted_income, predicted_expense, net_cashflow, metric_value
        FROM model_predictions
        ORDER BY target_month
        """,
        conn,
    )
    anomalies = pd.read_sql_query(
        """
        SELECT a.transaction_id, a.anomaly_score, t.txn_date, t.description, t.amount
        FROM anomalies a
        JOIN transactions t ON t.id = a.transaction_id
        ORDER BY a.anomaly_score ASC
        LIMIT 20
        """,
        conn,
    )

st.subheader("ML Forecast")
if pred.empty:
    st.info("Need at least 3 months of data for forecasting.")
else:
    st.dataframe(pred, use_container_width=True, hide_index=True)

st.subheader("Anomaly Watch")
if anomalies.empty:
    st.info("Need at least 25 transactions for anomaly detection.")
else:
    st.dataframe(anomalies, use_container_width=True, hide_index=True)

st.subheader("Recent Transactions")
st.dataframe(recent, use_container_width=True, hide_index=True)
