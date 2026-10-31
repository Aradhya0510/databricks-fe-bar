# Task `generate_ops_data` — SUCCESS

*Run 968794760217598 · started 2026-10-30 21:34:06 UTC · 341s*

# 02 · Simulate the retailer's ERP / WMS extracts (synthetic, aligned to real M5 demand)

M5 gives us **real demand** but no inventory or supply data. This notebook simulates what the retailer's
ERP and warehouse systems would export, *driven by* the real Walmart sales so the two stay consistent:

* **Stockouts are not invented.** A zero-sales streak is treated as an out-of-stock (OOS) when it is
  statistically implausible under the item-store's own trailing demand rate λ:  `P(0 sales for L days) = e^(-λL) < 1%`.
* Each inferred OOS run is explained by one of two operational root causes:
  * **Supplier delay** (≈75%) – the replenishment PO due before the run arrived late, stock drained to zero.
  * **Phantom inventory** (≈25%) – the system still shows units on hand, so no order was raised (record inaccuracy).
* Outside OOS runs, a periodic-review (R=7d) order-up-to policy with stochastic lead times, partial fills and
  occasional harmless late POs keeps shelves stocked; direct-store-delivery (DSD) top-ups cover demand spikes.

Outputs (all tagged `source=synthetic` downstream):

| Path | Content | Grain |
|---|---|---|
| `raw/erp/stores/` | store master (managers are fictitious) | store |
| `raw/erp/suppliers/` | supplier master incl. contract SLA terms | supplier |
| `raw/erp/item_master/` | item → supplier, unit cost (confidential), case pack | item |
| `raw/erp/inventory_snapshots/snapshot_date=*/` | end-of-day on-hand & on-order | store-item-day |
| `raw/erp/po_events/event_date=*/` | PO lifecycle events (CREATED / RECEIVED) JSON | event |
| `raw/_staged/...` | the 3 days after the as-of date, released later by `03_release_daily_feed` | |

Deliberate data-quality defects are injected (duplicates, negative on-hand, null keys, unknown stores,
inconsistent casing) so the Lakeflow expectations have something real to catch.

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
RAW = f"/Volumes/{catalog}/{schema}/raw"

import datetime as dt
import numpy as np
import pandas as pd
from pyspark.sql import functions as F, types as T

M5_DAY1 = dt.date(2011, 1, 29)
AS_OF = dt.date(2016, 5, 22)                     # last day of sales_train_evaluation (d_1941)
WINDOW_START = AS_OF - dt.timedelta(days=179)    # 180 days of inventory history
WARMUP_START = WINDOW_START - dt.timedelta(days=90)
FEED_DAYS = 3                                    # days 2016-05-23..25 are held back for the incremental demo
FEED_END = AS_OF + dt.timedelta(days=FEED_DAYS)
day_n = lambda d: (d - M5_DAY1).days + 1
print(f"inventory window {WINDOW_START} → {AS_OF}, staged feed → {FEED_END}")
```

**Output:**

```text
inventory window 2015-11-25 → 2016-05-22, staged feed → 2016-05-25
```

## Master data: stores, suppliers, items

```python
rng = np.random.default_rng(20160522)

stores = pd.DataFrame([
    # store_id, state, region, city, sqft, review weekday (0=Mon)
    ("CA_1", "CA", "West", "Los Angeles", 182000, 0), ("CA_2", "CA", "West", "San Diego", 176000, 1),
    ("CA_3", "CA", "West", "San Jose", 204000, 2), ("CA_4", "CA", "West", "Sacramento", 151000, 3),
    ("TX_1", "TX", "South", "Houston", 188000, 0), ("TX_2", "TX", "South", "Dallas", 197000, 1),
    ("TX_3", "TX", "South", "Austin", 169000, 2),
    ("WI_1", "WI", "Midwest", "Milwaukee", 172000, 0), ("WI_2", "WI", "Midwest", "Madison", 165000, 1),
    ("WI_3", "WI", "Midwest", "Green Bay", 158000, 2),
], columns=["store_id", "state_id", "region", "city", "sqft", "review_weekday"])
first = ["Maria", "James", "Priya", "Daniel", "Aisha", "Kevin", "Sofia", "Marcus", "Elena", "Tom"]
last = ["Alvarez", "Chen", "Patel", "Okafor", "Nguyen", "Brooks", "Rossi", "Hall", "Kowalski", "Reyes"]
stores["store_name"] = "Store " + stores.store_id + " · " + stores.city
stores["store_manager"] = [f"{f} {l}" for f, l in zip(first, last)]
stores["store_manager_email"] = [f"{f.lower()}.{l.lower()}@osa-demo-retail.example" for f, l in zip(first, last)]
stores["regional_manager_email"] = stores.region.map({
    "West": "west.rm@osa-demo-retail.example", "South": "south.rm@osa-demo-retail.example",
    "Midwest": "midwest.rm@osa-demo-retail.example"})
