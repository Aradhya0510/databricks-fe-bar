# Task `governance_apply` — SUCCESS

*Run 208151004152290 · started 2026-10-30 23:57:40 UTC · 55s*

# Governance 2/2 · Classify, document, grant, and prove it (runs **after** the pipeline)

* **Classification tags** on every table: `layer`, `source` (public:m5 / synthetic / derived), `domain`,
  and column-level `pii` / `confidential` tags.
* **Business documentation**: column comments on the gold tables (they also teach Genie the semantics).
* **Least-privilege grants** per persona group.
* **Evidence**: tags, row filters, column masks, grants and lineage read back from `information_schema` and
  `system.access.table_lineage`.

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("persona_principals", "", "e.g. <sp-app-id>=REGION:South")
dbutils.widgets.text("admin_principals", "", "ADMIN principals, e.g. the app SP")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
S = f"{catalog}.{schema}"
personas = [p.split("=", 1)[0].strip() for p in dbutils.widgets.get("persona_principals").split(",") if "=" in p]

def run(sql):
    try:
        spark.sql(sql)
        return "ok"
    except Exception as e:
        return f"skipped: {str(e).splitlines()[0][:140]}"

tables = {r.table_name: r.table_type for r in spark.sql(
    f"SELECT table_name, table_type FROM {catalog}.information_schema.tables WHERE table_schema = '{schema}'").collect()}
print(f"{len(tables)} tables/views in {S}")
```

**Output:**

```text
56 tables/views in serverless_stable_4hkk7k_catalog.osa_retail
```

## Table classification tags

```python
# `layer` and `domain` are account-governed tag keys (allowed values enforced by tag policies);
# `osa_data_origin` / `osa_project` are free-form project tags.
def layer(t):
    return ("bronze" if t.startswith("bronze_") else "silver" if t.startswith(("silver_", "dim_"))
            else "gold" if t.startswith(("gold_", "replenishment_")) else None)

def origin(t):
    if t.startswith("bronze_m5") or t in ("bronze_pos_daily_sales", "silver_calendar", "silver_sell_prices", "silver_sales_daily"):
        return "public_m5"
    if t.startswith(("bronze_erp", "dim_store", "dim_supplier", "silver_inventory", "silver_po", "silver_purchase")):
        return "synthetic"
    return "derived"

results = []
for t, ttype in sorted(tables.items()):
    if t.startswith("__"):          # Lakeflow-internal materialization tables
        continue
    kw = "MATERIALIZED VIEW" if ttype == "MATERIALIZED_VIEW" else "VIEW" if ttype == "VIEW" else "TABLE"
    tags = {"domain": "supply_chain", "osa_data_origin": origin(t), "osa_project": "osa-retail"}
    if layer(t):
        tags["layer"] = layer(t)
    tag_sql = ", ".join(f"'{k}' = '{v}'" for k, v in tags.items())
    results.append((t, ttype, run(f"ALTER {kw} {S}.{t} SET TAGS ({tag_sql})")))
