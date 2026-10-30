# Databricks notebook source
# MAGIC %md
# MAGIC # Governance 2/2 · Classify, document, grant, and prove it (runs **after** the pipeline)
# MAGIC
# MAGIC * **Classification tags** on every table: `layer`, `source` (public:m5 / synthetic / derived), `domain`,
# MAGIC   and column-level `pii` / `confidential` tags.
# MAGIC * **Business documentation**: column comments on the gold tables (they also teach Genie the semantics).
# MAGIC * **Least-privilege grants** per persona group.
# MAGIC * **Evidence**: tags, row filters, column masks, grants and lineage read back from `information_schema` and
# MAGIC   `system.access.table_lineage`.

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ## Table classification tags

# COMMAND ----------

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

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ## Business column documentation (gold)

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ## Grants (least privilege per persona)

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md ## Evidence: policies, tags, grants, lineage

# COMMAND ----------

display(spark.sql(f"""
SELECT table_name, filter_name AS policy_function, target_columns
FROM {catalog}.information_schema.row_filters WHERE table_schema = '{schema}'"""))

# COMMAND ----------

display(spark.sql(f"""
SELECT table_name, column_name, mask_name AS policy_function
FROM {catalog}.information_schema.column_masks WHERE table_schema = '{schema}' ORDER BY 1, 2"""))

# COMMAND ----------

display(spark.sql(f"""
SELECT tag_name, tag_value, count(*) AS tables
FROM {catalog}.information_schema.table_tags WHERE schema_name = '{schema}'
GROUP BY ALL ORDER BY tag_name, tag_value"""))

# COMMAND ----------

display(spark.sql(f"""
SELECT table_name, column_name, tag_name, tag_value
FROM {catalog}.information_schema.column_tags WHERE schema_name = '{schema}' ORDER BY 1, 2"""))

# COMMAND ----------

display(spark.sql(f"""
SELECT grantee, table_name, privilege_type
FROM {catalog}.information_schema.table_privileges
WHERE table_schema = '{schema}' AND grantee IN ({", ".join(f"'{p}'" for p in personas) or "''"})
ORDER BY grantee, table_name"""))

# COMMAND ----------

display(spark.sql(f"SELECT principal, entitlement, granted_by, granted_at FROM {S}.osa_access_entitlements ORDER BY entitlement"))

# COMMAND ----------

lineage = spark.sql(f"""
SELECT DISTINCT source_table_full_name AS upstream, target_table_full_name AS downstream, entity_type
FROM system.access.table_lineage
WHERE target_table_schema = '{schema}' AND source_table_full_name IS NOT NULL
  AND event_date >= current_date() - INTERVAL 7 DAYS
ORDER BY downstream, upstream""")
print(f"lineage edges into {S}: {lineage.count()}")
display(lineage)
