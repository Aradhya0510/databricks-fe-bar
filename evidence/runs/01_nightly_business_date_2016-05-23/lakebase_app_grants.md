# Task `lakebase_app_grants` — SUCCESS

*Run 64429983975795 · started 2026-10-31 00:11:33 UTC · 25s*

# Lakebase 0 · Postgres grants for the app's service principal

Synced tables in Postgres schema `serving` are owned by the pipeline owner; the app's service principal only
gets `CAN_CONNECT_AND_CREATE` from its app resource. Grant it read access on `serving` (incl. future tables), and
show what the app has written into its own schema `osa_app`.

```python
%pip install -q "psycopg[binary]>=3.2" "databricks-sdk>=0.81"
%restart_python
```

**Output:**

```text
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

```python
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
```

**Output:**

```text
('aradhya.chouhan@databricks.com', 'PostgreSQL 17.11 (0bfbbeb) on aarch64-unknown-linux-gnu, compiled by gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit')
```

```python
roles = [r[0] for r in q("SELECT rolname FROM pg_roles WHERE rolname = %s", (APP_SP,))]
print(f"app role present: {bool(roles)}")
if roles:
    for stmt in [f'GRANT USAGE ON SCHEMA serving TO "{APP_SP}"',
                 f'GRANT SELECT ON ALL TABLES IN SCHEMA serving TO "{APP_SP}"',
                 f'ALTER DEFAULT PRIVILEGES IN SCHEMA serving GRANT SELECT ON TABLES TO "{APP_SP}"']:
        q(stmt)
        print("ok:", stmt)
```

**Output:**

```text
app role present: True
ok: GRANT USAGE ON SCHEMA serving TO "469361d3-732e-45be-b178-e0f3c33ad5ec"
ok: GRANT SELECT ON ALL TABLES IN SCHEMA serving TO "469361d3-732e-45be-b178-e0f3c33ad5ec"
ok: ALTER DEFAULT PRIVILEGES IN SCHEMA serving GRANT SELECT ON TABLES TO "469361d3-732e-45be-b178-e0f3c33ad5ec"
```

```python
for row in q("""SELECT table_schema, table_name, grantee, string_agg(privilege_type, ',') AS privileges
                FROM information_schema.role_table_grants WHERE table_schema IN ('serving', 'osa_app')
                GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"""):
    print(row)
```

**Output:**

```text
('serving', 'intelligence_reports', '469361d3-732e-45be-b178-e0f3c33ad5ec', 'SELECT')
('serving', 'intelligence_reports', 'aradhya.chouhan@databricks.com', 'SELECT,DELETE,TRUNCATE')
('serving', 'replenishment_recommendations', '469361d3-732e-45be-b178-e0f3c33ad5ec', 'SELECT')
('serving', 'replenishment_recommendations', 'aradhya.chouhan@databricks.com', 'TRUNCATE,DELETE,SELECT')
('serving', 'stockout_risk_scores', '469361d3-732e-45be-b178-e0f3c33ad5ec', 'SELECT')
('serving', 'stockout_risk_scores', 'aradhya.chouhan@databricks.com', 'DELETE,TRUNCATE,SELECT')
```

```python
print("rows per Lakebase table:")
for schema, table in q("""SELECT table_schema, table_name FROM information_schema.tables
                          WHERE table_schema IN ('serving', 'osa_app') ORDER BY 1, 2"""):
    print(f"  {schema}.{table}: {q(f'SELECT count(*) FROM {schema}.{table}')[0][0]:,}")
```

**Output:**

```text
rows per Lakebase table:
  serving.intelligence_reports: 8
  serving.replenishment_recommendations: 1,345
  serving.stockout_risk_scores: 21,971
```
