# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Land the public M5 dataset in the raw volume
# MAGIC
# MAGIC Source: **M5 Forecasting – Accuracy** (Makridakis et al., 2020), Walmart daily unit sales for 3,049 items
# MAGIC across 10 stores in California, Texas and Wisconsin, 2011-01-29 → 2016-06-19, with prices and an events/SNAP calendar.
# MAGIC Fetched from Nixtla's public mirror of the competition files. Files are landed **unchanged**:
# MAGIC
# MAGIC | Landing path | File | Role |
# MAGIC |---|---|---|
# MAGIC | `raw/m5/calendar/` | `calendar.csv` | date dimension, events, SNAP days |
# MAGIC | `raw/m5/sell_prices/` | `sell_prices.csv` | weekly shelf price per store-item |
# MAGIC | `raw/m5/sales_history/` | `sales_train_evaluation.csv` | wide daily unit sales d_1 … d_1941 (to 2016-05-22) |
# MAGIC | `raw/m5_holdout/` | `sales_test_evaluation.csv` | d_1942 … d_1969 — *not* ingested; replayed later as "tomorrow's" POS feed |

# COMMAND ----------

dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
RAW = f"/Volumes/{catalog}/{schema}/raw"
M5_URL = "https://github.com/Nixtla/m5-forecasts/raw/main/datasets/m5.zip"

# COMMAND ----------

import os, shutil, urllib.request, zipfile, hashlib

tmp = "/tmp/m5"
os.makedirs(tmp, exist_ok=True)
zip_path = f"{tmp}/m5.zip"
urllib.request.urlretrieve(M5_URL, zip_path)
sha = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
print(f"downloaded {os.path.getsize(zip_path):,} bytes  sha256={sha}")
with zipfile.ZipFile(zip_path) as z:
    z.extractall(tmp)
    print("\n".join(f"  {i.filename:32s} {i.file_size:>12,} bytes" for i in z.infolist()))

# COMMAND ----------

layout = {
    "calendar.csv": "m5/calendar",
    "sell_prices.csv": "m5/sell_prices",
    "sales_train_evaluation.csv": "m5/sales_history",
    "sales_test_evaluation.csv": "m5_holdout",
}
for fname, sub in layout.items():
    dest_dir = f"{RAW}/{sub}"
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copyfile(f"{tmp}/{fname}", f"{dest_dir}/{fname}")
    print(f"landed {fname:30s} -> {dest_dir}/  ({os.path.getsize(f'{dest_dir}/{fname}'):,} bytes)")

# COMMAND ----------

# Quick profile of what was landed (read straight from the volume)
cal = spark.read.option("header", True).csv(f"{RAW}/m5/calendar")
sales = spark.read.option("header", True).csv(f"{RAW}/m5/sales_history")
prices = spark.read.option("header", True).csv(f"{RAW}/m5/sell_prices")
print(f"calendar rows      : {cal.count():,}  ({cal.agg({'date':'min'}).first()[0]} -> {cal.agg({'date':'max'}).first()[0]})")
print(f"sales series (rows): {sales.count():,}  columns: {len(sales.columns):,}")
print(f"price rows         : {prices.count():,}")
display(sales.groupBy("state_id", "store_id").count().orderBy("store_id"))
