# Task `agent_tools` — SUCCESS

*Run 509206956646706 · started 2026-10-31 00:05:14 UTC · 21s*

# Agents 1/2 · Governed tools (Unity Catalog functions)

The Q&A Supervisor Agent and the nightly report agent call these **UC SQL table functions** as tools.
Because they are UC securables, every call is permission-checked, audited and visible in lineage — the agents
never get raw table access beyond what the functions expose.

| Function | Purpose |
|---|---|
| `osa_item_risk(store_id, item_search)` | latest risk score, drivers, cover, open/overdue POs for matching items |
| `osa_store_action_queue(store_id, top_n)` | tonight's prioritised action queue for a store |
| `osa_open_purchase_orders(store_id, item_id)` | open POs and how overdue they are |
| `osa_kpi_summary(region)` | OSA %, lost revenue, revenue: last 7 days vs prior 7 days (region or `ALL`) |
| `osa_supplier_watchlist(region)` | suppliers ranked by attributed stockouts / lost revenue in the last 28 days |

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
S = f"{catalog}.{schema}"
```

```python
spark.sql(f"""
CREATE OR REPLACE FUNCTION {S}.osa_item_risk(
  store_id STRING COMMENT 'Store id, e.g. TX_2. Use ALL for every store.',
  item_search STRING COMMENT 'Item id (FOODS_3_090) or part of the item name (e.g. cola, milk)')
RETURNS TABLE (score_date DATE, store_id STRING, item_id STRING, item_name STRING, dept_id STRING,
               supplier_name STRING, risk_tier STRING, risk_score DOUBLE, top_drivers STRING,
               on_hand_units INT, on_order_units INT, days_of_cover DOUBLE, demand_per_day DOUBLE,
               overdue_po_count BIGINT, max_days_overdue INT, revenue_at_risk_3d DOUBLE)
COMMENT 'Latest stockout-risk score and context for items matching item_search (id or name) in a store.'
RETURN
  SELECT r.score_date, r.store_id, r.item_id, r.item_name, r.dept_id, r.supplier_name, r.risk_tier,
         round(r.risk_score, 3), concat_ws(', ', r.driver_1, r.driver_2, r.driver_3),
         r.on_hand_units, r.on_order_units, r.days_of_cover, r.lambda_90d, r.overdue_po_count,
         r.max_days_overdue, r.revenue_at_risk_3d
  FROM {S}.gold_stockout_risk_scores r
  WHERE (osa_item_risk.store_id = 'ALL' OR r.store_id = osa_item_risk.store_id)
    AND (r.item_id = upper(item_search) OR lower(r.item_name) LIKE concat('%', lower(item_search), '%'))
  ORDER BY r.risk_score DESC
  LIMIT 25
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION {S}.osa_store_action_queue(
  store_id STRING COMMENT 'Store id, e.g. CA_1. Use ALL for all stores.',
  top_n INT COMMENT 'How many actions to return (max 50)')
RETURNS TABLE (priority_rank INT, store_id STRING, item_id STRING, item_name STRING, risk_tier STRING,
               risk_score DOUBLE, recommended_action STRING, recommended_qty INT, revenue_at_risk_3d DOUBLE,
               rationale STRING)
COMMENT 'Tonight''s prioritised replenishment action queue (highest revenue at risk first).'
RETURN
  SELECT CAST(t.rn AS INT), t.store_id, t.item_id, t.item_name, t.risk_tier, round(t.risk_score, 3),
         t.recommended_action, CAST(t.recommended_qty AS INT), t.revenue_at_risk_3d, t.rationale
  FROM (SELECT q.*, row_number() OVER (ORDER BY q.revenue_at_risk_3d DESC) AS rn
        FROM {S}.gold_replenishment_recommendations q
        WHERE osa_store_action_queue.store_id = 'ALL' OR q.store_id = osa_store_action_queue.store_id) t
  WHERE t.rn <= least(coalesce(osa_store_action_queue.top_n, 10), 50)
  ORDER BY t.rn
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION {S}.osa_open_purchase_orders(
  store_id STRING COMMENT 'Store id, e.g. WI_1',
  item_id STRING COMMENT 'Item id, e.g. FOODS_3_586; use ALL for every item in the store')
RETURNS TABLE (po_id STRING, store_id STRING, item_id STRING, supplier_id STRING, created_date DATE,
               expected_date DATE, ordered_qty BIGINT, days_overdue INT, as_of_date DATE)
COMMENT 'Purchase orders still open at the latest snapshot date, with days overdue (0 = due today, negative = not yet due).'
RETURN
  WITH asof AS (SELECT max(snapshot_date) AS d FROM {S}.silver_inventory_snapshots)
  SELECT p.po_id, p.store_id, p.item_id, p.supplier_id, p.created_date, p.expected_date, p.ordered_qty,
         datediff(asof.d, p.expected_date), asof.d
  FROM {S}.silver_purchase_orders p CROSS JOIN asof
  WHERE p.store_id = osa_open_purchase_orders.store_id
    AND (osa_open_purchase_orders.item_id = 'ALL' OR p.item_id = osa_open_purchase_orders.item_id)
    AND p.created_date <= asof.d AND (p.received_date IS NULL OR p.received_date > asof.d)
  ORDER BY datediff(asof.d, p.expected_date) DESC
  LIMIT 50
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION {S}.osa_kpi_summary(
  region STRING COMMENT 'West, South, Midwest, or ALL')
RETURNS TABLE (scope STRING, period STRING, period_start DATE, period_end DATE, osa_pct DOUBLE,
               revenue DOUBLE, lost_revenue DOUBLE, lost_sales_rate_pct DOUBLE, oos_store_item_days BIGINT)
COMMENT 'On-shelf availability KPIs for the last 7 days vs the prior 7 days, for a region or ALL regions.'
RETURN
  WITH mx AS (SELECT max(date) AS d FROM {S}.gold_osa_kpi_daily),
  k AS (
    SELECT CASE WHEN k.date > mx.d - INTERVAL 7 DAYS THEN 'last_7d' ELSE 'prior_7d' END AS period, k.*
    FROM {S}.gold_osa_kpi_daily k CROSS JOIN mx
    WHERE k.date > mx.d - INTERVAL 14 DAYS
      AND (osa_kpi_summary.region = 'ALL' OR lower(k.region) = lower(osa_kpi_summary.region)))
  SELECT coalesce(nullif(osa_kpi_summary.region, 'ALL'), 'All regions'), period, min(date), max(date),
         round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2),
         round(sum(revenue), 0), round(sum(lost_revenue), 0),
         round(100 * sum(lost_revenue) / (sum(revenue) + sum(lost_revenue)), 2), sum(oos_store_items)
  FROM k GROUP BY period ORDER BY period
""")

