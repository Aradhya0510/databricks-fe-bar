# Task `score_and_recommend` — SUCCESS

*Run 135029669284307 · started 2026-10-30 23:32:27 UTC · 405s*

# ML 2/2 · Score tonight's risk, size the order, and explain it with GenAI

1. Load `osa_stockout_risk@champion` from Unity Catalog and score every active store-item on the latest date.
2. Tier alerts per SOP-REP-001 (Critical ≥ 0.60, High ≥ 0.35, Watch ≥ 0.15) and flag suspected phantom inventory.
3. Size the recommended order per SOP-REP-001: `λ × (7 + lead time + safety days) − (on-hand + on-order)`,
   rounded up to case pack; phantom-inventory items get a **cycle count** action instead of an order.
4. `ai_query()` writes a one-sentence rationale grounded strictly in the row's facts.
5. Write `gold_stockout_risk_scores` (all items), `gold_replenishment_recommendations` (action queue, synced to
   Lakebase) and append to `gold_stockout_risk_scores_history` (for back-testing against real outcomes).

```python
%pip install -q lightgbm==4.6.0 "mlflow>=3.1"
%restart_python
```

**Output:**

```text
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("llm_fast_endpoint", "databricks-claude-sonnet-4-5")
dbutils.widgets.text("max_llm_rows", "400")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
LLM = dbutils.widgets.get("llm_fast_endpoint")
MAX_LLM = int(dbutils.widgets.get("max_llm_rows"))
S = f"{catalog}.{schema}"

import mlflow, pandas as pd, numpy as np
from pyspark.sql import functions as F
mlflow.set_registry_uri("databricks-uc")
model_uri = f"models:/{S}.osa_stockout_risk@champion"
champ = mlflow.MlflowClient().get_model_version_by_alias(f"{S}.osa_stockout_risk", "champion")
model = mlflow.pyfunc.load_model(model_uri)
print(f"scoring with {model_uri} (version {champ.version})")
```

**Output:**

```text
Downloading artifacts:   0%|          | 0/13 [00:00<?, ?it/s]
```

```text
scoring with models:/serverless_stable_4hkk7k_catalog.osa_retail.osa_stockout_risk@champion (version 2)
```

```python
feat = spark.table(f"{S}.gold_stockout_features")
score_date = feat.agg(F.max("date")).first()[0]
rows = (feat.where(F.col("date") == score_date).where("lambda_90d >= 0.3 AND days_since_last_sale <= 28")
        .join(spark.table(f"{S}.dim_item").select("item_id", "item_name", "case_pack"), "item_id", "left")
        .join(spark.table(f"{S}.dim_supplier").select("supplier_id", "supplier_name"), "supplier_id", "left")
        .toPandas())
pred = model.predict(rows)
scored = pd.concat([rows.reset_index(drop=True), pred.reset_index(drop=True)], axis=1)
print(f"score_date={score_date}  active store-items scored={len(scored):,}")

def tier(r):
    if r.is_oos_today:
        return "OOS_PHANTOM" if r.suspected_phantom else "OOS_NOW"
    return "CRITICAL" if r.risk_score >= 0.60 else "HIGH" if r.risk_score >= 0.35 else "WATCH" if r.risk_score >= 0.15 else "OK"

scored["risk_tier"] = scored.apply(tier, axis=1)
safety = scored.reliability_tier.map({"A": 3, "B": 4, "C": 5}).fillna(4)
target = scored.lambda_90d * (7 + scored.contract_lead_time_days.fillna(4) + safety)
need = np.maximum(0, target - scored.on_hand_units.fillna(0) - scored.on_order_units.fillna(0))
cp = scored.case_pack.fillna(1).clip(lower=1)
scored["recommended_qty"] = (np.ceil(need / cp) * cp).astype(int)
scored.loc[(scored.recommended_qty == 0) & scored.risk_tier.isin(["CRITICAL", "HIGH", "OOS_NOW"]), "recommended_qty"] = cp
scored["recommended_action"] = np.select(
    [scored.risk_tier == "OOS_PHANTOM",
     scored.risk_tier.isin(["CRITICAL", "OOS_NOW"]) & (scored.overdue_po_count > 0) & scored.dept_id.isin(["FOODS_1", "FOODS_2", "FOODS_3", "HOUSEHOLD_1"]),
     scored.risk_tier.isin(["CRITICAL", "HIGH", "OOS_NOW"]) & (scored.overdue_po_count > 0),
     scored.risk_tier.isin(["CRITICAL", "HIGH", "OOS_NOW"])],
    ["CYCLE_COUNT", "EMERGENCY_DSD", "EXPEDITE_PO_AND_ESCALATE", "EXPEDITED_ORDER"], default="MONITOR")
scored["revenue_at_risk_3d"] = (scored.lambda_90d * 3 * scored.sell_price.fillna(0)
                                * np.where(scored.is_oos_today, 1.0, scored.risk_score)).round(2)
scored["score_date"] = score_date
scored["model_version"] = int(champ.version)
display(scored.groupby("risk_tier").agg(store_items=("item_id", "size"), revenue_at_risk_3d=("revenue_at_risk_3d", "sum"))
        .reset_index().sort_values("revenue_at_risk_3d", ascending=False))
```

