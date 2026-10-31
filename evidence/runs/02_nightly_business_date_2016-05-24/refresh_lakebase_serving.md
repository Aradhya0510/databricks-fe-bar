# Task `refresh_lakebase_serving` — SUCCESS

*Run 1069883414812174 · started 2026-10-31 00:35:45 UTC · 88s*

# Lakebase 2/2 · Refresh the operational serving tables

Gold Delta tables are served to the app from **Lakebase Postgres** via *synced tables* (managed by Lakeflow):

| Lakebase table (`osa_lakebase.serving.*`) | Source (Delta) | Used by |
|---|---|---|
| `replenishment_recommendations` | `gold_replenishment_recommendations` | store action queue (sub-second lookups) |
| `stockout_risk_scores` | `gold_stockout_risk_scores` | item search / typeahead |
| `intelligence_reports` | `gold_intelligence_reports` | nightly briefings page |

Synced tables are created once by `scripts/setup_lakebase.sh`; this task triggers their refresh after the nightly
scoring + agent run and verifies Postgres row counts against Delta.

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("lakebase_catalog", "osa_lakebase")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
LB = dbutils.widgets.get("lakebase_catalog")
S = f"{catalog}.{schema}"

import time
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

SYNCED = {"replenishment_recommendations": "gold_replenishment_recommendations",
          "stockout_risk_scores": "gold_stockout_risk_scores",
          "intelligence_reports": "gold_intelligence_reports"}

def synced_table(name):
    return w.api_client.do("GET", f"/api/2.0/postgres/synced_tables/{LB}.serving.{name}")

started = {}
for target in SYNCED:
    st = synced_table(target)
    pid = (st.get("status") or {}).get("pipeline_id") or st.get("data_synchronization_status", {}).get("pipeline_id")
    upd = w.pipelines.start_update(pipeline_id=pid, full_refresh=False)
    started[target] = (pid, upd.update_id)
    print(f"refresh started: {LB}.serving.{target}  pipeline={pid} update={upd.update_id}")
```

**Output:**

```text
refresh started: osa_lakebase.serving.replenishment_recommendations  pipeline=87d43533-ad93-46d6-8647-9a7724fcd75c update=c8f2af1e-f3b9-4b8a-bdac-45ac67b9dc9b
refresh started: osa_lakebase.serving.stockout_risk_scores  pipeline=fa08392a-1518-4d6a-88eb-f935c53c7ba5 update=47194ae3-f3fb-4275-a02a-db7d2f9fad31
refresh started: osa_lakebase.serving.intelligence_reports  pipeline=3b3c9c11-4a13-481b-90c4-a82d34ee6102 update=df81bab1-3729-4f5a-a992-24d221dbbe82
```

```python
pending = dict(started)
deadline = time.time() + 1800
while pending and time.time() < deadline:
    for target, (pid, uid) in list(pending.items()):
        state = w.pipelines.get_update(pipeline_id=pid, update_id=uid).update.state.value
        if state in ("COMPLETED", "FAILED", "CANCELED"):
            print(f"{target:32s} {state}")
            pending.pop(target)
    time.sleep(15)
assert not pending, f"sync still running: {list(pending)}"
```

**Output:**

```text
replenishment_recommendations    COMPLETED
stockout_risk_scores             COMPLETED
intelligence_reports             COMPLETED
```

```python
# Verify Delta vs Lakebase Postgres row counts (the Lakebase side is read through the UC-registered catalog)
rows = []
for target, source in SYNCED.items():
    delta_n = spark.sql(f"SELECT count(*) FROM {S}.{source}").first()[0]
    pg_n = spark.sql(f"SELECT count(*) FROM {LB}.serving.{target}").first()[0]
    rows.append((f"{S}.{source}", f"{LB}.serving.{target}", delta_n, pg_n, delta_n == pg_n))
display(spark.createDataFrame(rows, "delta_source string, lakebase_table string, delta_rows long, postgres_rows long, in_sync boolean"))
```

**Output:**

| delta_source | lakebase_table | delta_rows | postgres_rows | in_sync |
|---|---|---|---|---|
| serverless_stable_4hkk7k_catalog.osa_retail.gold_replenishment_recommendations | osa_lakebase.serving.replenishment_recommendations | 1168 | 1168 | True |
| serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_risk_scores | osa_lakebase.serving.stockout_risk_scores | 21980 | 21980 | True |
| serverless_stable_4hkk7k_catalog.osa_retail.gold_intelligence_reports | osa_lakebase.serving.intelligence_reports | 12 | 12 | True |