display(spark.createDataFrame(results, "table string, type string, tagging string"))
```

**Output:**

| table | type | tagging |
|---|---|---|
| bronze_erp_inventory_snapshots | STREAMING_TABLE | ok |
| bronze_erp_item_master | STREAMING_TABLE | ok |
| bronze_erp_po_events | STREAMING_TABLE | ok |
| bronze_erp_stores | STREAMING_TABLE | ok |
| bronze_erp_suppliers | STREAMING_TABLE | ok |
| bronze_m5_calendar | STREAMING_TABLE | ok |
| bronze_m5_sales_wide | STREAMING_TABLE | ok |
| bronze_m5_sell_prices | STREAMING_TABLE | ok |
| bronze_pos_daily_sales | STREAMING_TABLE | ok |
| dim_item | MATERIALIZED_VIEW | ok |
| dim_store | MATERIALIZED_VIEW | ok |
| dim_supplier | MATERIALIZED_VIEW | ok |
| event_log_320292b1_a8ff_4653_80ac_e119c25b030a | MANAGED | ok |
| event_log_3b3c9c11_4a13_481b_90c4_a82d34ee6102 | MANAGED | ok |
| event_log_87d43533_ad93_46d6_8647_9a7724fcd75c | MANAGED | ok |
| event_log_fa08392a_1518_4d6a_88eb_f935c53c7ba5 | MANAGED | ok |
| gold_intelligence_reports | MANAGED | ok |
| gold_osa_kpi_daily | MATERIALIZED_VIEW | ok |
| gold_replenishment_recommendations | MANAGED | ok |
| gold_stockout_events | MATERIALIZED_VIEW | ok |
| gold_stockout_features | MATERIALIZED_VIEW | ok |
| gold_stockout_risk_scores | MANAGED | ok |
| gold_stockout_risk_scores_history | MANAGED | ok |
| gold_store_item_daily | MATERIALIZED_VIEW | ok |
| gold_supplier_performance_weekly | MATERIALIZED_VIEW | ok |
| osa_access_entitlements | MANAGED | ok |
| replenishment_actions | MANAGED | ok |
| silver_calendar | MATERIALIZED_VIEW | ok |
| silver_inventory_snapshots | MATERIALIZED_VIEW | ok |
| silver_po_events | STREAMING_TABLE | ok |
| silver_purchase_orders | MATERIALIZED_VIEW | ok |
| silver_sales_daily | STREAMING_TABLE | ok |
| silver_sell_prices | MATERIALIZED_VIEW | ok |

```python
# class.* keys are the account's governed data-classification tags
col_tags = [
    ("dim_store", "store_manager_email", "class.email_address", None),
    ("dim_store", "regional_manager_email", "class.email_address", None),
    ("dim_store", "store_manager", "class.name", None),
    ("dim_supplier", "account_manager_email", "class.email_address", None),
    ("dim_supplier", "late_penalty_pct_of_po", "confidential", "commercial_terms"),
    ("dim_supplier", "payment_terms", "confidential", "commercial_terms"),
    ("dim_item", "negotiated_cost_ratio", "confidential", "cost"),
]
def tag_sql(k, v):
    return f"'{k}'" if v is None else f"'{k}' = '{v}'"
display(spark.createDataFrame(
    [(t, c, k, v or "", run(f"ALTER MATERIALIZED VIEW {S}.{t} ALTER COLUMN {c} SET TAGS ({tag_sql(k, v)})"))
     for t, c, k, v in col_tags], "table string, column string, tag string, value string, result string"))
```

**Output:**

| table | column | tag | value | result |
|---|---|---|---|---|
| dim_store | store_manager_email | class.email_address |  | ok |
| dim_store | regional_manager_email | class.email_address |  | ok |
| dim_store | store_manager | class.name |  | ok |
| dim_supplier | account_manager_email | class.email_address |  | ok |
| dim_supplier | late_penalty_pct_of_po | confidential | commercial_terms | ok |
| dim_supplier | payment_terms | confidential | commercial_terms | ok |
| dim_item | negotiated_cost_ratio | confidential | cost | ok |

## Business column documentation (gold)

```python
docs = {
    "gold_store_item_daily": {
        "is_oos": "TRUE when the day is inferred out-of-stock: inside a zero-sales streak with lambda*L >= 4.6 (P<1%).",
        "lambda_90d": "Trailing 90-day mean daily unit sales (demand rate) before this day.",
        "lost_units": "Estimated units not sold because of the stockout (= demand rate on OOS days).",
        "lost_revenue": "lost_units x shelf price, in USD.",
        "days_of_cover": "On-hand units / demand rate at end of day.",
        "is_active": "Item-store is active (demand rate >= 0.3/day or OOS) - denominator for OSA %.",
    },
    "gold_osa_kpi_daily": {
        "osa_pct": "On-shelf availability % = 100 x (1 - oos_store_items / active_store_items).",
        "lost_sales_rate_pct": "Lost revenue as % of (revenue + lost revenue).",
        "lost_revenue": "Estimated revenue lost to stockouts, USD.",
        "region": "West (CA), South (TX), Midwest (WI). Row-level security applies on this column.",
    },
    "gold_stockout_events": {
        "root_cause": "SUPPLIER_DELAY | PHANTOM_INVENTORY | DEMAND_SPIKE | UNEXPLAINED | NO_OPS_DATA (before ERP window).",
        "oos_days": "Length of the stockout in days.",
        "is_ongoing": "TRUE if the item is still out of stock on the latest date.",
    },
    "gold_supplier_performance_weekly": {
        "on_time_pct": "% of supplier POs due in the week that were received on or before the expected date.",
        "attributed_stockouts": "Stockout events in the week whose root cause is a late PO from this supplier.",
    },
}
out = []
for t, cols in docs.items():
    for c, txt in cols.items():
        out.append((t, c, run(f"ALTER MATERIALIZED VIEW {S}.{t} ALTER COLUMN {c} COMMENT '{txt}'")))
