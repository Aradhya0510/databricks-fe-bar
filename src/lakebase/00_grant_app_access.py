# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase 0 · Postgres grants for the app's service principal
# MAGIC
# MAGIC Synced tables in Postgres schema `serving` are owned by the pipeline owner; the app's service principal only
# MAGIC gets `CAN_CONNECT_AND_CREATE` from its app resource. Grant it read access on `serving` (incl. future tables), and
# MAGIC show what the app has written into its own schema `osa_app`.

# COMMAND ----------

# MAGIC %pip install -q "psycopg[binary]>=3.2" "databricks-sdk>=0.81"
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("lakebase_project", "my-fe-bar-project")
dbutils.widgets.text("app_sp_client_id", "")
PROJECT = dbutils.widgets.get("lakebase_project")
APP_SP = dbutils.widgets.get("app_sp_client_id").strip()

import psycopg
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
ep = w.postgres.get_endpoint(name=f"projects/{PROJECT}/branches/production/endpoints/primary")
token = w.postgres.generate_database_credential(endpoint=ep.name).token
conn = psycopg.connect(host=ep.status.hosts.host, dbname="databricks_postgres", user=w.current_user.me().user_name,
                       password=token, sslmode="require", autocommit=True)

def q(sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() if cur.description else []

print(q("SELECT current_user, version()")[0])

# COMMAND ----------

roles = [r[0] for r in q("SELECT rolname FROM pg_roles WHERE rolname = %s", (APP_SP,))]
print(f"app role present: {bool(roles)}")
if roles:
    for stmt in [f'GRANT USAGE ON SCHEMA serving TO "{APP_SP}"',
                 f'GRANT SELECT ON ALL TABLES IN SCHEMA serving TO "{APP_SP}"',
                 f'ALTER DEFAULT PRIVILEGES IN SCHEMA serving GRANT SELECT ON TABLES TO "{APP_SP}"']:
        q(stmt)
        print("ok:", stmt)

# COMMAND ----------

for row in q("""SELECT table_schema, table_name, grantee, string_agg(privilege_type, ',') AS privileges
                FROM information_schema.role_table_grants WHERE table_schema IN ('serving', 'osa_app')
                GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"""):
    print(row)

# COMMAND ----------

print("rows per Lakebase table:")
for schema, table in q("""SELECT table_schema, table_name FROM information_schema.tables
                          WHERE table_schema IN ('serving', 'osa_app') ORDER BY 1, 2"""):
    print(f"  {schema}.{table}: {q(f'SELECT count(*) FROM {schema}.{table}')[0][0]:,}")
