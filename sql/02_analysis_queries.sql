-- ============================================================
-- FinTrack Analytics — Business Analysis Queries
-- Phase 1: SQL Analysis (15 queries covering real analyst skills)
-- ============================================================


-- ── Q1. Total revenue by month (MoM trend) ──────────────────
-- Business question: Is overall revenue growing?
SELECT
    month,
    ROUND(SUM(revenue), 2)                                          AS total_revenue,
    ROUND(SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY month), 2) AS mom_change,
    ROUND(
        100.0 * (SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY month))
        / NULLIF(LAG(SUM(revenue)) OVER (ORDER BY month), 0), 2
    )                                                               AS mom_pct_change
FROM monthly_revenue
GROUP BY month
ORDER BY month;


-- ── Q2. Revenue by product (with trend direction) ────────────
-- Business question: Which products are growing vs declining?
WITH monthly_product AS (
    SELECT
        month,
        product_name,
        SUM(revenue) AS revenue
    FROM monthly_revenue
    GROUP BY month, product_name
),
ranked AS (
    SELECT *,
        FIRST_VALUE(revenue) OVER (PARTITION BY product_name ORDER BY month)       AS first_month_rev,
        LAST_VALUE(revenue)  OVER (PARTITION BY product_name ORDER BY month
                                   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_month_rev
    FROM monthly_product
)
SELECT DISTINCT
    product_name,
    ROUND(first_month_rev, 2)  AS jan_2023_revenue,
    ROUND(last_month_rev, 2)   AS jun_2024_revenue,
    ROUND(100.0 * (last_month_rev - first_month_rev) / NULLIF(first_month_rev, 0), 1) AS total_growth_pct,
    CASE
        WHEN last_month_rev > first_month_rev * 1.10 THEN '📈 Growing'
        WHEN last_month_rev < first_month_rev * 0.90 THEN '📉 Declining'
        ELSE '➡️ Stable'
    END AS trend
FROM ranked
ORDER BY total_growth_pct DESC;


-- ── Q3. Revenue by region ────────────────────────────────────
-- Business question: Which region is outperforming?
SELECT
    region,
    ROUND(SUM(revenue), 2)                                     AS total_revenue,
    ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) AS revenue_share_pct,
    COUNT(DISTINCT customer_id)                                 AS unique_customers,
    ROUND(SUM(revenue) / COUNT(DISTINCT customer_id), 2)        AS revenue_per_customer
FROM monthly_revenue
GROUP BY region
ORDER BY total_revenue DESC;


-- ── Q4. Customer churn analysis ──────────────────────────────
-- Business question: When did churn spike and why?
SELECT
    TO_CHAR(churn_date, 'YYYY-MM')          AS churn_month,
    COUNT(*)                                 AS churned_customers,
    ROUND(AVG(credit_score), 0)              AS avg_credit_score,
    ROUND(AVG(annual_income), 0)             AS avg_income,
    ROUND(AVG(EXTRACT(YEAR FROM AGE(churn_date, join_date)) * 12
            + EXTRACT(MONTH FROM AGE(churn_date, join_date))), 1) AS avg_months_as_customer
FROM customers
WHERE is_churned = TRUE
  AND churn_date IS NOT NULL
GROUP BY churn_month
ORDER BY churn_month;


-- ── Q5. Cohort retention (monthly cohorts) ───────────────────
-- Business question: Do customers who joined in certain months retain better?
WITH cohorts AS (
    SELECT
        customer_id,
        TO_CHAR(join_date, 'YYYY-MM') AS cohort_month
    FROM customers
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),
retained AS (
    SELECT
        c.cohort_month,
        TO_CHAR(DATE_TRUNC('month', t.transaction_date), 'YYYY-MM') AS active_month,
        COUNT(DISTINCT c.customer_id) AS active_customers
    FROM cohorts c
    JOIN accounts a ON c.customer_id = a.customer_id
    JOIN transactions t ON a.account_id = t.account_id
    WHERE t.status = 'completed'
    GROUP BY c.cohort_month, active_month
)
SELECT
    r.cohort_month,
    cs.cohort_size,
    r.active_month,
    r.active_customers,
    ROUND(100.0 * r.active_customers / cs.cohort_size, 1) AS retention_rate_pct