display(spark.createDataFrame(out, "table string, column string, result string"))
```

**Output:**

| table | column | result |
|---|---|---|
| gold_store_item_daily | is_oos | ok |
| gold_store_item_daily | lambda_90d | ok |
| gold_store_item_daily | lost_units | ok |
| gold_store_item_daily | lost_revenue | ok |
| gold_store_item_daily | days_of_cover | ok |
| gold_store_item_daily | is_active | ok |
| gold_osa_kpi_daily | osa_pct | ok |
| gold_osa_kpi_daily | lost_sales_rate_pct | ok |
| gold_osa_kpi_daily | lost_revenue | ok |
| gold_osa_kpi_daily | region | ok |
| gold_stockout_events | root_cause | ok |
| gold_stockout_events | oos_days | ok |
| gold_stockout_events | is_ongoing | ok |
| gold_supplier_performance_weekly | on_time_pct | ok |
| gold_supplier_performance_weekly | attributed_stockouts | ok |

## Grants (least privilege per persona)

```python
# Persona principals (store / regional managers) get read access to the curated gold + dimension tables only;
# what they actually see inside those tables is decided by the row filter and column masks.
persona_objects = ["gold_osa_kpi_daily", "gold_stockout_events", "gold_supplier_performance_weekly", "dim_item",
                   "dim_store", "dim_supplier", "gold_replenishment_recommendations", "osa_access_entitlements"]
admins = [p.strip() for p in dbutils.widgets.get("admin_principals").split(",") if p.strip()]
grants = []
for p in admins:   # e.g. the app's service principal: full read + tool execution on the project schema
    grants += [f"GRANT USE CATALOG ON CATALOG {catalog} TO `{p}`",
               f"GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA {S} TO `{p}`"]
for p in personas:
    grants += [f"GRANT USE CATALOG ON CATALOG {catalog} TO `{p}`", f"GRANT USE SCHEMA ON SCHEMA {S} TO `{p}`"]
    grants += [f"GRANT SELECT ON TABLE {S}.{o} TO `{p}`" for o in persona_objects]
    grants += [f"GRANT EXECUTE ON FUNCTION {S}.{f} TO `{p}`" for f in
               ["fn_region_filter", "fn_mask_commercial_double", "fn_mask_commercial_string", "fn_mask_email"]]
display(spark.createDataFrame([(g, run(g)) for g in grants] or [("(no persona principals configured)", "")],
                              "statement string, result string"))
