# Task `agent_tools` — FAILED

*Run 809764781771715 · started 2026-10-30 23:39:16 UTC · 16s*

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
  SELECT CAST(row_number() OVER (ORDER BY q.revenue_at_risk_3d DESC) AS INT), q.store_id, q.item_id, q.item_name,
         q.risk_tier, round(q.risk_score, 3), q.recommended_action, CAST(q.recommended_qty AS INT),
         q.revenue_at_risk_3d, q.rationale
  FROM {S}.gold_replenishment_recommendations q
  WHERE osa_store_action_queue.store_id = 'ALL' OR q.store_id = osa_store_action_queue.store_id
  QUALIFY row_number() OVER (ORDER BY q.revenue_at_risk_3d DESC) <= least(coalesce(osa_store_action_queue.top_n, 10), 50)
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



```text
ERROR: ---------------------------------------------------------------------------
AnalysisException                         Traceback (most recent call last)
File <command-8293210456947530>, line 22
      1 spark.sql(f"""
      2 CREATE OR REPLACE FUNCTION {S}.osa_item_risk(
      3   store_id STRING COMMENT 'Store id, e.g. TX_2. Use ALL for every store.',
   (...)     19   LIMIT 25
     20 """)
---> 22 spark.sql(f"""
     23 CREATE OR REPLACE FUNCTION {S}.osa_store_action_queue(
     24   store_id STRING COMMENT 'Store id, e.g. CA_1. Use ALL for all stores.',
     25   top_n INT COMMENT 'How many actions to return (max 50)')
     26 RETURNS TABLE (priority_rank INT, store_id STRING, item_id STRING, item_name STRING, risk_tier STRING,
     27                risk_score DOUBLE, recommended_action STRING, recommended_qty INT, revenue_at_risk_3d DOUBLE,
     28                rationale STRING)
     29 COMMENT 'Tonight''s prioritised replenishment action queue (highest revenue at risk first).'
     30 RETURN
     31   SELECT CAST(row_number() OVER (ORDER BY q.revenue_at_risk_3d DESC) AS INT), q.store_id, q.item_id, q.item_name,
     32          q.risk_tier, round(q.risk_score, 3), q.recommended_action, CAST(q.recommended_qty AS INT),
     33          q.revenue_at_risk_3d, q.rationale
     34   FROM {S}.gold_replenishment_recommendations q
     35   WHERE osa_store_action_queue.store_id = 'ALL' OR q.store_id = osa_store_action_queue.store_id
     36   QUALIFY row_number() OVER (ORDER BY q.revenue_at_risk_3d DESC) <= least(coalesce(osa_store_action_queue.top_n, 10), 50)
     37 """)
     39 spark.sql(f"""
     40 CREATE OR REPLACE FUNCTION {S}.osa_open_purchase_orders(
     41   store_id STRING COMMENT 'Store id, e.g. WI_1',
   (...)     55   LIMIT 50
     56 """)
     58 spark.sql(f"""
     59 CREATE OR REPLACE FUNCTION {S}.osa_kpi_summary(
     60   region STRING COMMENT 'West, South, Midwest, or ALL')
   (...)     75   FROM k GROUP BY period ORDER BY period
     76 """)

File /databricks/python/lib/python3.12/site-packages/pyspark/sql/connect/session.py:919, in SparkSession.sql(self, sqlQuery, args, **kwargs)
    916         _views.append(SubqueryAlias(df._plan, name))
    918 cmd = SQL(sqlQuery, _args, _named_args, _views)
--> 919 data, properties, ei = self.client.execute_command(cmd.command(self._client))
    920 if "sql_command_result" in properties:
    921     df = DataFrame(CachedRelation(properties["sql_command_result"]), self)

File /databricks/python/lib/python3.12/site-packages/pyspark/sql/connect/client/core.py:1812, in SparkConnectClient.execute_command(self, command, observations, extra_request_metadata)
   1810 req = self._execute_plan_request_with_metadata()
   1811 self._set_command_in_plan(req.plan, command)
-> 1812 data, _, metrics, observed_metrics, properties = self._execute_and_fetch(
   1813     req, observations or {}, extra_request_metadata
   1814 )
   1815 # Create a query execution object.
   1816 ei = ExecutionInfo(metrics, obs
```

## Smoke-test every tool

```python
display(spark.sql(f"SELECT * FROM {S}.osa_kpi_summary('ALL')"))
display(spark.sql(f"SELECT * FROM {S}.osa_store_action_queue('TX_2', 5)"))
top = spark.sql(f"SELECT store_id, item_id FROM {S}.gold_replenishment_recommendations ORDER BY priority_rank LIMIT 1").first()
display(spark.sql(f"SELECT * FROM {S}.osa_item_risk('{top.store_id}', '{top.item_id}')"))
display(spark.sql(f"SELECT * FROM {S}.osa_open_purchase_orders('{top.store_id}', 'ALL') LIMIT 10"))
display(spark.sql(f"SELECT * FROM {S}.osa_supplier_watchlist('ALL')"))
```