stores["opened_date"] = pd.to_datetime(rng.choice(pd.date_range("1994-01-01", "2008-12-31"), len(stores))).date

dept_suppliers = {
    "FOODS_1": ["Golden Prairie Dairy Co", "Riverbend Fresh Foods", "Sunvale Bakery Partners"],
    "FOODS_2": ["Harvest Lane Grocers Supply", "Blue Ridge Pantry Distributors", "Coastal Canning Co"],
    "FOODS_3": ["Northstar Snacks & Beverage", "Evergreen Foods Wholesale", "Prime Valley Distribution",
                "Lakeshore Beverage Group"],
    "HOBBIES_1": ["Brightline Toys & Crafts", "Summit Hobby Wholesale", "Maker's Mark Supply Co"],
    "HOBBIES_2": ["Pinecrest Leisure Goods", "Atlas Party & Seasonal"],
    "HOUSEHOLD_1": ["CleanWave Home Products", "Ironwood Household Supply", "Polaris Paper & Plastics"],
    "HOUSEHOLD_2": ["Hearthstone Home Goods", "Meridian Kitchen & Bath", "Crestview Hardware Wholesale"],
}
sup_rows = []
for dept, names in dept_suppliers.items():
    for n in names:
        reliability = rng.choice(["A", "B", "C"], p=[0.45, 0.4, 0.15])
        sup_rows.append(dict(
            supplier_id=f"SUP{len(sup_rows)+1:03d}", supplier_name=n, primary_dept_id=dept,
            reliability_tier=reliability,
            contract_lead_time_days=int(rng.choice([2, 3, 4, 5, 6, 7], p=[.1, .25, .25, .2, .12, .08])),
            contract_on_time_sla_pct=float({"A": 97, "B": 95, "C": 92}[reliability]),
            contract_fill_rate_sla_pct=float({"A": 98, "B": 96, "C": 94}[reliability]),
            late_penalty_pct_of_po=float({"A": 1.0, "B": 1.5, "C": 2.0}[reliability]),
            payment_terms=rng.choice(["NET30", "NET45", "NET60"]),
            account_manager_email=f"am.{n.split()[0].lower()}@{n.split()[0].lower()}-supply.example",
        ))
suppliers = pd.DataFrame(sup_rows)
print(suppliers[["supplier_id", "supplier_name", "primary_dept_id", "reliability_tier", "contract_lead_time_days"]].to_string(index=False))
```

**Output:**

```text
supplier_id                  supplier_name primary_dept_id reliability_tier  contract_lead_time_days
     SUP001        Golden Prairie Dairy Co         FOODS_1                A                        5
     SUP002          Riverbend Fresh Foods         FOODS_1                B                        5
     SUP003        Sunvale Bakery Partners         FOODS_1                A                        2
     SUP004    Harvest Lane Grocers Supply         FOODS_2                C                        4
     SUP005 Blue Ridge Pantry Distributors         FOODS_2                B                        2
     SUP006             Coastal Canning Co         FOODS_2                A                        6
     SUP007    Northstar Snacks & Beverage         FOODS_3                B                        3
     SUP008      Evergreen Foods Wholesale         FOODS_3                B                        4
     SUP009      Prime Valley Distribution         FOODS_3                C                        5
     SUP010       Lakeshore Beverage Group         FOODS_3                C                        3
     SUP011       Brightline Toys & Crafts       HOBBIES_1                C                        3
     SUP012         Summit Hobby Wholesale       HOBBIES_1                B                        4
     SUP013         Maker's Mark Supply Co       HOBBIES_1                B                        4
     SUP014        Pinecrest Leisure Goods       HOBBIES_2                A                        5
     SUP015         Atlas Party & Seasonal       HOBBIES_2                A                        4
     SUP016        CleanWave Home Products     HOUSEHOLD_1                A                        5
     SUP017      Ironwood Household Supply     HOUSEHOLD_1                B                        2
     SUP018       Polaris Paper & Plastics     HOUSEHOLD_1                B                        3
     SUP019         Hearthstone Home Goods     HOUSEHOLD_2                A                        5
     SUP020        Meridian Kitchen & Bath     HOUSEHOLD_2                B                        3
     SUP021   Crestview Hardware Wholesale     HOUSEHOLD_2                A                        3
