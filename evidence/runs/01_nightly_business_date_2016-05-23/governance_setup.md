# Task `governance_setup` — SUCCESS

*Run 1107641825585143 · started 2026-10-30 23:53:31 UTC · 31s*

# Governance 1/2 · Access model (runs **before** the pipeline)

Unity Catalog policies referenced by the Lakeflow pipeline must exist before the pipeline creates its tables.

**Entitlement-driven ABAC.** Who may see which region, and who may see commercial terms, is *data*: the governed
table `osa_access_entitlements(principal, entitlement)`. Policy functions look up `current_user()` in it, so
onboarding a new regional manager is an INSERT, not a code change. Account-group membership is honoured too.

| Entitlement | Grants |
|---|---|
| `ADMIN` | all regions, unmasked (VP Supply Chain, Supply Planning, pipeline/job identity, the app) |
| `SOURCING_FINANCE` | supplier commercial terms + item cost unmasked |
| `REGION:<West/South/Midwest>` | rows of that region only in regional KPI / stockout tables |

Policies are attached in the pipeline definition (`ROW FILTER` / `MASK`), so they hold for every consumer:
SQL, Genie, the agents, notebooks and the app.

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("admin_principals", "", "extra ADMIN principals (comma separated, e.g. app SP id)")
dbutils.widgets.text("persona_principals", "", "persona grants, e.g. <sp-app-id>=REGION:South")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
S = f"{catalog}.{schema}"
me = spark.sql("SELECT current_user()").first()[0]
```

```python
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
```

**Output:**

| principal | entitlement | granted_by | granted_at |
|---|---|---|---|
| 469361d3-732e-45be-b178-e0f3c33ad5ec | ADMIN | aradhya.chouhan@databricks.com | 2026-10-30T23:24:05.771Z |
| aradhya.chouhan@databricks.com | ADMIN | aradhya.chouhan@databricks.com | 2026-10-30T22:21:46.023Z |
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 | REGION:South | aradhya.chouhan@databricks.com | 2026-10-30T22:21:46.023Z |

## Policy functions

```python
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
```

**Output:**

| function |
|---|
| serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_commercial_double |
| serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_commercial_string |
| serverless_stable_4hkk7k_catalog.osa_retail.fn_mask_email |
| serverless_stable_4hkk7k_catalog.osa_retail.fn_region_filter |

```python
# Policy check as the current identity (an ADMIN)
display(spark.sql(f"""
SELECT current_user() AS identity,
       {S}.fn_region_filter('West') AS sees_west, {S}.fn_region_filter('South') AS sees_south,
       {S}.fn_mask_commercial_double(0.62) AS cost_ratio, {S}.fn_mask_email('maria.alvarez@osa-demo-retail.example') AS email
"""))
```

**Output:**

| identity | sees_west | sees_south | cost_ratio | email |
|---|---|---|---|---|
| aradhya.chouhan@databricks.com | True | True | 0.62 | maria.alvarez@osa-demo-retail.example |
