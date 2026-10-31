# Task `ingest_app_actions` — SUCCESS

*Run 511927266746019 · started 2026-10-31 00:20:30 UTC · 28s*

# Lakebase 1/2 · Close the loop: store decisions → lakehouse

Store managers approve / override / reject recommendations in the **OSA Command Center** app. The app writes those
decisions transactionally into Lakebase Postgres (`osa_app.replenishment_actions`). The Lakebase database is
registered in Unity Catalog as catalog **`osa_lakebase`**, so this job reads the operational table with plain SQL
and MERGEs it into the governed Delta table `replenishment_actions` — where it feeds the KPIs (alert response
rate), the agents, and tomorrow's scoring (approved quantities count as on-order).

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("lakebase_catalog", "osa_lakebase")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
LB = dbutils.widgets.get("lakebase_catalog")
S = f"{catalog}.{schema}"

spark.sql(f"""CREATE TABLE IF NOT EXISTS {S}.replenishment_actions (
  action_id STRING NOT NULL, rec_id STRING, store_id STRING, item_id STRING, action STRING, final_qty INT,
  reason_code STRING, note STRING, decided_by STRING, decided_at TIMESTAMP, recommended_qty INT, risk_tier STRING,
  ingested_at TIMESTAMP, CONSTRAINT replenishment_actions_pk PRIMARY KEY (action_id))
  COMMENT 'Store-manager decisions on OSA recommendations, written by the app to Lakebase and merged here nightly.'""")

src = f"{LB}.osa_app.replenishment_actions"
try:
    n_src = spark.sql(f"SELECT count(*) FROM {src}").first()[0]
except Exception as e:
    n_src = None
    print(f"{src} not readable yet ({str(e).splitlines()[0][:160]}) - the app creates it on first start")

if n_src is not None:
    print(f"rows in Lakebase {src}: {n_src}")
    spark.sql(f"""
    MERGE INTO {S}.replenishment_actions t
    USING (SELECT CAST(action_id AS STRING) AS action_id, rec_id, store_id, item_id, action, CAST(final_qty AS INT) AS final_qty,
                  reason_code, note, decided_by, CAST(decided_at AS TIMESTAMP) AS decided_at,
                  CAST(recommended_qty AS INT) AS recommended_qty, risk_tier, current_timestamp() AS ingested_at
           FROM {src}) s
    ON t.action_id = s.action_id
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *""")

display(spark.sql(f"""
SELECT action, risk_tier, count(*) AS decisions, sum(final_qty) AS units, min(decided_at) AS first, max(decided_at) AS last
FROM {S}.replenishment_actions GROUP BY ALL ORDER BY decisions DESC"""))
```

**Output:**

```text
rows in Lakebase osa_lakebase.osa_app.replenishment_actions: 3
```

| action | risk_tier | decisions | units | first | last |
|---|---|---|---|---|---|
| APPROVE | CRITICAL | 1 | 4 | 2026-10-31T00:14:26.779Z | 2026-10-31T00:14:26.779Z |
| OVERRIDE | CRITICAL | 1 | 73 | 2026-10-31T00:14:27.113Z | 2026-10-31T00:14:27.113Z |
| REJECT | CRITICAL | 1 | 0 | 2026-10-31T00:14:27.766Z | 2026-10-31T00:14:27.766Z |

```python
# Alert response KPI: share of critical recommendations that received a decision
display(spark.sql(f"""
SELECT r.score_date, count(*) AS critical_alerts, count(a.action_id) AS actioned,
       round(100 * count(a.action_id) / count(*), 1) AS response_rate_pct
FROM {S}.gold_replenishment_recommendations r
LEFT JOIN {S}.replenishment_actions a ON a.rec_id = r.rec_id
WHERE r.risk_tier = 'CRITICAL' GROUP BY r.score_date"""))
```

**Output:**

| score_date | critical_alerts | actioned | response_rate_pct |
|---|---|---|---|
| 2016-05-23 | 527 | 3 | 0.6 |
