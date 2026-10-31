# Task `release_next_day` — SUCCESS

*Run 771658537875193 · started 2026-10-30 23:53:05 UTC · 20s*

# 04 · Release the next business day's source files ("tomorrow's feed")

Simulates the nightly arrival of new files from POS and ERP: moves the next staged day (real M5 sales for
2016-05-23 … 05-25 plus the matching simulated inventory snapshot and PO events) into the landing folders.
The next pipeline update then ingests **only the new files** (Auto Loader incremental processing), and the
model's earlier predictions can be checked against what actually happened.

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
RAW = f"/Volumes/{catalog}/{schema}/raw"
FEEDS = [("_staged/pos/daily_sales", "pos/daily_sales", "business_date"),
         ("_staged/erp/inventory_snapshots", "erp/inventory_snapshots", "snapshot_date"),
         ("_staged/erp/po_events", "erp/po_events", "event_date")]

def parts(path, key):
    try:
        return sorted(f.name.rstrip("/").split("=")[1] for f in dbutils.fs.ls(f"{RAW}/{path}") if f.name.startswith(key + "="))
    except Exception:
        return []

staged = parts(FEEDS[0][0], FEEDS[0][2])
landed = parts(FEEDS[1][1], FEEDS[1][2])
print(f"staged days: {staged}\nlatest landed inventory day: {landed[-1] if landed else None}")
if not staged:
    dbutils.notebook.exit("nothing left to release")
day = staged[0]
```

**Output:**

```text
staged days: ['2016-05-23', '2016-05-24', '2016-05-25']
latest landed inventory day: 2016-05-22
```

```python
for src, dst, key in FEEDS:
    s, d = f"{RAW}/{src}/{key}={day}", f"{RAW}/{dst}/{key}={day}"
    files = [f for f in dbutils.fs.ls(s) if not f.name.startswith("_")]
    for f in files:
        dbutils.fs.cp(f.path, f"{d}/{f.name}")
    dbutils.fs.rm(s, recurse=True)
    print(f"released {key}={day}: {len(files)} file(s) -> {dst}/")
dbutils.notebook.exit(f"released {day}")
```

**Output:**

```text
released 2016-05-23
```