FROM retained r
JOIN cohort_sizes cs ON r.cohort_month = cs.cohort_month
ORDER BY r.cohort_month, r.active_month;


-- ── Q6. RFM Scoring (Recency, Frequency, Monetary) ──────────
-- Business question: Who are our most valuable customers?
WITH customer_txn AS (
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name  AS customer_name,
        c.region,
        MAX(t.transaction_date)             AS last_transaction,
        COUNT(t.transaction_id)             AS frequency,
        SUM(t.amount)                       AS monetary
    FROM customers c
    JOIN accounts a  ON c.customer_id  = a.customer_id
    JOIN transactions t ON a.account_id = t.account_id
    WHERE t.status = 'completed'
      AND t.transaction_type != 'fee'
      AND c.is_churned = FALSE
    GROUP BY c.customer_id, customer_name, c.region
),
rfm_base AS (
    SELECT *,
        CURRENT_DATE - last_transaction AS recency_days,
        NTILE(5) OVER (ORDER BY CURRENT_DATE - last_transaction ASC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency DESC)                        AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC)                         AS m_score
    FROM customer_txn
)
SELECT
    customer_id,
    customer_name,
    region,
    recency_days,
    frequency,
    ROUND(monetary, 2)          AS monetary,
    r_score, f_score, m_score,
    r_score + f_score + m_score AS rfm_total,
    CASE
        WHEN r_score + f_score + m_score >= 13 THEN 'Champions'
        WHEN r_score + f_score + m_score >= 10 THEN 'Loyal Customers'
        WHEN r_score + f_score + m_score >= 7  THEN 'Potential Loyalists'
        WHEN r_score <= 2                       THEN 'At Risk'
        ELSE 'Others'
    END AS rfm_segment
FROM rfm_base
ORDER BY rfm_total DESC;


-- ── Q7. Product cross-sell opportunities ─────────────────────
-- Business question: Which customers only have 1 product? (upsell targets)
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.region,
    c.credit_score,
    COUNT(a.account_id)                AS product_count,
    STRING_AGG(a.product_name, ', ')   AS products_held,
    c.annual_income
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
WHERE a.status = 'active'
  AND c.is_churned = FALSE
GROUP BY c.customer_id, customer_name, c.region, c.credit_score, c.annual_income
HAVING COUNT(a.account_id) = 1
ORDER BY c.credit_score DESC
LIMIT 100;


-- ── Q8. Transaction anomalies ────────────────────────────────
-- Business question: Are there suspicious high-value transactions?
WITH stats AS (
    SELECT
        AVG(amount)    AS avg_amount,
        STDDEV(amount) AS std_amount
    FROM transactions
    WHERE status = 'completed'
      AND transaction_type != 'fee'
)
SELECT
    t.transaction_id,
    t.account_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    t.transaction_date,
    t.transaction_type,
    t.amount,
    t.currency,
    t.merchant_category,
    ROUND((t.amount - s.avg_amount) / NULLIF(s.std_amount, 0), 2) AS z_score
FROM transactions t
JOIN accounts a  ON t.account_id   = a.account_id
JOIN customers c ON a.customer_id  = c.customer_id
CROSS JOIN stats s
WHERE t.status = 'completed'
  AND (t.amount - s.avg_amount) / NULLIF(s.std_amount, 0) > 3
ORDER BY z_score DESC
LIMIT 50;


-- ── Q9. Data quality audit ───────────────────────────────────
-- Business question: What are the data issues we need to fix?
SELECT 'transactions' AS table_name, 'null description' AS issue,
       COUNT(*) AS affected_rows
FROM transactions WHERE description IS NULL
UNION ALL
SELECT 'transactions', 'duplicate transaction_id',
       COUNT(*) - COUNT(DISTINCT transaction_id)
FROM transactions
UNION ALL
SELECT 'transactions', 'USD currency (needs conversion)',
       COUNT(*)
FROM transactions WHERE currency = 'USD'
UNION ALL
SELECT 'transactions', 'failed status',
       COUNT(*)
