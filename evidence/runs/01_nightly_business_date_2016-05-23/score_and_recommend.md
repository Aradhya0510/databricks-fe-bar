# Task `score_and_recommend` — SUCCESS

*Run 255951456155763 · started 2026-10-30 23:58:27 UTC · 404s*

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
2026/10/30 23:59:12 WARNING mlflow.models.utils: Found extra inputs in the model input that are not defined in the model signature: `['lost_revenue_next3', 'is_oos_today', 'state_id', 'supplier_id', 'suspected_phantom', 'units', 'date', 'label_oos_next3', 'region', 'supplier_name', 'case_pack', 'item_id', 'item_name']`. These inputs will be ignored.
```

```text
score_date=2016-05-23  active store-items scored=21,971
```

| risk_tier | store_items | revenue_at_risk_3d |
|---|---|---|
| OK | 20184 | 6718.38 |
| CRITICAL | 527 | 6627.53 |
| OOS_NOW | 561 | 6617.43 |
| OOS_PHANTOM | 136 | 1909.04 |
| WATCH | 442 | 1173.02 |
| HIGH | 121 | 496.32 |

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
wrote 21,971 scores
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
| 1 | TX_2 | Great Value Tortilla Chips #120 | OOS_PHANTOM | 0.238 | CYCLE_COUNT | 24 | 247.84 | System shows 231 units on hand with 13.92 days of cover, but zero recent sales suggest phantom inventory—conduct CYCLE_COUNT immediately and reorder 24 units if shelf is empty. |
| 2 | CA_3 | Equate Cheddar Block #170 | CRITICAL | 0.92 | EXPEDITED_ORDER | 4 | 163.05 | Equate Cheddar Block #170 faces 92% stockout probability with only 1.53 days cover at 10.5 units/day demand; place EXPEDITED_ORDER for 4 units immediately. |
| 3 | WI_2 | Hearth & Home Cereal #029 | CRITICAL | 0.971 | EMERGENCY_DSD | 36 | 150.59 | CRITICAL: Hearth & Home Cereal #029 has 0 units on hand with 97% stockout probability; execute EMERGENCY_DSD of 36 units immediately due to 1-day overdue supplier PO. |
| 4 | WI_2 | Parent's Choice Peanut Butter #316 | OOS_NOW | 0.496 | EMERGENCY_DSD | 8 | 131.08 | Parent's Choice Peanut Butter #316 is out of stock with 50% stockout probability; execute EMERGENCY_DSD of 8 units due to 1 overdue PO (4 days late). |
| 5 | TX_3 | Great Value Pasta #368 | OOS_NOW | 0.629 | EMERGENCY_DSD | 24 | 109.39 | Great Value Pasta #368 is out of stock with 63% stockout probability and 1 overdue PO; execute EMERGENCY_DSD of 24 units immediately. |
| 6 | CA_3 | Northpeak Soup #183 | CRITICAL | 0.967 | VERIFY_SHELF_AND_EXPEDITE_PO | 4 | 97.3 | Northpeak Soup #183 has 97% stockout probability despite 20 units on-hand due to 1 overdue PO; verify shelf accuracy and expedite the 4-unit purchase order. |
| 7 | CA_1 | Equate Cola 12pk #682 | CRITICAL | 0.961 | EMERGENCY_DSD | 48 | 87.09 | Store CA_1 has 0 units of Equate Cola 12pk #682 with 96% stockout probability; execute EMERGENCY_DSD of 48 units immediately despite 102 on order being overdue. |
| 8 | WI_1 | Equate Black Beans #282 | CRITICAL | 0.999 | EMERGENCY_DSD | 16 | 78.55 | Equate Black Beans #282 has 0 units on hand with 100% stockout probability and 1 overdue PO; execute EMERGENCY_DSD of 16 units immediately. |
| 9 | CA_3 | Marketside Trash Bags #249 | OOS_NOW | 0.644 | EMERGENCY_DSD | 24 | 75.72 | Marketside Trash Bags #249 is out of stock with 64% stockout probability and 1 overdue PO; execute EMERGENCY_DSD of 24 units from CleanWave Home Products immediately. |
| 10 | CA_3 | Sunny Fields Coffee #574 | OOS_NOW | 0.924 | EMERGENCY_DSD | 20 | 75.55 | Sunny Fields Coffee #574 is out of stock with 92% stockout probability and 1 overdue PO; execute EMERGENCY_DSD of 20 units immediately. |
| 11 | CA_3 | Great Value Dish Soap #488 | CRITICAL | 0.974 | VERIFY_SHELF_AND_EXPEDITE_PO | 24 | 74.54 | Great Value Dish Soap #488 has 97% stockout probability despite 35 units on-hand due to 2-days overdue PO; verify shelf accuracy and expedite 24-unit order from Polaris Paper & Plastics. |
| 12 | CA_1 | Sunny Fields Coffee #574 | OOS_NOW | 0.082 | EMERGENCY_DSD | 16 | 69.77 | Sunny Fields Coffee #574 is out of stock with 1 PO overdue by 10 days; execute EMERGENCY_DSD of 16 units immediately to prevent stockout. |
| 13 | WI_2 | Great Value Dish Soap #488 | CRITICAL | 0.979 | EMERGENCY_DSD | 24 | 69.4 | Great Value Dish Soap #488 is out of stock with 98% stockout probability and 1 overdue PO; execute EMERGENCY_DSD of 24 units immediately. |
| 14 | CA_3 | Parent's Choice Storage Bins #348 | OOS_PHANTOM | 0.113 | CYCLE_COUNT | 24 | 67.21 | Item #348 shows 28 units on hand but has stopped selling despite 3.0 units/day demand; conduct cycle count now and reorder 24 units if shelf is empty. |
| 15 | CA_3 | Parent's Choice Frozen Pizza #476 | OOS_NOW | 0.171 | EMERGENCY_DSD | 6 | 66.18 | Item #476 is out of stock with 0 units on hand and 1 overdue PO (7 days late); execute EMERGENCY_DSD of 6 units from Northstar Snacks & Beverage immediately. |

```python
display(spark.sql(f"""
SELECT risk_tier, recommended_action, count(*) AS items, round(sum(revenue_at_risk_3d), 0) AS revenue_at_risk_3d,
       sum(CASE WHEN rationale_source <> 'template' THEN 1 ELSE 0 END) AS llm_rationales
FROM {S}.gold_replenishment_recommendations GROUP BY ALL ORDER BY revenue_at_risk_3d DESC"""))
```

**Output:**

| risk_tier | recommended_action | items | revenue_at_risk_3d | llm_rationales |
|---|---|---|---|---|
| OOS_NOW | EMERGENCY_DSD | 392 | 5007.0 | 136 |
| CRITICAL | EMERGENCY_DSD | 340 | 4452.0 | 126 |
| OOS_PHANTOM | CYCLE_COUNT | 136 | 1909.0 | 46 |
| OOS_NOW | EXPEDITE_PO_AND_ESCALATE | 127 | 975.0 | 22 |
| CRITICAL | EXPEDITED_ORDER | 61 | 801.0 | 17 |
| CRITICAL | EXPEDITE_PO_AND_ESCALATE | 92 | 736.0 | 14 |
| CRITICAL | VERIFY_SHELF_AND_EXPEDITE_PO | 34 | 638.0 | 17 |
| OOS_NOW | EXPEDITED_ORDER | 42 | 635.0 | 19 |
| HIGH | EXPEDITED_ORDER | 102 | 388.0 | 2 |
| HIGH | VERIFY_SHELF_AND_EXPEDITE_PO | 8 | 62.0 | 1 |
| HIGH | EXPEDITE_PO_AND_ESCALATE | 11 | 46.0 | 0 |