**Output:**

```text
2026/10/30 23:33:11 WARNING mlflow.models.utils: Found extra inputs in the model input that are not defined in the model signature: `['lost_revenue_next3', 'is_oos_today', 'state_id', 'supplier_id', 'suspected_phantom', 'units', 'date', 'label_oos_next3', 'region', 'supplier_name', 'case_pack', 'item_id', 'item_name']`. These inputs will be ignored.
```

```text
score_date=2016-05-22  active store-items scored=21,907
```

| risk_tier | store_items | revenue_at_risk_3d |
|---|---|---|
| CRITICAL | 683 | 8020.06 |
| OOS_NOW | 513 | 6260.67 |
| OK | 20003 | 6140.28 |
| OOS_PHANTOM | 111 | 1499.2 |
| WATCH | 469 | 1139.17 |
| HIGH | 128 | 709.66 |

```python
score_cols = ["score_date", "store_id", "state_id", "region", "item_id", "item_name", "dept_id", "cat_id", "supplier_id",
              "supplier_name", "risk_score", "risk_tier", "driver_1", "driver_1_impact", "driver_2", "driver_2_impact",
              "driver_3", "driver_3_impact", "lambda_90d", "on_hand_units", "on_order_units", "days_of_cover",
              "overdue_po_count", "max_days_overdue", "days_to_next_receipt", "sell_price", "revenue_at_risk_3d",
              "is_oos_today", "suspected_phantom", "model_version"]
sdf = spark.createDataFrame(scored[score_cols])
sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{S}.gold_stockout_risk_scores")
spark.sql(f"CREATE TABLE IF NOT EXISTS {S}.gold_stockout_risk_scores_history LIKE {S}.gold_stockout_risk_scores")
spark.sql(f"DELETE FROM {S}.gold_stockout_risk_scores_history WHERE score_date = DATE'{score_date}'")
sdf.write.mode("append").saveAsTable(f"{S}.gold_stockout_risk_scores_history")
print(f"wrote {sdf.count():,} scores")
```

**Output:**

```text
wrote 21,907 scores
```

## Action queue + GenAI rationale (`ai_query`)

