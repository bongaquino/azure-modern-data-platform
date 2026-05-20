import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = "./sandbox/data/raw/sales"
N_GOOD = 500
N_BAD = 25
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEGMENTS   = ["Premium", "Standard", "Budget"]
SEG_WEIGHT = [0.20, 0.50, 0.30]
REGIONS    = ["Metro Manila", "Cebu", "Davao", "Clark", "Iloilo"]
CATEGORIES = ["Electronics", "Apparel", "Food & Bev", "Sports", "Home & Living"]
CAT_PRICES = {
    "Electronics":   (3000, 80000),
    "Apparel":       (500,  8000),
    "Food & Bev":    (150,  2000),
    "Sports":        (800,  25000),
    "Home & Living": (400,  15000)
}

def rand_date(start="2025-01-01", end="2025-05-31"):
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end,   "%Y-%m-%d")
    return (s + timedelta(days=random.randint(0, (e-s).days))).strftime("%Y-%m-%d")

def make_customer_id():
    return f"CUST-{random.randint(1000, 9999)}"

# --- GOOD RECORDS ---
good_rows = []
for i in range(N_GOOD):
    seg = random.choices(SEGMENTS, SEG_WEIGHT)[0]
    cat = random.choice(CATEGORIES)
    lo, hi = CAT_PRICES[cat]
    multiplier = 1.8 if seg == "Premium" else (1.0 if seg == "Standard" else 0.6)
    amount = round(random.uniform(lo, hi) * multiplier, 2)
    good_rows.append({
        "sale_id":          f"SALE-{100000 + i}",
        "sale_date":        rand_date(),
        "customer_id":      make_customer_id(),
        "customer_segment": seg,
        "product_id":       f"PROD-{random.randint(1, 200):04d}",
        "product_category": cat,
        "sale_amount":      amount,
        "quantity":         random.randint(1, 5),
        "store_id":         f"STR-{random.randint(1, 20):03d}",
        "region":           random.choice(REGIONS),
        "payment_method":   random.choice(["Credit Card", "GCash", "Cash", "Bank Transfer"]),
        "ingestion_source": "pos_system_v2",
    })

# --- BAD RECORDS (intentional — shows DLT expectations catching them) ---
bad_rows = []
for i in range(N_BAD):
    row = good_rows[i].copy()
    row["sale_id"] = f"BAD-{i:04d}"
    if i % 2 == 0:
        row["sale_amount"] = round(random.uniform(-5000, 0), 2)
        row["_bad_reason"] = "negative_sale_amount"
    else:
        row["customer_id"] = None
        row["_bad_reason"] = "null_customer_id"
    bad_rows.append(row)

# --- WRITE 3 BATCH FILES (simulates files landing over time) ---
df = pd.DataFrame(good_rows + bad_rows).sample(frac=1).reset_index(drop=True)
batch_size = len(df) // 3

for batch_num, start in enumerate(range(0, len(df), batch_size)):
    batch = df.iloc[start:start + batch_size]
    fname = f"{OUTPUT_DIR}/sales_batch_{batch_num + 1:02d}.csv"
    batch.to_csv(fname, index=False)
    print(f"  Written {len(batch)} rows -> {fname}")

print(f"\nDone.")
print(f"  {N_GOOD} good records + {N_BAD} bad records across 3 batch files.")
print(f"  Bad records: {N_BAD//2} negative sale_amount + {N_BAD - N_BAD//2} null customer_id")
print(f"  Silver layer will DROP these {N_BAD} rows -- ready to demo.")