spark.sql(f"""
CREATE OR REPLACE FUNCTION {S}.osa_supplier_watchlist(
  region STRING COMMENT 'West, South, Midwest, or ALL')
RETURNS TABLE (supplier_id STRING, supplier_name STRING, reliability_tier STRING, attributed_stockouts BIGINT,
               attributed_lost_revenue DOUBLE, ongoing_stockouts BIGINT, avg_days_late DOUBLE)
COMMENT 'Suppliers ranked by stockouts attributed to late POs in the last 28 days (root_cause = SUPPLIER_DELAY).'
RETURN
  WITH mx AS (SELECT max(end_date) AS d FROM {S}.gold_stockout_events)
  SELECT e.supplier_id, s.supplier_name, s.reliability_tier, count(*), round(sum(e.lost_revenue), 0),
         sum(CASE WHEN e.is_ongoing THEN 1 ELSE 0 END), round(avg(e.overdue_po_days_late), 2)
  FROM {S}.gold_stockout_events e CROSS JOIN mx
  JOIN {S}.dim_supplier s ON s.supplier_id = e.supplier_id
  WHERE e.root_cause = 'SUPPLIER_DELAY' AND e.start_date > mx.d - INTERVAL 28 DAYS
    AND (osa_supplier_watchlist.region = 'ALL' OR lower(e.region) = lower(osa_supplier_watchlist.region))
  GROUP BY e.supplier_id, s.supplier_name, s.reliability_tier
  ORDER BY 5 DESC
  LIMIT 10
""")