```python
queue = scored[scored.risk_tier.isin(["CRITICAL", "HIGH", "OOS_NOW", "OOS_PHANTOM"])].copy()
queue["rec_id"] = queue.store_id + "|" + queue.item_id + "|" + str(score_date)
queue = queue.sort_values("revenue_at_risk_3d", ascending=False).reset_index(drop=True)
queue["priority_rank"] = np.arange(1, len(queue) + 1)
pretty = {"days_of_cover": "low days of cover", "position_cover_days": "low on-hand + on-order cover",
          "max_days_overdue": "an overdue supplier PO", "overdue_po_count": "an overdue supplier PO",
          "days_to_next_receipt": "next receipt is far out", "on_hand_units": "low on-hand units",
          "days_since_last_sale": "an unusual zero-sales streak", "lambda_90d": "high demand rate",
          "avg_units_7d": "recent demand uplift", "trend_7_28": "accelerating demand", "sup_on_time_56d": "weak supplier on-time record",
          "event_next3": "an upcoming calendar event", "snap_next3": "upcoming SNAP benefit days",
          "price_change_7d": "a recent price change", "on_order_units": "little stock on order"}
queue["drivers_text"] = queue.apply(lambda r: "; ".join(dict.fromkeys(
    pretty.get(r[f"driver_{i}"], r[f"driver_{i}"]) for i in (1, 2, 3))), axis=1)
rec_cols = ["rec_id", "priority_rank", "score_date", "store_id", "region", "item_id", "item_name", "dept_id",
            "supplier_id", "supplier_name", "risk_tier", "risk_score", "recommended_action", "recommended_qty",
            "on_hand_units", "on_order_units", "days_of_cover", "lambda_90d", "overdue_po_count", "max_days_overdue",
            "days_to_next_receipt", "sell_price", "revenue_at_risk_3d", "drivers_text", "model_version"]
spark.createDataFrame(queue[rec_cols]).createOrReplaceTempView("queue")

def f(expr):
    return f"coalesce(cast({expr} AS STRING), 'n/a')"
prompt = f"""concat(
 'You are a retail replenishment analyst. Write ONE sentence (max 30 words) telling a store manager why this ',
 'item needs action and what to do. Use only these facts, quote numbers exactly, no preamble.\\n',
 'Item: ', {f('item_name')}, ' (', item_id, '), store ', store_id, '.\\n',
 'Alert tier: ', risk_tier, '; stockout probability next 3 days: ', {f('format_number(risk_score * 100, 0)')}, '%.\\n',
 'On hand: ', {f('on_hand_units')}, ' units; on order: ', {f('on_order_units')}, '; days of cover: ', {f('days_of_cover')}, '.\\n',
 'Typical demand: ', {f('format_number(lambda_90d, 1)')}, ' units/day.\\n',
 'Overdue POs: ', {f('overdue_po_count')}, coalesce(concat(' (max ', cast(nullif(max_days_overdue, -1) AS STRING), ' days overdue)'), ''), '.\\n',
 'Supplier: ', {f('supplier_name')}, '.\\n',
 'Model drivers: ', {f('drivers_text')}, '.\\n',
 'Recommended action: ', recommended_action, ' of ', {f('recommended_qty')}, ' units.')"""
# Only the top-N rows are sent to the LLM (materialised first so ai_query never sees the long tail);
# the remainder get a deterministic template rationale.
spark.sql(f"""
WITH llm AS (
  SELECT q.*, ai_query('{LLM}', {prompt}, modelParameters => named_struct('max_tokens', 200), failOnError => false) AS r
  FROM queue q WHERE priority_rank <= {MAX_LLM})
SELECT * EXCEPT (r),
       coalesce(nullif(trim(r.result), ''),
                concat(risk_tier, ': ', drivers_text, '. ', replace(recommended_action, '_', ' '), ' ', recommended_qty, ' units.')) AS rationale,
       CASE WHEN nullif(trim(r.result), '') IS NOT NULL THEN '{LLM}' ELSE concat('template (llm error: ', coalesce(r.errorMessage, 'empty'), ')') END
         AS rationale_source
FROM llm""").write.mode("overwrite").saveAsTable(f"{S}._queue_llm_scratch")
display(spark.sql(f"SELECT rationale_source, count(*) AS n FROM {S}._queue_llm_scratch GROUP BY 1"))
spark.sql(f"""
CREATE OR REPLACE TEMP VIEW queue_explained AS
SELECT *, current_timestamp() AS generated_at FROM {S}._queue_llm_scratch
UNION ALL
SELECT q.*, concat(risk_tier, ': ', drivers_text, '. ', replace(recommended_action, '_', ' '), ' ', recommended_qty, ' units.'),
       'template', current_timestamp()
FROM queue q WHERE priority_rank > {MAX_LLM}""")
recs = spark.table("queue_explained")
(recs.write.mode("overwrite").option("overwriteSchema", "true")
     .option("delta.enableChangeDataFeed", "true").saveAsTable(f"{S}.gold_replenishment_recommendations"))
spark.sql(f"ALTER TABLE {S}.gold_replenishment_recommendations SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
spark.sql(f"DROP TABLE IF EXISTS {S}._queue_llm_scratch")
spark.sql(f"COMMENT ON TABLE {S}.gold_replenishment_recommendations IS "
          f"'Nightly OSA action queue: one row per at-risk store-item with recommended action/qty and GenAI rationale. Synced to Lakebase.'")
```

