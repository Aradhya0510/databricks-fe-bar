# Task `score_and_recommend` — SUCCESS

*Run 53427127416947 · started 2026-10-31 00:21:32 UTC · 621s*

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
# GUIDE-DSD-005: emergency DSD only for eligible departments when the shelf is empty or cover < 3 days;
# with cover left and a late PO, expedite/escalate the PO and verify the shelf (system stock may be wrong).
dsd_dept = scored.dept_id.isin(["FOODS_1", "FOODS_2", "FOODS_3", "HOUSEHOLD_1"])
low_cover = scored.is_oos_today | (scored.days_of_cover.fillna(0) < 3)
alerting = scored.risk_tier.isin(["CRITICAL", "HIGH", "OOS_NOW"])
scored["recommended_action"] = np.select(
    [scored.risk_tier == "OOS_PHANTOM",
     scored.risk_tier.isin(["CRITICAL", "OOS_NOW"]) & (scored.overdue_po_count > 0) & dsd_dept & low_cover,
     alerting & (scored.overdue_po_count > 0) & ~low_cover,
     alerting & (scored.overdue_po_count > 0),
     alerting],
    ["CYCLE_COUNT", "EMERGENCY_DSD", "VERIFY_SHELF_AND_EXPEDITE_PO", "EXPEDITE_PO_AND_ESCALATE", "EXPEDITED_ORDER"],
    default="MONITOR")
scored["revenue_at_risk_3d"] = (scored.lambda_90d * 3 * scored.sell_price.fillna(0)
                                * np.where(scored.is_oos_today, 1.0, scored.risk_score)).round(2)
scored["score_date"] = score_date
scored["model_version"] = int(champ.version)
display(scored.groupby("risk_tier").agg(store_items=("item_id", "size"), revenue_at_risk_3d=("revenue_at_risk_3d", "sum"))
        .reset_index().sort_values("revenue_at_risk_3d", ascending=False))