```

```python
wide = (spark.read.option("header", True).option("inferSchema", False).csv(f"{RAW}/m5/sales_history"))
hold = (spark.read.option("header", True).option("inferSchema", False).csv(f"{RAW}/m5_holdout"))
items = wide.select("item_id", "dept_id", "cat_id").distinct().toPandas().sort_values("item_id")

nouns = {
    "FOODS_1": ["Whole Milk", "Greek Yogurt", "Cheddar Block", "Butter", "Large Eggs", "Sourdough Loaf", "Bagels", "Cream Cheese"],
    "FOODS_2": ["Pasta", "Tomato Sauce", "Black Beans", "Rice", "Peanut Butter", "Cereal", "Canned Tuna", "Soup"],
    "FOODS_3": ["Tortilla Chips", "Sparkling Water", "Cola 12pk", "Granola Bars", "Frozen Pizza", "Ice Cream", "Coffee", "Juice"],
    "HOBBIES_1": ["Puzzle 1000pc", "Acrylic Paint Set", "Building Blocks", "Yarn Bundle", "Board Game", "Sketchbook"],
    "HOBBIES_2": ["Party Balloons", "Gift Wrap", "Seasonal Decor", "Greeting Cards"],
    "HOUSEHOLD_1": ["Paper Towels", "Laundry Detergent", "Dish Soap", "Trash Bags", "Bath Tissue", "Surface Cleaner"],
    "HOUSEHOLD_2": ["Storage Bins", "Frying Pan", "Bath Towels", "Light Bulbs", "Shower Curtain", "Food Containers"],
}
brands = ["Great Value", "Marketside", "Equate", "Mainstays", "Parent's Choice", "Hearth & Home", "Sunny Fields", "Northpeak"]
def _desc(row):
    h = int(row.item_id.split("_")[-1])
    return f"{brands[h % len(brands)]} {nouns[row.dept_id][h % len(nouns[row.dept_id])]} #{h:03d}"
items["item_name"] = items.apply(_desc, axis=1)
sup_by_dept = suppliers.groupby("primary_dept_id").supplier_id.apply(list).to_dict()
items["supplier_id"] = [sup_by_dept[d][int(i.split("_")[-1]) % len(sup_by_dept[d])] for d, i in zip(items.dept_id, items.item_id)]
items["negotiated_cost_ratio"] = np.round(rng.uniform(0.55, 0.78, len(items)), 3)  # landed cost / shelf price
items["case_pack"] = rng.choice([4, 6, 8, 12, 24], len(items))
print(f"items: {len(items):,}")
```

**Output:**

```text
items: 3,049
```

## Daily demand for the simulation window (real M5 units)

```python
def long_sales(df, d_from, d_to):
    cols = [c for c in df.columns if c.startswith("d_") and d_from <= int(c[2:]) <= d_to]
    expr = "stack({n}, {pairs}) as (d, units)".format(n=len(cols), pairs=", ".join(f"'{c}', `{c}`" for c in cols))
    return df.select("store_id", "item_id", F.expr(expr))

sales_long = (long_sales(wide, day_n(WARMUP_START), day_n(AS_OF))
              .unionByName(long_sales(hold, day_n(AS_OF) + 1, day_n(FEED_END)))
              .withColumn("date", F.date_add(F.lit(M5_DAY1), F.substring("d", 3, 10).cast("int") - 1))
              .withColumn("units", F.col("units").cast("int"))
              .drop("d"))

params = (spark.createDataFrame(items[["item_id", "supplier_id", "case_pack"]])
          .join(spark.createDataFrame(suppliers[["supplier_id", "contract_lead_time_days", "reliability_tier"]]), "supplier_id")
          .crossJoin(spark.createDataFrame(stores[["store_id", "review_weekday"]])))
