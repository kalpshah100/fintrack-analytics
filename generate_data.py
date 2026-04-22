"""
FinTrack Analytics - Synthetic Data Generator
Generates realistic fintech transaction data for portfolio project
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── CONFIG ──────────────────────────────────────────────────────────────────
START_DATE = datetime(2023, 1, 1)
END_DATE   = datetime(2024, 6, 30)
N_CUSTOMERS = 5000
N_TRANSACTIONS = 50000

REGIONS = ["Ontario", "British Columbia", "Quebec", "Alberta", "Manitoba"]
REGION_WEIGHTS = [0.38, 0.22, 0.20, 0.15, 0.05]

PRODUCTS = {
    "Savings Account":   {"fee": 0,    "monthly_revenue": (2, 15),   "trend": "stable"},
    "Investment Account":{"fee": 9.99, "monthly_revenue": (20, 120), "trend": "growing"},
    "Credit Card":       {"fee": 0,    "monthly_revenue": (5, 80),   "trend": "declining"},
    "Personal Loan":     {"fee": 29.99,"monthly_revenue": (50, 300), "trend": "stable"},
    "Crypto Wallet":     {"fee": 0,    "monthly_revenue": (1, 200),  "trend": "volatile"},
}

TRANSACTION_TYPES = ["deposit", "withdrawal", "transfer", "payment", "fee", "interest"]
TRANSACTION_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.05, 0.05]

CHURN_SPIKE_MONTHS = [4, 5]   # April–May 2023 churn spike
BC_BOOST_MONTHS   = [10, 11, 12]  # BC outperforms in Q4


# ── CUSTOMERS ───────────────────────────────────────────────────────────────
def generate_customers(n):
    first_names = ["Liam","Emma","Noah","Olivia","Ethan","Ava","Aiden","Sophia",
                   "James","Isabella","Lucas","Mia","Oliver","Charlotte","Mason",
                   "Amelia","Logan","Harper","Raj","Priya","Wei","Mei","Carlos","Ana"]
    last_names  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller",
                   "Davis","Wilson","Taylor","Patel","Singh","Chen","Kim","Nguyen"]

    regions = np.random.choice(REGIONS, size=n, p=REGION_WEIGHTS)
    join_dates = [START_DATE + timedelta(days=random.randint(-365, 180)) for _ in range(n)]

    # ~12% churn rate overall; spike in Apr–May 2023
    churned = []
    churn_dates = []
    for jd in join_dates:
        base_churn = 0.12
        # customers who joined before April are more likely to churn in spike window
        if jd < datetime(2023, 4, 1):
            base_churn = 0.18
        is_churned = random.random() < base_churn
        churned.append(is_churned)
        if is_churned:
            # churn date weighted toward Apr–May 2023
            if random.random() < 0.55:
                churn_month = random.choice(CHURN_SPIKE_MONTHS)
                cd = datetime(2023, churn_month, random.randint(1, 28))
            else:
                cd = jd + timedelta(days=random.randint(60, 500))
                cd = min(cd, END_DATE)
            churn_dates.append(cd)
        else:
            churn_dates.append(None)

    customers = pd.DataFrame({
        "customer_id":  [f"CUST{str(i).zfill(5)}" for i in range(1, n+1)],
        "first_name":   [random.choice(first_names) for _ in range(n)],
        "last_name":    [random.choice(last_names)  for _ in range(n)],
        "email":        [f"user{i}@fintrack.io" for i in range(1, n+1)],
        "region":       regions,
        "age":          np.random.randint(22, 68, size=n),
        "join_date":    join_dates,
        "is_churned":   churned,
        "churn_date":   churn_dates,
        "credit_score": np.random.randint(580, 850, size=n),
        "annual_income":np.random.randint(35000, 220000, size=n),
    })
    return customers


# ── ACCOUNTS ────────────────────────────────────────────────────────────────
def generate_accounts(customers):
    accounts = []
    account_id = 1
    for _, cust in customers.iterrows():
        # each customer gets 1–3 products
        n_products = random.choices([1, 2, 3], weights=[0.4, 0.4, 0.2])[0]
        chosen = random.sample(list(PRODUCTS.keys()), n_products)
        for product in chosen:
            open_date = cust["join_date"] + timedelta(days=random.randint(0, 10))
            close_date = cust["churn_date"] if cust["is_churned"] else None
            accounts.append({
                "account_id":   f"ACC{str(account_id).zfill(6)}",
                "customer_id":  cust["customer_id"],
                "product_name": product,
                "open_date":    open_date,
                "close_date":   close_date,
                "status":       "closed" if cust["is_churned"] else "active",
                "monthly_fee":  PRODUCTS[product]["fee"],
                "balance":      round(random.uniform(100, 50000), 2),
            })
            account_id += 1
    return pd.DataFrame(accounts)


# ── TRANSACTIONS ─────────────────────────────────────────────────────────────
def generate_transactions(accounts, customers, n):
    cust_lookup = customers.set_index("customer_id")["region"].to_dict()
    active_accounts = accounts[accounts["status"] == "active"]["account_id"].tolist()
    all_accounts    = accounts["account_id"].tolist()

    transactions = []
    for i in range(1, n + 1):
        acc_id = random.choice(all_accounts)
        acc_row = accounts[accounts["account_id"] == acc_id].iloc[0]
        region  = cust_lookup.get(acc_row["customer_id"], "Ontario")

        # transaction date between account open and close (or end date)
        t_start = acc_row["open_date"]
        t_end   = acc_row["close_date"] if pd.notna(acc_row["close_date"]) else END_DATE
        if t_start >= t_end:
            t_start = END_DATE - timedelta(days=5)
            t_end   = END_DATE
        days_range = (t_end - t_start).days
        t_date = t_start + timedelta(days=random.randint(0, max(days_range - 1, 0)))

        # BC boost in Q4
        amount_multiplier = 1.0
        if region == "British Columbia" and t_date.month in BC_BOOST_MONTHS:
            amount_multiplier = 1.35

        # seasonality: higher spending Nov–Dec
        if t_date.month in [11, 12]:
            amount_multiplier *= 1.20

        txn_type = random.choices(TRANSACTION_TYPES, weights=TRANSACTION_WEIGHTS)[0]
        base_amount = round(random.uniform(5, 3000) * amount_multiplier, 2)

        # introduce ~3% nulls in description (realistic messiness)
        description = random.choice([
            "Online Transfer", "ATM Withdrawal", "Bill Payment", "Direct Deposit",
            "E-Transfer", "Subscription", "Refund", "Interest Credit", None
        ]) if random.random() > 0.03 else None

        # introduce ~1% duplicate transaction_ids (data quality issue)
        txn_id = f"TXN{str(i).zfill(7)}"
        if random.random() < 0.01 and i > 10:
            txn_id = f"TXN{str(random.randint(1, i-1)).zfill(7)}"

        transactions.append({
            "transaction_id":   txn_id,
            "account_id":       acc_id,
            "transaction_date": t_date,
            "transaction_type": txn_type,
            "amount":           base_amount if txn_type not in ["fee"] else round(random.uniform(1, 30), 2),
            "currency":         random.choices(["CAD", "USD"], weights=[0.93, 0.07])[0],
            "description":      description,
            "status":           random.choices(["completed", "pending", "failed"],
                                               weights=[0.92, 0.05, 0.03])[0],
            "merchant_category":random.choice(["Retail", "Food & Drink", "Travel",
                                               "Entertainment", "Healthcare", "Other", None]),
        })

    return pd.DataFrame(transactions)


# ── REVENUE (monthly aggregate) ──────────────────────────────────────────────
def generate_monthly_revenue(accounts, customers):
    cust_lookup = customers.set_index("customer_id")[["region"]].to_dict("index")
    rows = []
    months = pd.date_range(START_DATE, END_DATE, freq="MS")
    for month in months:
        for _, acc in accounts.iterrows():
            if acc["open_date"] > month + pd.offsets.MonthEnd(0):
                continue
            if pd.notna(acc["close_date"]) and acc["close_date"] < month:
                continue
            product = acc["product_name"]
            lo, hi  = PRODUCTS[product]["monthly_revenue"]
            trend   = PRODUCTS[product]["trend"]
            month_idx = (month.year - 2023) * 12 + month.month

            # apply trend
            if trend == "growing":
                base = random.uniform(lo, hi) * (1 + 0.015 * month_idx)
            elif trend == "declining":
                base = random.uniform(lo, hi) * max(0.5, 1 - 0.012 * month_idx)
            elif trend == "volatile":
                base = random.uniform(lo, hi) * random.uniform(0.3, 2.5)
            else:
                base = random.uniform(lo, hi)

            region = cust_lookup.get(acc["customer_id"], {}).get("region", "Ontario")
            if region == "British Columbia" and month.month in BC_BOOST_MONTHS:
                base *= 1.30

            rows.append({
                "month":        month.strftime("%Y-%m"),
                "account_id":   acc["account_id"],
                "customer_id":  acc["customer_id"],
                "product_name": product,
                "region":       region,
                "revenue":      round(base, 2),
                "fee_charged":  acc["monthly_fee"],
            })
    return pd.DataFrame(rows)


# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🏦 FinTrack Analytics — Generating synthetic data...")

    print("  → Customers...")
    customers = generate_customers(N_CUSTOMERS)
    customers.to_csv(f"{OUTPUT_DIR}/customers.csv", index=False)
    print(f"     {len(customers):,} customers saved")

    print("  → Accounts...")
    accounts = generate_accounts(customers)
    accounts.to_csv(f"{OUTPUT_DIR}/accounts.csv", index=False)
    print(f"     {len(accounts):,} accounts saved")

    print("  → Transactions...")
    transactions = generate_transactions(accounts, customers, N_TRANSACTIONS)
    transactions.to_csv(f"{OUTPUT_DIR}/transactions.csv", index=False)
    print(f"     {len(transactions):,} transactions saved")

    print("  → Monthly Revenue...")
    revenue = generate_monthly_revenue(accounts, customers)
    revenue.to_csv(f"{OUTPUT_DIR}/monthly_revenue.csv", index=False)
    print(f"     {len(revenue):,} revenue rows saved")

    print("\n✅ All datasets written to data/raw/")
    print("\nData quality issues intentionally seeded:")
    print("  • ~3% null descriptions in transactions")
    print("  • ~1% duplicate transaction IDs")
    print("  • ~7% USD transactions (currency inconsistency)")
    print("  • Churn spike in Apr–May 2023")
    print("  • BC revenue boost in Q4")
    print("  • Credit Card product on declining trend")
