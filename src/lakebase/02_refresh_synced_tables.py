# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase 2/2 · Refresh the operational serving tables
# MAGIC
# MAGIC Gold Delta tables are served to the app from **Lakebase Postgres** via *synced tables* (managed by Lakeflow):
# MAGIC
# MAGIC | Lakebase table (`osa_lakebase.serving.*`) | Source (Delta) | Used by |
# MAGIC |---|---|---|
# MAGIC | `replenishment_recommendations` | `gold_replenishment_recommendations` | store action queue (sub-second lookups) |
# MAGIC | `stockout_risk_scores` | `gold_stockout_risk_scores` | item search / typeahead |
# MAGIC | `intelligence_reports` | `gold_intelligence_reports` | nightly briefings page |
# MAGIC
# MAGIC Synced tables are created once by `scripts/setup_lakebase.sh`; this task triggers their refresh after the nightly
# MAGIC scoring + agent run and verifies Postgres row counts against Delta.

# COMMAND ----------

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

# COMMAND ----------

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

# COMMAND ----------

# Verify Delta vs Lakebase Postgres row counts (the Lakebase side is read through the UC-registered catalog)
rows = []
for target, source in SYNCED.items():
    delta_n = spark.sql(f"SELECT count(*) FROM {S}.{source}").first()[0]
    pg_n = spark.sql(f"SELECT count(*) FROM {LB}.serving.{target}").first()[0]
    rows.append((f"{S}.{source}", f"{LB}.serving.{target}", delta_n, pg_n, delta_n == pg_n))
display(spark.createDataFrame(rows, "delta_source string, lakebase_table string, delta_rows long, postgres_rows long, in_sync boolean"))