sim_in = sales_long.join(F.broadcast(params), ["store_id", "item_id"])
print(f"simulation input rows: {sim_in.count():,}")
```

**Output:**

```text
simulation input rows: 8,323,770
```

## Per store-item simulation (`applyInPandas`)

```python
INV_SCHEMA = "store_id string, item_id string, snapshot_date date, on_hand_units int, on_order_units int, kind string"
PO_SCHEMA = ("po_id string, store_id string, item_id string, supplier_id string, event_type string, event_date date, "
             "expected_date date, qty int, kind string")
OUT_SCHEMA = ("rec string, store_id string, item_id string, supplier_id string, d date, a int, b int, "
              "po_id string, event_type string, expected_date date")

WS, AO, FE = pd.Timestamp(WINDOW_START), pd.Timestamp(AS_OF), pd.Timestamp(FEED_END)

def simulate(pdf: pd.DataFrame) -> pd.DataFrame:
    import zlib
    pdf = pdf.sort_values("date").reset_index(drop=True)
    store, item, sup = pdf.store_id[0], pdf.item_id[0], pdf.supplier_id[0]
    lt0, review_wd, tier = int(pdf.contract_lead_time_days[0]), int(pdf.review_weekday[0]), pdf.reliability_tier[0]
    r = np.random.default_rng(zlib.crc32(f"{store}|{item}".encode()))
    s = pdf.units.fillna(0).to_numpy()
    dates = pd.to_datetime(pdf.date).to_numpy()
    weekdays = pd.to_datetime(pdf.date).dt.weekday.to_numpy()
    n = len(s)
    lam = pd.Series(s).rolling(90, min_periods=28).mean().shift(1).bfill().fillna(0).to_numpy()

    # infer OOS runs from real sales: zero streak with e^(-λL) < 1%
    oos = np.zeros(n, bool); run_start = {}          # run start index -> run end index
    i = 0
    while i < n:
        if s[i] == 0:
            j = i
            while j + 1 < n and s[j + 1] == 0:
                j += 1
            L, l0 = j - i + 1, lam[i]
            if l0 >= 0.3 and L >= 2 and L * l0 >= 4.6:
                oos[i:j + 1] = True; run_start[i] = j
            i = j + 1
        else:
            i += 1
    phantom_runs = {a for a in run_start if r.random() < 0.25}

    rows = []
    def emit_po(po_id, et, day, exp, qty):
        rows.append(("po", store, item, sup, dates[day] if day < n else None, int(qty), 0, po_id, et,
                     dates[exp] if exp is not None and exp < n else None))

    T_cover = r.uniform(10, 16)                 # order-up-to level in days of demand
    w0 = int(np.searchsorted(dates, np.datetime64(WS)))
    on_hand = int(round(max(lam[w0], 0.2) * T_cover * 0.7)) + 2
    open_pos = []                               # [po_id, receive_day, qty, expected_day]
    seq = 0
    culprit_for = {}                            # run start -> planned review day whose PO will be late
    for a in run_start:
        if a in phantom_runs or a < w0:
            continue
        exp_day = a - int(r.integers(0, 4))     # PO was due 0-3 days before the shelf went empty
        culprit_for[a] = exp_day
    late_receipts = {}                          # expected day -> actual receive day

    for t in range(w0, n):
        # 1) receipts
        for po in [p for p in open_pos if p[1] == t]:
            on_hand += po[2]; emit_po(po[0], "RECEIVED", t, po[3], po[2]); open_pos.remove(po)
        # 2) culprit PO: created L days before its due date, will arrive the day after the OOS run ends
        for a, exp_day in culprit_for.items():
            if t == max(exp_day - lt0, w0):
                seq += 1; pid = f"PO-{store}-{item}-{seq:04d}"
                qty = int(np.ceil(max(lam[a], 0.5) * T_cover))
                recv = run_start[a] + 1
                open_pos.append([pid, recv, qty, exp_day]); emit_po(pid, "CREATED", t, exp_day, qty)
        # the replenishment that would have topped up stock ahead of a supplier-delay run is skipped,
        # so stock drains naturally into the run (one full review cycle before the culprit PO)
        pending_culprit = any(exp_day - lt0 - 7 <= t <= run_start[a] for a, exp_day in culprit_for.items())
        # 3) demand
        if oos[t]:
            a = max(k for k in run_start if k <= t)
            if a in phantom_runs:
                on_hand = max(on_hand, int(r.integers(3, 9)))          # system still believes stock exists
                if t == run_start[a]:                                   # cycle count corrects, emergency DSD next day
                    on_hand = 0; seq += 1; pid = f"PO-{store}-{item}-{seq:04d}"
                    q = int(np.ceil(max(lam[a], 0.5) * T_cover))
                    open_pos.append([pid, t + 1, q, t + 1]); emit_po(pid, "CREATED", t, t + 1, q)
            else:
                on_hand = 0
        else:
            if on_hand < s[t] and not pending_culprit:                  # DSD top-up keeps records consistent
                seq += 1; pid = f"DSD-{store}-{item}-{seq:04d}"
                q = int(s[t] - on_hand + np.ceil(lam[t] * 3))
                emit_po(pid, "CREATED", t, t, q); emit_po(pid, "RECEIVED", t, t, q); on_hand += q
            on_hand = max(0, on_hand - int(s[t]))
        # 4) periodic review (skipped while a run is in progress or a culprit PO is pending)
        if weekdays[t] == review_wd and not oos[t] and not pending_culprit:
            on_order = sum(p[2] for p in open_pos)
            target = lam[t] * T_cover
            qty = int(np.ceil(max(0.0, target - on_hand - on_order)))
            if qty > 0:
                seq += 1; pid = f"PO-{store}-{item}-{seq:04d}"
                exp = t + lt0
                delay = int(r.choice([0, 1, 2, 3], p={"A": [.93, .05, .015, .005], "B": [.86, .09, .04, .01],
                                                       "C": [.75, .14, .08, .03]}[tier]))
                fill = 1.0 if r.random() < 0.93 else r.uniform(0.6, 0.95)
                open_pos.append([pid, exp + delay, max(1, int(qty * fill)), exp])
                emit_po(pid, "CREATED", t, exp, qty)
        rows.append(("inv", store, item, sup, dates[t], int(on_hand), int(sum(p[2] for p in open_pos)),
                     None, None, None))
    out = pd.DataFrame(rows, columns=["rec", "store_id", "item_id", "supplier_id", "d", "a", "b",
                                      "po_id", "event_type", "expected_date"])
    out["d"] = pd.to_datetime(out["d"]).dt.date
    out["expected_date"] = pd.to_datetime(out["expected_date"]).dt.date
    return out