```

**Output:**

| statement | result |
|---|---|
| GRANT USE CATALOG ON CATALOG serverless_stable_4hkk7k_catalog TO `469361d3-732e-45be-b178-e0f3c33ad5ec` | ok |
| GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA serverless_stable_4hkk7k_catalog.osa_retail TO `469361d3-732e-45be-b178-e0f3c33ad5ec` | ok |
| GRANT USE CATALOG ON CATALOG serverless_stable_4hkk7k_catalog TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT USE SCHEMA ON SCHEMA serverless_stable_4hkk7k_catalog.osa_retail TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_events TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.gold_supplier_performance_weekly TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.dim_item TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.dim_store TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.dim_supplier TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.gold_replenishment_recommendations TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT SELECT ON TABLE serverless_stable_4hkk7k_catalog.osa_retail.osa_access_entitlements TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT EXECUTE ON FUNCTION serverless_stable_4hkk7k_catalog.osa_retail.fn_region_filter TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT EXECUTE ON FUNCTION serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_commercial_double TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT EXECUTE ON FUNCTION serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_commercial_string TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |
| GRANT EXECUTE ON FUNCTION serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_email TO `8e31f1c1-5055-49b6-9a53-5903b724ef03` | ok |

## Evidence: policies, tags, grants, lineage

```python
display(spark.sql(f"""
SELECT table_name, filter_name AS policy_function, target_columns
FROM {catalog}.information_schema.row_filters WHERE table_schema = '{schema}'"""))
```

**Output:**

| table_name | policy_function | target_columns |
|---|---|---|
| gold_osa_kpi_daily | serverless_stable_4hkk7k_catalog.osa_retail.fn_region_filter | region |
| gold_stockout_events | serverless_stable_4hkk7k_catalog.osa_retail.fn_region_filter | region |

```python
display(spark.sql(f"""
SELECT table_name, column_name, mask_name AS policy_function
FROM {catalog}.information_schema.column_masks WHERE table_schema = '{schema}' ORDER BY 1, 2"""))
```

**Output:**

| table_name | column_name | policy_function |
|---|---|---|
| dim_item | negotiated_cost_ratio | serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_commercial_double |
| dim_store | regional_manager_email | serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_email |
| dim_store | store_manager_email | serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_email |
| dim_supplier | account_manager_email | serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_email |
| dim_supplier | late_penalty_pct_of_po | serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_commercial_double |
| dim_supplier | payment_terms | serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_commercial_string |

```python
display(spark.sql(f"""
SELECT tag_name, tag_value, count(*) AS tables
FROM {catalog}.information_schema.table_tags WHERE schema_name = '{schema}'
GROUP BY ALL ORDER BY tag_name, tag_value"""))
```

**Output:**

| tag_name | tag_value | tables |
|---|---|---|
| domain | supply_chain | 33 |
| layer | bronze | 9 |
| layer | gold | 10 |
| layer | silver | 9 |
| osa_data_origin | derived | 16 |
| osa_data_origin | public_m5 | 7 |
| osa_data_origin | synthetic | 10 |
| osa_project | osa-retail | 33 |

```python
display(spark.sql(f"""
SELECT table_name, column_name, tag_name, tag_value
FROM {catalog}.information_schema.column_tags WHERE schema_name = '{schema}' ORDER BY 1, 2"""))
```

**Output:**

| table_name | column_name | tag_name | tag_value |
|---|---|---|---|
| dim_item | negotiated_cost_ratio | confidential | cost |
| dim_store | regional_manager_email | class.email_address |  |
| dim_store | store_manager | class.name |  |
| dim_store | store_manager_email | class.email_address |  |
| dim_supplier | account_manager_email | class.email_address |  |
| dim_supplier | late_penalty_pct_of_po | confidential | commercial_terms |
| dim_supplier | payment_terms | confidential | commercial_terms |

```python
display(spark.sql(f"""
SELECT grantee, table_name, privilege_type
FROM {catalog}.information_schema.table_privileges
WHERE table_schema = '{schema}' AND grantee IN ({", ".join(f"'{p}'" for p in personas) or "''"})
ORDER BY grantee, table_name"""))
```

**Output:**

| grantee | table_name | privilege_type |
|---|---|---|
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | dim_item | SELECT |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | dim_store | SELECT |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | dim_supplier | SELECT |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | gold_osa_kpi_daily | SELECT |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | gold_replenishment_recommendations | SELECT |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | gold_stockout_events | SELECT |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | gold_supplier_performance_weekly | SELECT |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | osa_access_entitlements | SELECT |

```python
display(spark.sql(f"SELECT principal, entitlement, granted_by, granted_at FROM {S}.osa_access_entitlements ORDER BY entitlement"))
```

**Output:**

| principal | entitlement | granted_by | granted_at |
|---|---|---|---|
| aradhya.chouhan@databricks.com | ADMIN | aradhya.chouhan@databricks.com | 2026-10-30T22:21:46.023Z |
| 469361d3-732e-45be-b178-e0f3c33ad5ec | ADMIN | aradhya.chouhan@databricks.com | 2026-10-30T23:24:05.771Z |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | REGION:South | aradhya.chouhan@databricks.com | 2026-10-30T22:21:46.023Z |

```python
lineage = spark.sql(f"""
SELECT DISTINCT source_table_full_name AS upstream, target_table_full_name AS downstream, entity_type
FROM system.access.table_lineage
WHERE target_table_schema = '{schema}' AND source_table_full_name IS NOT NULL
  AND event_date >= current_date() - INTERVAL 7 DAYS
ORDER BY downstream, upstream""")
print(f"lineage edges into {S}: {lineage.count()}")
display(lineage)
```

**Output:**

```text
lineage edges into serverless_stable_4hkk7k_catalog.osa_retail: 31
```

| upstream | downstream | entity_type |
|---|---|---|
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_erp_item_master | serverless_stable_4hkk7k_catalog.osa_retail.dim_item | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_erp_stores | serverless_stable_4hkk7k_catalog.osa_retail.dim_store | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_erp_suppliers | serverless_stable_4hkk7k_catalog.osa_retail.dim_supplier | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail._queue_llm_scratch | serverless_stable_4hkk7k_catalog.osa_retail.gold_replenishment_recommendations | JOB |
| serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_events | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_inventory_snapshots | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_events | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_purchase_orders | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_events | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.dim_supplier | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_features | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_features | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_calendar | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_features | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_inventory_snapshots | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_features | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_purchase_orders | serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_features | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.dim_item | serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.dim_store | serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_calendar | serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_inventory_snapshots | serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_sales_daily | serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_sell_prices | serverless_stable_4hkk7k_catalog.osa_retail.gold_store_item_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.dim_supplier | serverless_stable_4hkk7k_catalog.osa_retail.gold_supplier_performance_weekly | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_events | serverless_stable_4hkk7k_catalog.osa_retail.gold_supplier_performance_weekly | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_calendar | serverless_stable_4hkk7k_catalog.osa_retail.gold_supplier_performance_weekly | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_purchase_orders | serverless_stable_4hkk7k_catalog.osa_retail.gold_supplier_performance_weekly | PIPELINE |
| osa_lakebase.osa_app.replenishment_actions | serverless_stable_4hkk7k_catalog.osa_retail.replenishment_actions | JOB |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_m5_calendar | serverless_stable_4hkk7k_catalog.osa_retail.silver_calendar | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_erp_inventory_snapshots | serverless_stable_4hkk7k_catalog.osa_retail.silver_inventory_snapshots | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_erp_po_events | serverless_stable_4hkk7k_catalog.osa_retail.silver_po_events | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.silver_po_events | serverless_stable_4hkk7k_catalog.osa_retail.silver_purchase_orders | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_m5_sales_wide | serverless_stable_4hkk7k_catalog.osa_retail.silver_sales_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_pos_daily_sales | serverless_stable_4hkk7k_catalog.osa_retail.silver_sales_daily | PIPELINE |
| serverless_stable_4hkk7k_catalog.osa_retail.bronze_m5_sell_prices | serverless_stable_4hkk7k_catalog.osa_retail.silver_sell_prices | PIPELINE |
