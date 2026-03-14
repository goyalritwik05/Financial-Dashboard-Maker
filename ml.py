from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from .analytics import load_monthly_summary
from .db import get_connection


def run_forecast(db_path: Path, horizon: int = 3) -> pd.DataFrame:
    monthly = load_monthly_summary(db_path)
    if len(monthly) < 3:
        return pd.DataFrame(columns=[
            "target_month",
            "predicted_income",
            "predicted_expense",
            "net_cashflow",
            "metric_mae",
        ])

    monthly = monthly.copy().reset_index(drop=True)
    monthly["idx"] = np.arange(len(monthly))

    x = monthly[["idx"]]
    y_income = monthly["total_income"]
    y_expense = monthly["total_expense"]

    income_model = LinearRegression().fit(x, y_income)
    expense_model = LinearRegression().fit(x, y_expense)

    pred_income_train = income_model.predict(x)
    pred_expense_train = expense_model.predict(x)
    mae = float(
        (mean_absolute_error(y_income, pred_income_train) + mean_absolute_error(y_expense, pred_expense_train)) / 2
    )

    last_month = pd.to_datetime(monthly.iloc[-1]["month"] + "-01")
    future_idx = np.arange(len(monthly), len(monthly) + horizon)

    rows = []
    for i, idx in enumerate(future_idx, start=1):
        target_month = (last_month + pd.DateOffset(months=i)).strftime("%Y-%m")
        future_x = pd.DataFrame({"idx": [idx]})
        income_pred = float(income_model.predict(future_x)[0])
        expense_pred = float(expense_model.predict(future_x)[0])
        rows.append(
            {
                "target_month": target_month,
                "predicted_income": round(max(income_pred, 0), 2),
                "predicted_expense": round(max(expense_pred, 0), 2),
                "net_cashflow": round(max(income_pred, 0) - max(expense_pred, 0), 2),
                "metric_mae": round(mae, 2),
            }
        )

    forecast = pd.DataFrame(rows)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM model_predictions")
        conn.executemany(
            """
            INSERT INTO model_predictions (
                model_name, target_month, metric_name, metric_value,
                predicted_income, predicted_expense, net_cashflow
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "LinearRegression",
                    r["target_month"],
                    "MAE",
                    r["metric_mae"],
                    r["predicted_income"],
                    r["predicted_expense"],
                    r["net_cashflow"],
                )
                for r in rows
            ],
        )
        conn.commit()

    return forecast


def detect_anomalies(db_path: Path, contamination: float = 0.07) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        tx = pd.read_sql_query(
            "SELECT id, txn_date, amount, category FROM transactions ORDER BY txn_date",
            conn,
        )

    if len(tx) < 25:
        return pd.DataFrame(columns=["transaction_id", "anomaly_score", "reason"])

    tx = tx.copy()
    tx["abs_amount"] = tx["amount"].abs()
    tx["day"] = pd.to_datetime(tx["txn_date"]).dt.day
    x = tx[["abs_amount", "day"]]

    model = IsolationForest(contamination=contamination, random_state=42)
    labels = model.fit_predict(x)
    scores = model.score_samples(x)

    anomalies = tx[labels == -1].copy()
    anomalies["anomaly_score"] = scores[labels == -1]
    anomalies["reason"] = "Unusual amount/date pattern"

    out = anomalies[["id", "anomaly_score", "reason"]].rename(columns={"id": "transaction_id"})

    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM anomalies")
        conn.executemany(
            "INSERT INTO anomalies (transaction_id, anomaly_score, reason) VALUES (?, ?, ?)",
            [(int(r.transaction_id), float(r.anomaly_score), r.reason) for r in out.itertuples(index=False)],
        )
        conn.commit()

    return out