**Output:**

| rationale_source | n |
|---|---|
| databricks-claude-sonnet-4-5 | 400 |

```python
display(spark.sql(f"""
SELECT priority_rank, store_id, item_name, risk_tier, round(risk_score, 3) AS risk, recommended_action, recommended_qty,
       revenue_at_risk_3d, rationale
FROM {S}.gold_replenishment_recommendations ORDER BY priority_rank LIMIT 15"""))
```

**Output:**

| priority_rank | store_id | item_name | risk_tier | risk | recommended_action | recommended_qty | revenue_at_risk_3d | rationale |
|---|---|---|---|---|---|---|---|---|
| 1 | CA_3 | Equate Cheddar Block #170 | CRITICAL | 0.885 | EXPEDITED_ORDER | 4 | 156.15 | Equate Cheddar Block #170 faces 88% stockout probability with only 1.73 days cover at 10.4 units/day demand; place EXPEDITED_ORDER for 4 units immediately. |
| 2 | WI_2 | Hearth & Home Cereal #029 | CRITICAL | 0.969 | EMERGENCY_DSD | 36 | 149.25 | Hearth & Home Cereal #029 has 0 units on hand with 97% stockout probability; execute EMERGENCY_DSD of 36 units immediately due to overdue supplier PO. |
| 3 | WI_2 | Parent's Choice Peanut Butter #316 | OOS_NOW | 0.773 | EMERGENCY_DSD | 8 | 131.74 | Parent's Choice Peanut Butter #316 is out of stock with 77% stockout probability; execute EMERGENCY_DSD of 8 units while 51-unit order is 3 days overdue. |
| 4 | TX_3 | Great Value Pasta #368 | OOS_NOW | 0.898 | EMERGENCY_DSD | 24 | 111.23 | Great Value Pasta #368 is out of stock with 90% stockout probability and needs EMERGENCY_DSD of 24 units due to 1 overdue PO (2 days late). |
| 5 | CA_3 | Northpeak Soup #183 | CRITICAL | 0.877 | EXPEDITED_ORDER | 4 | 89.24 | Northpeak Soup #183 faces 88% stockout probability despite 24 units on-hand due to 3.8 units/day demand; place EXPEDITED_ORDER for 4 units immediately. |
| 6 | CA_1 | Equate Cola 12pk #682 | CRITICAL | 0.928 | EXPEDITED_ORDER | 48 | 84.83 | Equate Cola 12pk #682 has 0 units on hand with 93% stockout probability and 8.6 units/day demand—place EXPEDITED_ORDER for 48 units immediately. |
| 7 | WI_1 | Parent's Choice Large Eggs #012 | OOS_NOW | 0.963 | EMERGENCY_DSD | 6 | 82.88 | Out of stock with 96% stockout probability and 1 overdue PO from Golden Prairie Dairy; execute EMERGENCY_DSD of 6 units immediately. |
| 8 | CA_3 | Marketside Trash Bags #489 | OOS_NOW | 0.102 | EXPEDITED_ORDER | 12 | 79.44 | Marketside Trash Bags #489 is out of stock with 0 units on hand and 0.0 days of cover; place an EXPEDITED_ORDER of 12 units immediately. |
| 9 | WI_1 | Equate Black Beans #282 | CRITICAL | 0.997 | EMERGENCY_DSD | 8 | 77.92 | Equate Black Beans #282 has 100% stockout probability despite 48 units on-hand due to 1 overdue PO; execute EMERGENCY_DSD of 8 units immediately. |
| 10 | CA_3 | Sunny Fields Coffee #574 | OOS_NOW | 0.975 | EMERGENCY_DSD | 24 | 76.14 | Sunny Fields Coffee #574 is out of stock with 97% stockout probability; expedite the 3-days-overdue PO from Prime Valley Distribution and execute EMERGENCY_DSD of 24 units immediately. |
| 11 | TX_3 | Mainstays Butter #107 | OOS_NOW | 0.933 | EMERGENCY_DSD | 24 | 72.5 | Mainstays Butter #107 is out of stock with 93% stockout probability; execute EMERGENCY_DSD of 24 units immediately as supplier PO is 2 days overdue. |
| 12 | CA_3 | Great Value Dish Soap #488 | CRITICAL | 0.972 | EMERGENCY_DSD | 24 | 72.44 | Despite 36 units on hand, overdue supplier PO and 97% stockout probability require EMERGENCY_DSD of 24 units from Polaris Paper & Plastics immediately. |
| 13 | CA_3 | Marketside Trash Bags #249 | CRITICAL | 0.94 | EMERGENCY_DSD | 24 | 72.16 | Marketside Trash Bags #249 has 0 units on hand with 94% stockout probability; execute EMERGENCY_DSD of 24 units due to 3-days-overdue supplier PO. |
| 14 | CA_1 | Parent's Choice Frozen Pizza #476 | OOS_NOW | 0.78 | EMERGENCY_DSD | 6 | 71.37 | Parent's Choice Frozen Pizza #476 is out of stock with 78% stockout probability and 1 overdue PO; execute EMERGENCY_DSD of 6 units from Northstar Snacks & Beverage immediately. |
| 15 | CA_1 | Sunny Fields Coffee #574 | OOS_NOW | 0.09 | EMERGENCY_DSD | 16 | 69.77 | Sunny Fields Coffee #574 is out of stock with 1 PO 9 days overdue from Prime Valley Distribution; execute EMERGENCY_DSD of 16 units immediately. |

