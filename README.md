# 🏦 FinTrack Analytics — Customer Spending & Revenue Intelligence

> **Portfolio project** simulating a real data analyst workflow at a fintech company.  
> Stack: PostgreSQL · Python (pandas, seaborn) · Power BI · GitHub

---

## 📌 Business Context

FinTrack is a fictional Canadian fintech offering savings accounts, investment accounts, credit cards, personal loans, and crypto wallets. As the data analyst, you've been asked to:

1. Understand revenue trends across products and regions
2. Identify which customer segments are most valuable (RFM analysis)
3. Flag customers at risk of churning
4. Deliver an executive dashboard to leadership

---

## 🔍 Key Findings

| Finding | Detail |
|---|---|
| **Churn Spike** | 18% of customers churned in Apr–May 2023 vs. 12% baseline |
| **BC Outperformance** | British Columbia generated 30% more revenue per customer in Q4 2023 |
| **Declining Product** | Credit Card revenue declined ~15% over 18 months |
| **Top Segment** | Champions (top RFM) account for ~35% of total revenue with only ~12% of customers |
| **Cross-sell Opportunity** | ~40% of active customers hold only 1 product |

---

## 🛠️ Tech Stack

| Tool | Usage |
|---|---|
| **PostgreSQL** | Relational data store, 15+ analytical SQL queries |
| **Python / pandas** | Data cleaning, RFM segmentation, churn scoring |
| **Seaborn / Matplotlib** | Exploratory charts |
| **Power BI** | 3-page executive dashboard |
| **SQLAlchemy** | Python ↔ PostgreSQL connection |
| **GitHub** | Version control |

---

## 📁 Project Structure

```
fintrack/
├── data/
│   ├── raw/                    # Generated CSVs (customers, accounts, transactions, revenue)
│   └── powerbi_exports/        # Clean exports for Power BI
├── sql/
│   ├── 01_schema.sql           # Table creation
│   └── 02_analysis_queries.sql # 15 business SQL queries
├── charts/                     # Python-generated charts
├── generate_data.py            # Synthetic data generator
├── load_to_postgres.py         # CSV → PostgreSQL loader
├── analysis.py                 # RFM + churn scoring + exports
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ (pgAdmin optional but recommended)
- Power BI Desktop (free)

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Generate data
```bash
python generate_data.py
```

### Step 3 — Set up PostgreSQL
1. Create a database called `fintrack` in PostgreSQL
2. Run `sql/01_schema.sql` to create tables
3. Update DB credentials in `load_to_postgres.py`
4. Run: `python load_to_postgres.py`

### Step 4 — Run analysis
```bash
python analysis.py
```

### Step 5 — Power BI
1. Open Power BI Desktop
2. Get Data → Text/CSV → point to `data/powerbi_exports/`
3. Import all 4 CSVs and build the dashboard (see Power BI guide below)

---

## 📊 SQL Concepts Demonstrated

- Window functions (`LAG`, `LEAD`, `NTILE`, `FIRST_VALUE`, `LAST_VALUE`, running totals)
- CTEs (Common Table Expressions)
- Cohort analysis
- RFM scoring
- Churn flag logic
- Data quality auditing
- Percentile functions (`PERCENTILE_CONT`)
- Conditional aggregation (`CASE WHEN` inside `SUM`)

---

## 🗒️ Analyst Memo (Summary)

**To:** VP of Revenue, FinTrack  
**From:** Data Analytics Team  
**Re:** Q2 2024 Customer & Revenue Intelligence Report

Revenue grew 22% over the 18-month period, driven primarily by the Investment Account product (+38%) offsetting Credit Card decline (-15%). British Columbia customers generated 30% more revenue per customer in Q4, suggesting a seasonal or demographic effect worth investigating for targeted campaigns.

Customer health shows a concentration risk: our Champions segment (12% of customers) generates 35% of revenue. The Apr–May 2023 churn event affected 18% of the eligible base — correlation with low credit scores (avg 612) suggests a credit-risk-driven offboarding or competitive displacement. Approximately 40% of active customers hold a single product, representing the strongest cross-sell opportunity.

**Recommended actions:**
1. Launch a retention campaign targeting At Risk RFM customers (high recency, low frequency)
2. Investigate BC Q4 outperformance for national campaign replication
3. Design Investment Account upsell offer for single-product Savings customers
4. Deprecate or redesign Credit Card product offering

---

## 📝 Data Note

Data is synthetically generated using Python (numpy, random) with realistic patterns including: seasonality, a churn spike, a declining product trend, and regional variance. No real customer data was used.

---

*Built as a portfolio project demonstrating end-to-end data analyst skills.*