```

**Output:**

```text
2026/10/31 00:22:25 WARNING mlflow.models.utils: Found extra inputs in the model input that are not defined in the model signature: `['lost_revenue_next3', 'is_oos_today', 'state_id', 'supplier_id', 'suspected_phantom', 'units', 'date', 'label_oos_next3', 'region', 'supplier_name', 'case_pack', 'item_id', 'item_name']`. These inputs will be ignored.
```

```text
score_date=2016-05-24  active store-items scored=21,980
```

| risk_tier | store_items | revenue_at_risk_3d |
|---|---|---|
| OOS_NOW | 586 | 7421.78 |
| OK | 20366 | 6277.71 |
| CRITICAL | 319 | 4105.32 |
| OOS_PHANTOM | 151 | 1825.6 |
| WATCH | 446 | 1101.9 |
| HIGH | 112 | 547.79 |

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
wrote 21,980 scores
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
 'Recommended action: ', CASE WHEN recommended_action = 'CYCLE_COUNT'
     THEN concat('CYCLE_COUNT now (system shows stock but the item stopped selling); if the shelf is empty, reorder ', {f('recommended_qty')}, ' units')
     ELSE concat(recommended_action, ' of ', {f('recommended_qty')}, ' units') END, '.')"""
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
| 1 | TX_2 | Great Value Tortilla Chips #120 | OOS_NOW | 0.334 | EXPEDITED_ORDER | 24 | 237.05 | Great Value Tortilla Chips #120 is out of stock with 0 units on hand despite 217 on order; place EXPEDITED_ORDER of 24 units to cover 15.9 units/day demand. |
| 2 | CA_3 | Equate Cheddar Block #170 | CRITICAL | 0.988 | EMERGENCY_DSD | 4 | 174.59 | Equate Cheddar Block #170 has 0 units on hand with 99% stockout probability and 10.4 units/day demand—execute EMERGENCY_DSD of 4 units immediately. |
| 3 | WI_2 | Hearth & Home Cereal #029 | CRITICAL | 0.961 | EMERGENCY_DSD | 36 | 149.98 | Hearth & Home Cereal #029 has 0 units on hand with 96% stockout probability; execute EMERGENCY_DSD of 36 units immediately due to 2-day overdue supplier PO. |
| 4 | WI_2 | Parent's Choice Peanut Butter #316 | OOS_NOW | 0.288 | EMERGENCY_DSD | 8 | 131.08 | Parent's Choice Peanut Butter #316 is out of stock with 1 overdue PO (5 days late); execute EMERGENCY_DSD of 8 units immediately. |
| 5 | TX_3 | Great Value Pasta #368 | OOS_NOW | 0.185 | EMERGENCY_DSD | 24 | 109.39 | Great Value Pasta #368 is out of stock with 0 units on hand and 1 overdue PO; execute EMERGENCY_DSD of 24 units immediately. |
| 6 | TX_1 | Marketside Surface Cleaner #497 | OOS_NOW | 0.677 | EXPEDITED_ORDER | 8 | 108.71 | Marketside Surface Cleaner #497 is out of stock with 68% stockout risk despite 27 units on order; place expedited order for 8 units from Polaris Paper & Plastics immediately. |
| 7 | CA_3 | Northpeak Soup #183 | CRITICAL | 0.991 | EMERGENCY_DSD | 16 | 99.91 | Northpeak Soup #183 has 0 units on hand with 99% stockout probability; execute EMERGENCY_DSD of 16 units immediately due to 1 overdue PO and 3.7 units/day demand. |
| 8 | CA_1 | Equate Cola 12pk #682 | CRITICAL | 0.994 | EMERGENCY_DSD | 48 | 89.1 | Item #682 has 0 units on hand with 99% stockout probability and 8.4 units/day demand; execute EMERGENCY_DSD of 48 units immediately due to 1-day overdue PO. |
| 9 | WI_1 | Equate Black Beans #282 | OOS_NOW | 0.987 | EMERGENCY_DSD | 16 | 78.62 | Equate Black Beans #282 is out of stock with 99% stockout probability; expedite the 3-days-overdue PO or arrange EMERGENCY_DSD of 16 units immediately. |
| 10 | CA_3 | Great Value Dish Soap #488 | CRITICAL | 0.981 | EMERGENCY_DSD | 24 | 75.37 | Great Value Dish Soap #488 has 0 units on hand with 98% stockout probability and overdue supplier delivery; execute EMERGENCY_DSD of 24 units immediately. |
| 11 | WI_2 | Mainstays Rice #251 | OOS_NOW | 0.363 | EXPEDITED_ORDER | 16 | 72.67 | Mainstays Rice #251 is out of stock with 0 units on hand and 36% stockout risk, requiring an EXPEDITED_ORDER of 16 units immediately. |
| 12 | WI_2 | Great Value Dish Soap #488 | OOS_NOW | 0.959 | EMERGENCY_DSD | 24 | 70.54 | Great Value Dish Soap #488 is out of stock with 96% stockout probability; execute EMERGENCY_DSD of 24 units immediately due to 2-days-overdue supplier PO. |
| 13 | CA_1 | Sunny Fields Coffee #574 | OOS_NOW | 0.056 | EMERGENCY_DSD | 12 | 68.57 | Sunny Fields Coffee #574 is out of stock with 1 PO overdue 11 days from Prime Valley Distribution; execute EMERGENCY_DSD of 12 units immediately. |
| 14 | CA_3 | Parent's Choice Storage Bins #348 | OOS_NOW | 0.233 | EXPEDITE_PO_AND_ESCALATE | 24 | 67.21 | Storage Bins #348 is out of stock with 0 units on hand; expedite the 1-day overdue PO for 24 units from Hearthstone Home Goods immediately. |
| 15 | CA_3 | Parent's Choice Frozen Pizza #476 | OOS_NOW | 0.136 | EMERGENCY_DSD | 6 | 66.18 | Item #476 is out of stock with 0 units on hand and 1 PO overdue by 8 days; execute EMERGENCY_DSD of 6 units from Northstar Snacks & Beverage immediately. |

```python
display(spark.sql(f"""
SELECT risk_tier, recommended_action, count(*) AS items, round(sum(revenue_at_risk_3d), 0) AS revenue_at_risk_3d,
       sum(CASE WHEN rationale_source <> 'template' THEN 1 ELSE 0 END) AS llm_rationales
FROM {S}.gold_replenishment_recommendations GROUP BY ALL ORDER BY revenue_at_risk_3d DESC"""))
```

**Output:**

| risk_tier | recommended_action | items | revenue_at_risk_3d | llm_rationales |
|---|---|---|---|---|
| OOS_NOW | EMERGENCY_DSD | 406 | 5381.0 | 167 |
| CRITICAL | EMERGENCY_DSD | 224 | 3427.0 | 110 |
| OOS_PHANTOM | CYCLE_COUNT | 151 | 1826.0 | 52 |
| OOS_NOW | EXPEDITE_PO_AND_ESCALATE | 129 | 1132.0 | 30 |
| OOS_NOW | EXPEDITED_ORDER | 51 | 908.0 | 19 |
| HIGH | EXPEDITED_ORDER | 90 | 421.0 | 5 |
| CRITICAL | EXPEDITE_PO_AND_ESCALATE | 58 | 415.0 | 7 |
| CRITICAL | EXPEDITED_ORDER | 31 | 187.0 | 4 |
| CRITICAL | VERIFY_SHELF_AND_EXPEDITE_PO | 6 | 76.0 | 3 |
| HIGH | EXPEDITE_PO_AND_ESCALATE | 13 | 72.0 | 2 |
| HIGH | VERIFY_SHELF_AND_EXPEDITE_PO | 9 | 54.0 | 1 |
