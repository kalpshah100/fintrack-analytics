"""
FinTrack Analytics — Load CSVs into PostgreSQL
Run after generate_data.py and after running 01_schema.sql
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os

# ── CONNECTION ────────────────────────────────────────────────────────────────
# Update these with your local PostgreSQL credentials
DB_USER     = "postgres"
DB_PASSWORD = "kalpshah"      # change to your password
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "fintrack"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

DATA_DIR = "data/raw"

def load_table(filename, table_name, parse_dates=None):
    filepath = os.path.join(DATA_DIR, filename)
    print(f"  → Loading {filename} into [{table_name}]...")
    df = pd.read_csv(filepath, parse_dates=parse_dates)
    df.to_sql(table_name, engine, if_exists="append", index=False, method="multi", chunksize=1000)
    print(f"     ✅ {len(df):,} rows loaded")
    return df

if __name__ == "__main__":
    print("🏦 FinTrack — Loading data into PostgreSQL\n")

    # Load in FK-safe order
    load_table("customers.csv",      "customers",      parse_dates=["join_date", "churn_date"])
    load_table("accounts.csv",       "accounts",       parse_dates=["open_date", "close_date"])
    load_table("transactions.csv",   "transactions",   parse_dates=["transaction_date"])
    load_table("monthly_revenue.csv","monthly_revenue")

    # Quick validation
    print("\n📊 Row counts validation:")
    with engine.connect() as conn:
        for table in ["customers", "accounts", "transactions", "monthly_revenue"]:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   {table:<20} {count:>8,} rows")

    print("\n✅ Database ready. Open pgAdmin or run 02_analysis_queries.sql to begin.")