```python
display(spark.sql(f"""
SELECT risk_tier, recommended_action, count(*) AS items, round(sum(revenue_at_risk_3d), 0) AS revenue_at_risk_3d,
       sum(CASE WHEN rationale_source <> 'template' THEN 1 ELSE 0 END) AS llm_rationales
FROM {S}.gold_replenishment_recommendations GROUP BY ALL ORDER BY revenue_at_risk_3d DESC"""))
```

**Output:**

| risk_tier | recommended_action | items | revenue_at_risk_3d | llm_rationales |
|---|---|---|---|---|
| CRITICAL | EMERGENCY_DSD | 446 | 5631.0 | 146 |
| OOS_NOW | EMERGENCY_DSD | 369 | 4853.0 | 122 |
| OOS_PHANTOM | CYCLE_COUNT | 111 | 1499.0 | 37 |
| CRITICAL | EXPEDITED_ORDER | 96 | 1381.0 | 33 |
| CRITICAL | EXPEDITE_PO_AND_ESCALATE | 141 | 1008.0 | 20 |
| OOS_NOW | EXPEDITE_PO_AND_ESCALATE | 104 | 881.0 | 19 |
| HIGH | EXPEDITED_ORDER | 91 | 543.0 | 8 |
| OOS_NOW | EXPEDITED_ORDER | 40 | 527.0 | 15 |
| HIGH | EXPEDITE_PO_AND_ESCALATE | 37 | 167.0 | 0 |