display(spark.sql(f"SHOW USER FUNCTIONS IN {S} LIKE 'osa_*'"))
```

**Output:**

| function |
|---|
| serverless_stable_4hkk7k_catalog.osa_retail.osa_item_risk |
| serverless_stable_4hkk7k_catalog.osa_retail.osa_kpi_summary |
| serverless_stable_4hkk7k_catalog.osa_retail.osa_open_purchase_orders |
| serverless_stable_4hkk7k_catalog.osa_retail.osa_store_action_queue |
| serverless_stable_4hkk7k_catalog.osa_retail.osa_supplier_watchlist |

## Smoke-test every tool

```python
display(spark.sql(f"SELECT * FROM {S}.osa_kpi_summary('ALL')"))
display(spark.sql(f"SELECT * FROM {S}.osa_store_action_queue('TX_2', 5)"))
top = spark.sql(f"SELECT store_id, item_id FROM {S}.gold_replenishment_recommendations ORDER BY priority_rank LIMIT 1").first()
display(spark.sql(f"SELECT * FROM {S}.osa_item_risk('{top.store_id}', '{top.item_id}')"))
display(spark.sql(f"SELECT * FROM {S}.osa_open_purchase_orders('{top.store_id}', 'ALL') LIMIT 10"))
display(spark.sql(f"SELECT * FROM {S}.osa_supplier_watchlist('ALL')"))
```

**Output:**

| scope | period | period_start | period_end | osa_pct | revenue | lost_revenue | lost_sales_rate_pct | oos_store_item_days |
|---|---|---|---|---|---|---|---|---|
| All regions | last_7d | 2016-05-17 | 2016-05-23 | 93.74 | 957303.0 | 40235.0 | 4.03 | 9609 |
| All regions | prior_7d | 2016-05-10 | 2016-05-16 | 91.98 | 1024462.0 | 50567.0 | 4.7 | 12198 |

| priority_rank | store_id | item_id | item_name | risk_tier | risk_score | recommended_action | recommended_qty | revenue_at_risk_3d | rationale |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TX_2 | FOODS_3_120 | Great Value Tortilla Chips #120 | OOS_PHANTOM | 0.238 | CYCLE_COUNT | 24 | 247.84 | System shows 231 units on hand with 13.92 days of cover, but zero recent sales suggest phantom inventory—conduct CYCLE_COUNT immediately and reorder 24 units if shelf is empty. |
| 2 | TX_2 | FOODS_3_695 | Northpeak Juice #695 | CRITICAL | 0.996 | EMERGENCY_DSD | 8 | 53.64 | Northpeak Juice #695 has 0 units on hand with 100% stockout probability; execute EMERGENCY_DSD of 8 units immediately due to 2-day overdue supplier PO. |
| 3 | TX_2 | FOODS_3_661 | Hearth & Home Ice Cream #661 | OOS_PHANTOM | 0.339 | CYCLE_COUNT | 48 | 50.4 | Conduct immediate cycle count for Hearth & Home Ice Cream #661 showing 50 units on-hand but zero recent sales despite 5.1 units/day demand; reorder 48 units if shelf empty. |
| 4 | TX_2 | FOODS_2_194 | Equate Black Beans #194 | CRITICAL | 0.856 | EXPEDITED_ORDER | 4 | 49.29 | Despite 12.61 days of cover, expedite 4 units immediately as 86% stockout probability exists due to delayed next receipt and insufficient on-order quantity of 41 units. |
| 5 | TX_2 | FOODS_2_181 | Hearth & Home Cereal #181 | CRITICAL | 0.902 | EXPEDITED_ORDER | 24 | 41.13 | Despite 69 units on-hand and 8.08 days cover, Hearth & Home Cereal #181 has 90% stockout probability; place EXPEDITED_ORDER for 24 units immediately. |

| score_date | store_id | item_id | item_name | dept_id | supplier_name | risk_tier | risk_score | top_drivers | on_hand_units | on_order_units | days_of_cover | demand_per_day | overdue_po_count | max_days_overdue | revenue_at_risk_3d |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016-05-23 | TX_2 | FOODS_3_120 | Great Value Tortilla Chips #120 | FOODS_3 | Northstar Snacks & Beverage | OOS_PHANTOM | 0.238 | lambda_90d, days_since_last_sale, cv_units_28d | 231 | 0 | 13.92 | 16.589 | 0 | -1 | 247.84 |

| po_id | store_id | item_id | supplier_id | created_date | expected_date | ordered_qty | days_overdue | as_of_date |
|---|---|---|---|---|---|---|---|---|
| PO-TX_2-HOBBIES_1_203-0002 | TX_2 | HOBBIES_1_203 | SUP013 | 2015-12-08 | 2015-12-12 | 4 | 163 | 2016-05-23 |
| PO-TX_2-HOBBIES_1_189-0003 | TX_2 | HOBBIES_1_189 | SUP011 | 2015-12-10 | 2015-12-13 | 21 | 162 | 2016-05-23 |
| PO-TX_2-FOODS_3_126-0002 | TX_2 | FOODS_3_126 | SUP009 | 2015-12-08 | 2015-12-13 | 3 | 162 | 2016-05-23 |
| PO-TX_2-HOBBIES_1_236-0002 | TX_2 | HOBBIES_1_236 | SUP013 | 2015-12-09 | 2015-12-13 | 15 | 162 | 2016-05-23 |
| PO-TX_2-FOODS_3_092-0004 | TX_2 | FOODS_3_092 | SUP007 | 2015-12-15 | 2015-12-18 | 8 | 157 | 2016-05-23 |
| PO-TX_2-FOODS_3_409-0005 | TX_2 | FOODS_3_409 | SUP008 | 2015-12-15 | 2015-12-19 | 6 | 156 | 2016-05-23 |
| PO-TX_2-HOBBIES_2_122-0006 | TX_2 | HOBBIES_2_122 | SUP014 | 2015-12-16 | 2015-12-21 | 11 | 154 | 2016-05-23 |
| DSD-TX_2-FOODS_2_303-0011 | TX_2 | FOODS_2_303 | SUP004 | 2016-01-12 | 2016-01-12 | 2 | 132 | 2016-05-23 |
| PO-TX_2-FOODS_3_603-0012 | TX_2 | FOODS_3_603 | SUP010 | 2016-01-12 | 2016-01-15 | 9 | 129 | 2016-05-23 |
| PO-TX_2-HOBBIES_1_310-0010 | TX_2 | HOBBIES_1_310 | SUP012 | 2016-01-26 | 2016-01-30 | 4 | 114 | 2016-05-23 |

| supplier_id | supplier_name | reliability_tier | attributed_stockouts | attributed_lost_revenue | ongoing_stockouts | avg_days_late |
|---|---|---|---|---|---|---|
| SUP009 | Prime Valley Distribution | C | 394 | 11072.0 | 61 | 6.46 |
| SUP018 | Polaris Paper & Plastics | B | 288 | 10831.0 | 27 | 7.07 |
| SUP010 | Lakeshore Beverage Group | C | 449 | 10304.0 | 53 | 6.28 |
| SUP016 | CleanWave Home Products | A | 324 | 9527.0 | 32 | 6.66 |
| SUP007 | Northstar Snacks & Beverage | B | 386 | 9480.0 | 55 | 6.4 |
| SUP017 | Ironwood Household Supply | B | 285 | 8274.0 | 28 | 7.07 |
| SUP006 | Coastal Canning Co | A | 274 | 8179.0 | 36 | 7.05 |
| SUP004 | Harvest Lane Grocers Supply | C | 229 | 6755.0 | 25 | 7.79 |
| SUP005 | Blue Ridge Pantry Distributors | B | 241 | 6670.0 | 28 | 6.59 |
| SUP008 | Evergreen Foods Wholesale | B | 295 | 6155.0 | 38 | 6.77 |
