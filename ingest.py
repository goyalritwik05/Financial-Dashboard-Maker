import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .db import get_connection, init_db

_COLUMN_ALIASES = {
    "date": [
        "date",
        "tran date",
        "transaction date",
        "value date",
        "txn date",
        "posted date",
    ],
    "description": [
        "description",
        "narration",
        "details",
        "particulars",
        "remarks",
        "transaction details",
    ],
    "debit": ["debit", "withdrawal", "debit amount", "dr", "money out"],
    "credit": ["credit", "deposit", "credit amount", "cr", "money in"],
    "amount": ["amount", "transaction amount", "txn amount"],
    "amount_type": ["type", "dr/cr", "cr/dr", "transaction type", "debit/credit"],
    "balance": ["balance", "bal", "closing balance", "available balance"],
    "reference": ["reference", "ref", "cheque no", "transaction id", "utr", "rrn"],
}

_CATEGORY_RULES = {
    "Food & Dining": ["zomato", "swiggy", "restaurant", "cafe", "food", "pizza", "burger"],
    "Transport": ["uber", "ola", "fuel", "petrol", "diesel", "metro", "bus", "train"],
    "Shopping": ["amazon", "flipkart", "myntra", "store", "mall"],
    "Bills & Utilities": ["electricity", "water", "internet", "mobile", "recharge", "bill"],
    "Salary": ["salary", "payroll", "wages"],
    "Transfer": ["upi", "imps", "neft", "rtgs", "transfer", "bank transfer"],
    "Investment": ["mutual fund", "sip", "stock", "nps", "ppf"],
    "Healthcare": ["medical", "pharmacy", "clinic", "hospital"],
    "Travel": ["flight", "hotel", "trip", "travel"],
}


@dataclass
class IngestionResult:
    source_file: str
    rows_read: int
    rows_inserted: int
    duplicates_skipped: int


