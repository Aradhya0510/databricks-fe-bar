# Databricks notebook source
# MAGIC %md
# MAGIC # Governance 1/2 · Access model (runs **before** the pipeline)
# MAGIC
# MAGIC Unity Catalog policies referenced by the Lakeflow pipeline must exist before the pipeline creates its tables.
# MAGIC
# MAGIC **Entitlement-driven ABAC.** Who may see which region, and who may see commercial terms, is *data*: the governed
# MAGIC table `osa_access_entitlements(principal, entitlement)`. Policy functions look up `current_user()` in it, so
# MAGIC onboarding a new regional manager is an INSERT, not a code change. Account-group membership is honoured too.
# MAGIC
# MAGIC | Entitlement | Grants |
# MAGIC |---|---|
# MAGIC | `ADMIN` | all regions, unmasked (VP Supply Chain, Supply Planning, pipeline/job identity, the app) |
# MAGIC | `SOURCING_FINANCE` | supplier commercial terms + item cost unmasked |
# MAGIC | `REGION:<West/South/Midwest>` | rows of that region only in regional KPI / stockout tables |
# MAGIC
# MAGIC Policies are attached in the pipeline definition (`ROW FILTER` / `MASK`), so they hold for every consumer:
# MAGIC SQL, Genie, the agents, notebooks and the app.

# COMMAND ----------

dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("admin_principals", "", "extra ADMIN principals (comma separated, e.g. app SP id)")
dbutils.widgets.text("persona_principals", "", "persona grants, e.g. <sp-app-id>=REGION:South")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
S = f"{catalog}.{schema}"
me = spark.sql("SELECT current_user()").first()[0]

# COMMAND ----------

spark.sql(f"""CREATE TABLE IF NOT EXISTS {S}.osa_access_entitlements (
  principal STRING NOT NULL COMMENT 'User e-mail or service principal application id (= current_user())',
  entitlement STRING NOT NULL COMMENT 'ADMIN | SOURCING_FINANCE | REGION:<West|South|Midwest>',
  granted_by STRING, granted_at TIMESTAMP)
COMMENT 'ABAC entitlements consulted by the OSA row-filter and column-mask policy functions.'""")

wanted = [(me, "ADMIN")]
wanted += [(p.strip(), "ADMIN") for p in dbutils.widgets.get("admin_principals").split(",") if p.strip()]
for pair in dbutils.widgets.get("persona_principals").split(","):
    if "=" in pair:
        p, e = pair.split("=", 1)
        wanted.append((p.strip(), e.strip()))
spark.createDataFrame(wanted, "principal string, entitlement string").createOrReplaceTempView("wanted")
spark.sql(f"""MERGE INTO {S}.osa_access_entitlements t USING wanted s
              ON t.principal = s.principal AND t.entitlement = s.entitlement
              WHEN NOT MATCHED THEN INSERT (principal, entitlement, granted_by, granted_at)
                                    VALUES (s.principal, s.entitlement, '{me}', current_timestamp())""")
display(spark.sql(f"SELECT * FROM {S}.osa_access_entitlements ORDER BY entitlement, principal"))

# COMMAND ----------

# MAGIC %md ## Policy functions

# COMMAND ----------

def has(ent_sql):
    return (f"EXISTS (SELECT 1 FROM {S}.osa_access_entitlements e "
            f"WHERE e.principal = current_user() AND ({ent_sql}))")

spark.sql(f"""
CREATE OR REPLACE FUNCTION {S}.fn_region_filter(region STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: ADMIN sees all regions; REGION:<r> entitlement (or account group osa_region_<r>) sees region r.'
RETURN {has("e.entitlement = 'ADMIN' OR e.entitlement = concat('REGION:', region)")}
    OR is_account_group_member('osa_supply_chain_admins')
    OR is_account_group_member(concat('osa_region_', lower(region)))
""")

for typ, masked in [("double", "CAST(NULL AS DOUBLE)"), ("string", "'***RESTRICTED***'")]:
    spark.sql(f"""
    CREATE OR REPLACE FUNCTION {S}.fn_mask_commercial_{typ}(v {typ.upper()})
    RETURNS {typ.upper()}
    COMMENT 'Column mask: supplier commercial terms / item cost visible only to ADMIN and SOURCING_FINANCE.'
    RETURN CASE WHEN {has("e.entitlement IN ('ADMIN', 'SOURCING_FINANCE')")}
                  OR is_account_group_member('osa_sourcing_finance') THEN v ELSE {masked} END
    """)

spark.sql(f"""
CREATE OR REPLACE FUNCTION {S}.fn_mask_email(v STRING)
RETURNS STRING
COMMENT 'Column mask: e-mail local part redacted for everyone except ADMIN.'
RETURN CASE WHEN {has("e.entitlement = 'ADMIN'")} THEN v ELSE regexp_replace(v, '^[^@]+', '****') END
""")

display(spark.sql(f"SHOW USER FUNCTIONS IN {S} LIKE 'fn_*'"))

# COMMAND ----------

# Policy check as the current identity (an ADMIN)
display(spark.sql(f"""
SELECT current_user() AS identity,
       {S}.fn_region_filter('West') AS sees_west, {S}.fn_region_filter('South') AS sees_south,
       {S}.fn_mask_commercial_double(0.62) AS cost_ratio, {S}.fn_mask_email('maria.alvarez@osa-demo-retail.example') AS email
"""))
