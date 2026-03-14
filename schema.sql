PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    row_count INTEGER NOT NULL,
    inserted_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILED')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL,
    txn_date TEXT NOT NULL,
    description TEXT NOT NULL,
    merchant TEXT,
    category TEXT NOT NULL,
    txn_type TEXT NOT NULL CHECK (txn_type IN ('DEBIT', 'CREDIT')),
    amount REAL NOT NULL,
    balance REAL,
    reference TEXT,
    txn_hash TEXT NOT NULL UNIQUE,
    raw_payload TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (import_id) REFERENCES imports(id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_txn_date ON transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(txn_type);
CREATE INDEX IF NOT EXISTS idx_transactions_import_id ON transactions(import_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    action_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE TRIGGER IF NOT EXISTS trg_audit_insert_transaction
AFTER INSERT ON transactions
BEGIN
    INSERT INTO audit_log (transaction_id, action)
    VALUES (NEW.id, 'INSERT');
END;

CREATE TABLE IF NOT EXISTS model_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    model_name TEXT NOT NULL,
    target_month TEXT NOT NULL,
    metric_name TEXT,
    metric_value REAL,
    predicted_income REAL NOT NULL,
    predicted_expense REAL NOT NULL,
    net_cashflow REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    transaction_id INTEGER NOT NULL,
    anomaly_score REAL NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE VIEW IF NOT EXISTS vw_monthly_summary AS
SELECT
    strftime('%Y-%m', txn_date) AS month,
    ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) AS total_income,
    ROUND(ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)), 2) AS total_expense,
    ROUND(SUM(amount), 2) AS net_cashflow,
    COUNT(*) AS transaction_count
FROM transactions
GROUP BY strftime('%Y-%m', txn_date)
ORDER BY month;

CREATE VIEW IF NOT EXISTS vw_category_expense AS
SELECT
    strftime('%Y-%m', txn_date) AS month,
    category,
    ROUND(ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)), 2) AS expense
FROM transactions
GROUP BY strftime('%Y-%m', txn_date), category
ORDER BY month, expense DESC;

CREATE VIEW IF NOT EXISTS vw_cashflow_trend AS
WITH monthly AS (
    SELECT
        strftime('%Y-%m', txn_date) AS month,
        ROUND(SUM(amount), 2) AS net_cashflow
    FROM transactions
    GROUP BY strftime('%Y-%m', txn_date)
)
SELECT
    month,
    net_cashflow,
    LAG(net_cashflow) OVER (ORDER BY month) AS previous_month_cashflow,
    ROUND(net_cashflow - LAG(net_cashflow) OVER (ORDER BY month), 2) AS month_over_month_change
FROM monthly
ORDER BY month;