sim = sim_in.groupBy("store_id", "item_id").applyInPandas(simulate, OUT_SCHEMA)
sim.write.mode("overwrite").saveAsTable(f"{catalog}.{schema}._sim_scratch")
sim = spark.table(f"{catalog}.{schema}._sim_scratch")
display(sim.groupBy("rec", "event_type").count())
```

**Output:**

| rec | event_type | count |
|---|---|---|
| inv |  | 5579670 |
| po | CREATED | 717234 |
| po | RECEIVED | 695115 |

## Write landing files (+ inject data-quality defects)

```python
import shutil, os
for sub in ["erp", "_staged", "pos"]:
    shutil.rmtree(f"{RAW}/{sub}", ignore_errors=True)

def write_master(pdf, name):
    os.makedirs(f"{RAW}/erp/{name}", exist_ok=True)
    pdf.to_csv(f"{RAW}/erp/{name}/{name}.csv", index=False)
    print(f"wrote erp/{name}: {len(pdf)} rows")

write_master(stores, "stores")
write_master(suppliers, "suppliers")
write_master(items, "item_master")

inv = (sim.where("rec = 'inv'")
       .select("store_id", "item_id", F.col("d").alias("snapshot_date"),
               F.col("a").alias("on_hand_units"), F.col("b").alias("on_order_units"))
       .withColumn("extract_ts", F.to_timestamp(F.concat(F.col("snapshot_date").cast("string"), F.lit(" 23:55:00")))))