def _normalize_name(name: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", " ", str(name).strip().lower())
    return re.sub(r"\s+", " ", compact).strip()


def _read_csv_flexible(csv_path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            df = pd.read_csv(csv_path, sep=None, engine="python", encoding=enc)
            if len(df.columns) > 1:
                return df
        except Exception:  # noqa: BLE001
            continue
    raise ValueError("Could not parse CSV. Check delimiter/encoding and ensure it is a valid text CSV file.")


def _resolve_columns(columns: list[str]) -> dict[str, str]:
    normalized = {_normalize_name(c): c for c in columns}
    resolved = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                resolved[canonical] = normalized[alias]
                break

    if "date" not in resolved or "description" not in resolved:
        raise ValueError(
            "Missing required columns. Need date + description (or equivalent names like value date/narration)."
        )
    if "amount" not in resolved and not ({"debit", "credit"}.issubset(set(resolved))):
        raise ValueError(
            "Missing amount columns. Need either amount, or both debit and credit columns."
        )
    return resolved


def _to_number(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip()
    is_negative_paren = text.str.contains(r"^\(.*\)$", regex=True)
    cleaned = (
        text.str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace(r"\((.*)\)", r"\1", regex=True)
        .str.replace(r"\b(cr|dr)\b", "", flags=re.IGNORECASE, regex=True)
        .str.replace(r"[^\d.\-]", "", regex=True)
    )
    nums = pd.to_numeric(cleaned, errors="coerce")
    nums[is_negative_paren] = -nums[is_negative_paren].abs()
    return nums


def _derive_amount(df: pd.DataFrame, resolved: dict[str, str]) -> pd.Series:
    if "amount" in resolved and {"debit", "credit"}.issubset(set(resolved)):
        amount = _to_number(df[resolved["amount"]])
        if amount.notna().sum() > 0:
            return amount

    if "amount" in resolved and "amount_type" in resolved:
        amount = _to_number(df[resolved["amount"]]).fillna(0)
        typ = df[resolved["amount_type"]].fillna("").astype(str).str.upper()
        signed = amount.copy()
        signed[typ.str.contains("DR|DEBIT", regex=True)] = -signed.abs()
        signed[typ.str.contains("CR|CREDIT", regex=True)] = signed.abs()
        return signed

    if "amount" in resolved:
        amount_col = df[resolved["amount"]].fillna("").astype(str)
        amount = _to_number(amount_col).fillna(0)
        dr_mask = amount_col.str.contains(r"\bdr\b|\bdebit\b", regex=True, case=False)
        cr_mask = amount_col.str.contains(r"\bcr\b|\bcredit\b", regex=True, case=False)
        amount[dr_mask] = -amount[dr_mask].abs()
        amount[cr_mask] = amount[cr_mask].abs()
        return amount

    debit = _to_number(df[resolved["debit"]]).fillna(0)
    credit = _to_number(df[resolved["credit"]]).fillna(0)
    return credit - debit


def _assign_category(description: str) -> str:
    text = str(description).lower()
    for category, keywords in _CATEGORY_RULES.items():
        if any(k in text for k in keywords):
            return category
    return "Other"


def _compute_hash(txn_date: str, description: str, amount: float, reference: str) -> str:
    fingerprint = f"{txn_date}|{description}|{amount:.2f}|{reference}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def read_and_clean_csv(csv_path: Path) -> pd.DataFrame:
    if csv_path.suffix.lower() != ".csv":
        raise ValueError("Only CSV files are allowed.")

    df = _read_csv_flexible(csv_path)
    if df.empty:
        raise ValueError("CSV file is empty.")

    resolved = _resolve_columns(df.columns.tolist())

    clean = pd.DataFrame()
    clean["txn_date"] = pd.to_datetime(
        df[resolved["date"]], errors="coerce", dayfirst=True
    ).dt.strftime("%Y-%m-%d")
    clean["description"] = df[resolved["description"]].fillna("").astype(str).str.strip()
    clean["amount"] = _derive_amount(df, resolved)

    clean["balance"] = _to_number(df[resolved["balance"]]) if "balance" in resolved else None
    clean["reference"] = (
        df[resolved["reference"]].fillna("").astype(str).str.strip() if "reference" in resolved else ""
    )

    clean = clean.dropna(subset=["txn_date", "amount"])
    clean = clean[clean["description"] != ""]
    clean = clean[clean["amount"] != 0]
    clean["amount"] = clean["amount"].round(2)
    clean["txn_type"] = clean["amount"].apply(lambda v: "CREDIT" if v >= 0 else "DEBIT")
    clean["merchant"] = clean["description"].str.split("/").str[0].str[:80]
    clean["category"] = clean["description"].apply(_assign_category)
    clean = clean.drop_duplicates(subset=["txn_date", "description", "amount", "reference"])

    clean["raw_payload"] = clean.apply(
        lambda r: json.dumps(
            {
                "txn_date": r["txn_date"],
                "description": r["description"],
                "amount": r["amount"],
                "balance": r["balance"],
                "reference": r["reference"],
            },
            ensure_ascii=True,
        ),
        axis=1,
    )
    clean["txn_hash"] = clean.apply(
        lambda r: _compute_hash(r["txn_date"], r["description"], r["amount"], r["reference"]),
        axis=1,
    )

    return clean[
        [
            "txn_date",
            "description",
            "merchant",
            "category",
            "txn_type",
            "amount",
            "balance",
            "reference",
            "raw_payload",
            "txn_hash",
        ]
    ]


def ingest_csv(csv_path: Path, db_path: Path) -> IngestionResult:
    init_db(db_path=db_path)
    cleaned = read_and_clean_csv(csv_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO imports (source_file, row_count, inserted_count, status, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (csv_path.name, int(len(cleaned)), 0, "SUCCESS", "Ingestion started"),
        )
        import_id = cursor.lastrowid

        inserted = 0
        for row in cleaned.itertuples(index=False):
            cursor.execute(
                """
                INSERT OR IGNORE INTO transactions (
                    import_id, txn_date, description, merchant, category,
                    txn_type, amount, balance, reference, txn_hash, raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_id,
                    row.txn_date,
                    row.description,
                    row.merchant,
                    row.category,
                    row.txn_type,
                    float(row.amount),
                    None if pd.isna(row.balance) else float(row.balance),
                    row.reference,
                    row.txn_hash,
                    row.raw_payload,
                ),
            )
            inserted += cursor.rowcount

        cursor.execute(
            "UPDATE imports SET inserted_count = ?, notes = ? WHERE id = ?",
            (inserted, f"Inserted {inserted} rows", import_id),
        )
        conn.commit()

    return IngestionResult(
        source_file=csv_path.name,
        rows_read=int(len(cleaned)),
        rows_inserted=inserted,
        duplicates_skipped=int(len(cleaned) - inserted),
    )
