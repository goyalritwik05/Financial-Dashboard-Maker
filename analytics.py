from pathlib import Path

import pandas as pd

from .db import get_connection


def load_monthly_summary(db_path: Path) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            "SELECT month, total_income, total_expense, net_cashflow, transaction_count FROM vw_monthly_summary",
            conn,
        )


def load_category_expense(db_path: Path) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            "SELECT month, category, expense FROM vw_category_expense",
            conn,
        )


def load_recent_transactions(db_path: Path, limit: int = 20) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            """
            SELECT txn_date, description, category, txn_type, amount, balance
            FROM transactions
            ORDER BY txn_date DESC, id DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )


def load_top_merchants(db_path: Path, limit: int = 8) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            """
            SELECT merchant, ROUND(ABS(SUM(amount)), 2) AS spend
            FROM transactions
            WHERE amount < 0
            GROUP BY merchant
            ORDER BY spend DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )


def generate_insights(db_path: Path) -> list[str]:
    summary = load_monthly_summary(db_path)
    if summary.empty:
        return ["No transaction data available yet."]

    insights = []
    latest = summary.iloc[-1]
    insights.append(
        f"{latest['month']}: income {latest['total_income']:.2f}, expense {latest['total_expense']:.2f}, net {latest['net_cashflow']:.2f}."
    )

    savings_rate = 0.0
    if latest["total_income"] > 0:
        savings_rate = (latest["net_cashflow"] / latest["total_income"]) * 100
    insights.append(f"Estimated savings rate this month: {savings_rate:.1f}%.")

    if len(summary) > 1:
        prev = summary.iloc[-2]
        exp_delta = latest["total_expense"] - prev["total_expense"]
        net_delta = latest["net_cashflow"] - prev["net_cashflow"]
        exp_dir = "up" if exp_delta > 0 else "down"
        net_dir = "up" if net_delta > 0 else "down"
        insights.append(f"Expense is {exp_dir} by {abs(exp_delta):.2f} vs {prev['month']}.")
        insights.append(f"Net cashflow is {net_dir} by {abs(net_delta):.2f} vs {prev['month']}.")

    category_df = load_category_expense(db_path)
    latest_cat = category_df[category_df["month"] == latest["month"]]
    if not latest_cat.empty:
        top = latest_cat.sort_values("expense", ascending=False).iloc[0]
        total = max(latest_cat["expense"].sum(), 1)
        pct = (top["expense"] / total) * 100
        insights.append(
            f"Highest spending category: {top['category']} ({top['expense']:.2f}, {pct:.1f}% share)."
        )

    return insights
