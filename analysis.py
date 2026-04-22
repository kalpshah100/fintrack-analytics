"""
FinTrack Analytics — Phase 2: Python Analysis
RFM Segmentation, Churn Scoring, Power BI Export
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import os

# ── CONNECTION ────────────────────────────────────────────────────────────────
DB_USER     = "postgres"
DB_PASSWORD = "kalpshah"   # update this
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "fintrack"

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

EXPORT_DIR = "data/powerbi_exports"
CHART_DIR  = "charts"
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)


# ── LOAD DATA ─────────────────────────────────────────────────────────────────
def load_data():
    print("📥 Loading data from PostgreSQL...")
    customers    = pd.read_sql("SELECT * FROM customers",    engine, parse_dates=["join_date","churn_date"])
    accounts     = pd.read_sql("SELECT * FROM accounts",     engine, parse_dates=["open_date","close_date"])
    transactions = pd.read_sql("SELECT * FROM transactions", engine, parse_dates=["transaction_date"])
    revenue      = pd.read_sql("SELECT * FROM monthly_revenue", engine)
    print(f"   ✅ {len(customers):,} customers | {len(transactions):,} transactions | {len(revenue):,} revenue rows")
    return customers, accounts, transactions, revenue


# ── DATA CLEANING ─────────────────────────────────────────────────────────────
def clean_transactions(transactions):
    print("\n🧹 Cleaning transactions...")
    original = len(transactions)

    # Remove duplicates
    transactions = transactions.drop_duplicates(subset=["transaction_id"])
    print(f"   Removed {original - len(transactions)} duplicate transaction IDs")

    # Normalize currency to CAD (simplified: 1 USD = 1.36 CAD)
    usd_mask = transactions["currency"] == "USD"
    transactions.loc[usd_mask, "amount"] = transactions.loc[usd_mask, "amount"] * 1.36
    transactions.loc[usd_mask, "currency"] = "CAD"
    print(f"   Converted {usd_mask.sum()} USD transactions to CAD")

    # Fill null descriptions
    transactions["description"] = transactions["description"].fillna("Unknown")
    print(f"   Filled null descriptions")

    # Keep only completed
    completed = transactions[transactions["status"] == "completed"].copy()
    print(f"   Filtered to {len(completed):,} completed transactions")
    return completed


# ── RFM ANALYSIS ──────────────────────────────────────────────────────────────
def compute_rfm(customers, accounts, transactions):
    print("\n📊 Computing RFM scores...")
    snapshot_date = transactions["transaction_date"].max() + pd.Timedelta(days=1)

    # Merge
    txn_acc = transactions.merge(accounts[["account_id","customer_id"]], on="account_id")
    txn_acc = txn_acc[txn_acc["transaction_type"] != "fee"]

    rfm = txn_acc.groupby("customer_id").agg(
        recency   = ("transaction_date", lambda x: (snapshot_date - x.max()).days),
        frequency = ("transaction_id",   "count"),
        monetary  = ("amount",           "sum")
    ).reset_index()

    # Score 1–5
    rfm["r_score"] = pd.qcut(rfm["recency"],   5, labels=[5,4,3,2,1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"),  5, labels=[1,2,3,4,5]).astype(int)
    rfm["rfm_total"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    def segment(row):
        score = row["rfm_total"]
        if score >= 13:   return "Champions"
        elif score >= 10: return "Loyal Customers"
        elif score >= 7:  return "Potential Loyalists"
        elif row["r_score"] <= 2: return "At Risk"
        else:             return "Others"

    rfm["segment"] = rfm.apply(segment, axis=1)
    rfm["monetary"] = rfm["monetary"].round(2)

    # Join customer info
    rfm = rfm.merge(customers[["customer_id","first_name","last_name","region","is_churned"]], on="customer_id")
    print(f"   ✅ RFM computed for {len(rfm):,} customers")
    print(rfm["segment"].value_counts().to_string())
    return rfm


# ── CHURN RISK SCORING ────────────────────────────────────────────────────────
def compute_churn_risk(rfm, customers):
    print("\n⚠️  Computing churn risk scores...")
    active = rfm[rfm["is_churned"] == False].copy()

    def churn_risk(row):
        score = 0
        if row["recency"] > 90:   score += 3
        elif row["recency"] > 60: score += 2
        elif row["recency"] > 30: score += 1
        if row["frequency"] < 5:  score += 2
        if row["r_score"] <= 2:   score += 2
        if row["m_score"] <= 2:   score += 1
        return score

    active["risk_score"] = active.apply(churn_risk, axis=1)
    active["risk_label"] = pd.cut(active["risk_score"],
                                   bins=[-1, 2, 4, 10],
                                   labels=["Low Risk", "Medium Risk", "High Risk"])
    print("   Risk distribution:")
    print(active["risk_label"].value_counts().to_string())
    return active


# ── CHARTS ────────────────────────────────────────────────────────────────────
def generate_charts(rfm, revenue):
    print("\n🎨 Generating charts...")
    sns.set_theme(style="whitegrid", palette="muted")
    plt.rcParams["figure.dpi"] = 150

    # 1. RFM Segments
    fig, ax = plt.subplots(figsize=(8, 5))
    seg_counts = rfm["segment"].value_counts()
    colors = ["#4C72B0","#DD8452","#55A868","#C44E52","#8172B2"]
    seg_counts.plot(kind="bar", ax=ax, color=colors, edgecolor="white")
    ax.set_title("Customer RFM Segments", fontsize=14, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Number of Customers")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/rfm_segments.png")
    plt.close()
    print("   ✅ rfm_segments.png")

    # 2. Monthly Revenue Trend
    monthly = revenue.groupby("month")["revenue"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(monthly["month"], monthly["revenue"], marker="o", linewidth=2, color="#4C72B0")
    ax.fill_between(range(len(monthly)), monthly["revenue"], alpha=0.1, color="#4C72B0")
    ax.set_xticks(range(len(monthly)))
    ax.set_xticklabels(monthly["month"], rotation=45, ha="right")
    ax.set_title("Monthly Revenue Trend", fontsize=14, fontweight="bold")
    ax.set_ylabel("Revenue (CAD)")
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/monthly_revenue_trend.png")
    plt.close()
    print("   ✅ monthly_revenue_trend.png")

    # 3. Revenue by Region
    region_rev = revenue.groupby("region")["revenue"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    region_rev.plot(kind="barh", ax=ax, color="#55A868", edgecolor="white")
    ax.set_title("Total Revenue by Region", fontsize=14, fontweight="bold")
    ax.set_xlabel("Revenue (CAD)")
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/revenue_by_region.png")
    plt.close()
    print("   ✅ revenue_by_region.png")

    # 4. Product Revenue Trend
    product_monthly = revenue.groupby(["month","product_name"])["revenue"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(12, 6))
    for product in product_monthly["product_name"].unique():
        subset = product_monthly[product_monthly["product_name"] == product]
        ax.plot(subset["month"], subset["revenue"], marker=".", label=product, linewidth=1.5)
    ax.set_xticks(range(len(product_monthly["month"].unique())))
    ax.set_xticklabels(product_monthly["month"].unique(), rotation=45, ha="right")
    ax.set_title("Revenue by Product (Monthly)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Revenue (CAD)")
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/product_revenue_trend.png")
    plt.close()
    print("   ✅ product_revenue_trend.png")


# ── EXPORT FOR POWER BI ───────────────────────────────────────────────────────
def export_for_powerbi(rfm, churn_risk, revenue):
    print("\n📤 Exporting Power BI datasets...")

    # 1. RFM master
    rfm.to_csv(f"{EXPORT_DIR}/rfm_segments.csv", index=False)
    print("   ✅ rfm_segments.csv")

    # 2. Churn risk
    churn_risk[["customer_id","first_name","last_name","region",
                "recency","frequency","monetary","risk_score","risk_label"]]\
        .to_csv(f"{EXPORT_DIR}/churn_risk.csv", index=False)
    print("   ✅ churn_risk.csv")

    # 3. Monthly revenue (already clean from DB)
    revenue.to_csv(f"{EXPORT_DIR}/monthly_revenue.csv", index=False)
    print("   ✅ monthly_revenue.csv")

    # 4. Summary KPIs table
    kpis = pd.DataFrame([{
        "total_customers":    len(rfm),
        "champions":          (rfm["segment"] == "Champions").sum(),
        "at_risk":            (rfm["segment"] == "At Risk").sum(),
        "avg_monetary":       round(rfm["monetary"].mean(), 2),
        "avg_recency_days":   round(rfm["recency"].mean(), 1),
        "total_revenue":      round(revenue["revenue"].sum(), 2),
    }])
    kpis.to_csv(f"{EXPORT_DIR}/kpi_summary.csv", index=False)
    print("   ✅ kpi_summary.csv")

    print(f"\n   All exports saved to /{EXPORT_DIR}/")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  FinTrack Analytics — Phase 2 Python Analysis")
    print("=" * 55)

    customers, accounts, transactions, revenue = load_data()
    transactions_clean = clean_transactions(transactions)
    rfm        = compute_rfm(customers, accounts, transactions_clean)
    churn_risk = compute_churn_risk(rfm, customers)

    generate_charts(rfm, revenue)
    export_for_powerbi(rfm, churn_risk, revenue)

    print("\n🎉 Phase 2 complete!")
    print("   → Charts saved to /charts/")
    print("   → Power BI CSVs saved to /data/powerbi_exports/")
    print("   → Next: Open Power BI Desktop and connect to /data/powerbi_exports/")
