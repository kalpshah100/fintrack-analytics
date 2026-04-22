-- ============================================================
-- FinTrack Analytics — Database Schema
-- Run this first to create all tables
-- ============================================================

-- Drop tables if re-running
DROP TABLE IF EXISTS monthly_revenue CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ── CUSTOMERS ────────────────────────────────────────────────
CREATE TABLE customers (
    customer_id     VARCHAR(10) PRIMARY KEY,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    email           VARCHAR(100) UNIQUE,
    region          VARCHAR(50),
    age             INT,
    join_date       DATE,
    is_churned      BOOLEAN DEFAULT FALSE,
    churn_date      DATE,
    credit_score    INT,
    annual_income   INT
);

-- ── ACCOUNTS ─────────────────────────────────────────────────
CREATE TABLE accounts (
    account_id      VARCHAR(10) PRIMARY KEY,
    customer_id     VARCHAR(10) REFERENCES customers(customer_id),
    product_name    VARCHAR(50),
    open_date       DATE,
    close_date      DATE,
    status          VARCHAR(10),
    monthly_fee     NUMERIC(8,2),
    balance         NUMERIC(12,2)
);

-- ── TRANSACTIONS ──────────────────────────────────────────────
CREATE TABLE transactions (
    transaction_id      VARCHAR(12),
    account_id          VARCHAR(10) REFERENCES accounts(account_id),
    transaction_date    DATE,
    transaction_type    VARCHAR(20),
    amount              NUMERIC(12,2),
    currency            VARCHAR(3),
    description         VARCHAR(100),
    status              VARCHAR(15),
    merchant_category   VARCHAR(50)
);

-- ── MONTHLY REVENUE ───────────────────────────────────────────
CREATE TABLE monthly_revenue (
    month           VARCHAR(7),
    account_id      VARCHAR(10) REFERENCES accounts(account_id),
    customer_id     VARCHAR(10) REFERENCES customers(customer_id),
    product_name    VARCHAR(50),
    region          VARCHAR(50),
    revenue         NUMERIC(12,2),
    fee_charged     NUMERIC(8,2)
);

-- ── INDEXES ───────────────────────────────────────────────────
CREATE INDEX idx_transactions_date    ON transactions(transaction_date);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_accounts_customer    ON accounts(customer_id);
CREATE INDEX idx_revenue_month        ON monthly_revenue(month);
CREATE INDEX idx_revenue_product      ON monthly_revenue(product_name);
CREATE INDEX idx_revenue_region       ON monthly_revenue(region);

COMMENT ON TABLE customers       IS 'Core customer master table';
COMMENT ON TABLE accounts        IS 'Financial product accounts per customer';
COMMENT ON TABLE transactions    IS 'All transaction events across accounts';
COMMENT ON TABLE monthly_revenue IS 'Pre-aggregated monthly revenue per account';