# defects: 0.1% duplicates, 0.02% negative on-hand, 0.01% null item, unknown store
dups = inv.sample(0.001, seed=1)
neg = inv.sample(0.0002, seed=2).withColumn("on_hand_units", -F.col("on_hand_units") - 1)
nul = inv.sample(0.0001, seed=3).withColumn("item_id", F.lit(None).cast("string"))
unk = inv.where("store_id = 'CA_1'").sample(0.0003, seed=4).withColumn("store_id", F.lit("CA_9"))
inv_all = inv.unionByName(dups).unionByName(neg).unionByName(nul).unionByName(unk)

po = (sim.where("rec = 'po'")
      .select("po_id", "store_id", "item_id", "supplier_id", "event_type",
              F.col("d").alias("event_date"), "expected_date", F.col("a").alias("qty"))
      .where("event_date IS NOT NULL")
      .withColumn("event_ts", F.expr("timestamp(event_date) + make_interval(0,0,0,0, 6 + abs(hash(po_id, event_type)) % 14, abs(hash(po_id)) % 60, 0)"))
      .withColumn("event_type", F.when(F.rand(5) < 0.003, F.lower("event_type")).otherwise(F.col("event_type")))
      .withColumn("qty", F.when(F.rand(6) < 0.0005, F.lit(None)).otherwise(F.col("qty"))))

def write_daily(df, date_col, landing, staged, fmt):
    hist = df.where(F.col(date_col) <= F.lit(AS_OF))
    feed = df.where(F.col(date_col) > F.lit(AS_OF))
    w = lambda d, p: (d.repartition(date_col).write.mode("overwrite").partitionBy(date_col)
                      .option("header", True).format(fmt).save(p))
    w(hist, f"{RAW}/{landing}"); w(feed, f"{RAW}/{staged}")

write_daily(inv_all, "snapshot_date", "erp/inventory_snapshots", "_staged/erp/inventory_snapshots", "csv")
write_daily(po, "event_date", "erp/po_events", "_staged/erp/po_events", "json")

# POS feed for the staged days comes from the real M5 evaluation period (d_1942..d_1944)
pos = (long_sales(hold, day_n(AS_OF) + 1, day_n(FEED_END))
       .withColumn("business_date", F.date_add(F.lit(M5_DAY1), F.substring("d", 3, 10).cast("int") - 1))
       .withColumn("units_sold", F.col("units").cast("int")).drop("d", "units"))
(pos.repartition("business_date").write.mode("overwrite").partitionBy("business_date")
    .option("header", True).csv(f"{RAW}/_staged/pos/daily_sales"))
spark.sql(f"DROP TABLE IF EXISTS {catalog}.{schema}._sim_scratch")
```

**Output:**

```text
wrote erp/stores: 10 rows
wrote erp/suppliers: 21 rows
wrote erp/item_master: 3049 rows
```

## What was generated

```python
for p in ["erp/inventory_snapshots", "erp/po_events", "_staged/erp/inventory_snapshots", "_staged/erp/po_events", "_staged/pos/daily_sales"]:
    parts = [f for f in dbutils.fs.ls(f"{RAW}/{p}") if f.name.endswith("/")]
    print(f"{p:36s} {len(parts):4d} daily partitions  ({parts[0].name} … {parts[-1].name})")

inv_hist = spark.read.option("header", True).csv(f"{RAW}/erp/inventory_snapshots")
print(f"inventory snapshot rows landed: {inv_hist.count():,}")
po_hist = spark.read.json(f"{RAW}/erp/po_events")
display(po_hist.groupBy("event_type").count().orderBy("event_type"))
```

**Output:**

```text
erp/inventory_snapshots               180 daily partitions  (snapshot_date=2015-11-25/ … snapshot_date=2016-05-22/)
erp/po_events                         180 daily partitions  (event_date=2015-11-25/ … event_date=2016-05-22/)
_staged/erp/inventory_snapshots         3 daily partitions  (snapshot_date=2016-05-23/ … snapshot_date=2016-05-25/)
_staged/erp/po_events                   3 daily partitions  (event_date=2016-05-23/ … event_date=2016-05-25/)
_staged/pos/daily_sales                 3 daily partitions  (business_date=2016-05-23/ … business_date=2016-05-25/)
inventory snapshot rows landed: 5,495,410
```

| event_type | count |
|---|---|
| CREATED | 690573 |
| RECEIVED | 684757 |
| created | 2083 |
| received | 2046 |