FROM transactions WHERE status = 'failed'
UNION ALL
SELECT 'customers', 'churned without churn_date',
       COUNT(*)
FROM customers WHERE is_churned = TRUE AND churn_date IS NULL;


-- ── Q10. Top 10 customers by lifetime value ──────────────────
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.region,
    c.join_date,
    ROUND(SUM(mr.revenue), 2)          AS lifetime_revenue,
    COUNT(DISTINCT mr.product_name)    AS products_held,
    c.credit_score
FROM customers c
JOIN monthly_revenue mr ON c.customer_id = mr.customer_id
WHERE c.is_churned = FALSE
GROUP BY c.customer_id, customer_name, c.region, c.join_date, c.credit_score
ORDER BY lifetime_revenue DESC
LIMIT 10;


-- ── Q11. BC vs Other Regions Q4 comparison ───────────────────
-- Business question: How much did BC outperform in Q4?
SELECT
    region,
    ROUND(SUM(CASE WHEN month LIKE '%-10' OR month LIKE '%-11' OR month LIKE '%-12'
                   THEN revenue ELSE 0 END), 2) AS q4_revenue,
    ROUND(SUM(CASE WHEN month NOT LIKE '%-10' AND month NOT LIKE '%-11' AND month NOT LIKE '%-12'
                   THEN revenue ELSE 0 END), 2) AS non_q4_revenue,
    ROUND(SUM(revenue), 2)                       AS total_revenue
FROM monthly_revenue
WHERE month LIKE '2023%'
GROUP BY region
ORDER BY q4_revenue DESC;


-- ── Q12. Monthly active users (MAU) ──────────────────────────
SELECT
    TO_CHAR(DATE_TRUNC('month', transaction_date), 'YYYY-MM') AS month,
    COUNT(DISTINCT a.customer_id)                              AS mau
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
WHERE t.status = 'completed'
GROUP BY month
ORDER BY month;


-- ── Q13. Average transaction value by product & type ─────────
SELECT
    a.product_name,
    t.transaction_type,
    COUNT(*)                           AS txn_count,
    ROUND(AVG(t.amount), 2)            AS avg_amount,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.amount), 2) AS median_amount,
    ROUND(MAX(t.amount), 2)            AS max_amount
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
WHERE t.status = 'completed'
GROUP BY a.product_name, t.transaction_type
ORDER BY a.product_name, avg_amount DESC;


-- ── Q14. Churn risk scoring ───────────────────────────────────
-- Business question: Which active customers look like they will churn?
WITH last_activity AS (
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        c.region,
        c.credit_score,
        MAX(t.transaction_date)             AS last_txn_date,
        CURRENT_DATE - MAX(t.transaction_date) AS days_inactive,
        COUNT(t.transaction_id)             AS total_txns
    FROM customers c
    JOIN accounts a  ON c.customer_id  = a.customer_id
    JOIN transactions t ON a.account_id = t.account_id
    WHERE c.is_churned = FALSE
      AND t.status = 'completed'
    GROUP BY c.customer_id, customer_name, c.region, c.credit_score
)
SELECT *,
    CASE
        WHEN days_inactive > 90  AND total_txns < 10  THEN 'High Risk 🔴'
        WHEN days_inactive > 60  AND total_txns < 20  THEN 'Medium Risk 🟡'
        WHEN days_inactive > 30                        THEN 'Low Risk 🟢'
        ELSE 'Healthy ✅'
    END AS churn_risk_label
FROM last_activity
WHERE days_inactive > 30
ORDER BY days_inactive DESC
LIMIT 100;


-- ── Q15. Running total revenue with cumulative share ─────────
SELECT
    month,
    ROUND(SUM(revenue), 2)                                   AS monthly_revenue,
    ROUND(SUM(SUM(revenue)) OVER (ORDER BY month), 2)        AS cumulative_revenue,
    ROUND(100.0 * SUM(SUM(revenue)) OVER (ORDER BY month)
          / SUM(SUM(revenue)) OVER (), 1)                    AS cumulative_pct
FROM monthly_revenue
GROUP BY month
ORDER BY month;
