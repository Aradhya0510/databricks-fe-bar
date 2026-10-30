#!/usr/bin/env python3
"""Prove UC row filters / column masks by running identical queries as two identities.

  * ADMIN     : the builder's CLI profile
  * PERSONA   : service principal `osa-demo-south-store-manager` (entitlement REGION:South), authenticated with a
                short-lived OAuth secret minted for this check and revoked afterwards.

Writes evidence/governance/persona_check.md.  Usage: scripts/governance_persona_check.py [--profile fevm-bar]
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request

PROFILE = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "fevm-bar"
SP_NAME = "osa-demo-south-store-manager"
S = "serverless_stable_4hkk7k_catalog.osa_retail"
WAREHOUSE = "e0a8cc3b322c1f1d"
OUT = os.path.join(os.path.dirname(__file__), "..", "evidence", "governance", "persona_check.md")

QUERIES = [
    ("Who am I", "SELECT current_user() AS identity"),
    ("Row filter: regional KPI rows visible per region (gold_osa_kpi_daily)",
     f"SELECT region, count(*) AS rows, round(sum(lost_revenue)) AS lost_revenue FROM {S}.gold_osa_kpi_daily GROUP BY region ORDER BY region"),
    ("Row filter: stockout events visible per region (gold_stockout_events)",
     f"SELECT region, count(*) AS events FROM {S}.gold_stockout_events GROUP BY region ORDER BY region"),
    ("Column masks: supplier commercial terms (dim_supplier)",
     f"SELECT supplier_id, supplier_name, late_penalty_pct_of_po, payment_terms, account_manager_email FROM {S}.dim_supplier ORDER BY supplier_id LIMIT 4"),
    ("Column masks: item cost + store manager e-mail",
     f"SELECT i.item_id, i.negotiated_cost_ratio, s.store_id, s.store_manager_email FROM {S}.dim_item i CROSS JOIN {S}.dim_store s "
     f"WHERE i.item_id = 'FOODS_3_090' AND s.store_id IN ('CA_1', 'TX_1') ORDER BY s.store_id"),
    ("No grant: bronze table is not readable by the persona", f"SELECT count(*) AS n FROM {S}.bronze_erp_suppliers"),
]


def cli(*args):
    r = subprocess.run(["databricks", *args, "-p", PROFILE, "-o", "json"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:500])
    return json.loads(r.stdout) if r.stdout.strip() else {}


def host():
    return cli("auth", "describe")["details"]["host"].rstrip("/")


def run_sql(statement, token=None):
    body = {"statement": statement, "warehouse_id": WAREHOUSE, "wait_timeout": "50s"}
    if token is None:
        r = cli("api", "post", "/api/2.0/sql/statements", "--json", json.dumps(body))
    else:
        req = urllib.request.Request(f"{HOST}/api/2.0/sql/statements", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            r = json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            return None, f"HTTP {e.code}: {e.read().decode()[:300]}"
    st = r.get("status", {})
    if st.get("state") != "SUCCEEDED":
        return None, (st.get("error") or {}).get("message", st.get("state"))[:400]
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return [cols] + (r.get("result", {}).get("data_array") or []), None


def md(res, err):
    if err:
        return f"```text\nDENIED / ERROR: {err}\n```"
    head, rows = res[0], res[1:]
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] +
                     ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows])


HOST = host()
sp = cli("service-principals", "list", "--filter", f"displayName eq '{SP_NAME}'")[0]
# Persona needs the SQL entitlement and CAN_USE on the warehouse to run SQL at all
subprocess.run(["databricks", "service-principals", "patch", sp["id"], "-p", PROFILE, "--json", json.dumps({
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [{"op": "add", "path": "entitlements", "value": [{"value": "databricks-sql-access"}]}]})],
    check=True, capture_output=True)
cli("permissions", "update", "warehouses", WAREHOUSE, "--json",
    json.dumps({"access_control_list": [{"service_principal_name": sp["applicationId"], "permission_level": "CAN_USE"}]}))
secret = cli("service-principal-secrets-proxy", "create", sp["id"])
try:
    data = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "all-apis"}).encode()
    req = urllib.request.Request(f"{HOST}/oidc/v1/token", data=data)
    import base64
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sp['applicationId']}:{secret['secret']}".encode()).decode())
    token = json.loads(urllib.request.urlopen(req).read())["access_token"]
    time.sleep(2)
    out = ["# Governance proof: same queries, two identities\n",
           f"*Generated {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} against `{S}` on warehouse `{WAREHOUSE}`.*\n",
           f"* **ADMIN** – the build identity (entitlement `ADMIN`).",
           f"* **PERSONA** – service principal `{SP_NAME}` (`{sp['applicationId']}`), entitlement `REGION:South`, "
           f"SELECT on curated gold/dim tables only.\n",
           "Policies: `fn_region_filter` (row filter on `region`), `fn_mask_commercial_*`, `fn_mask_email` (column masks), "
           "all driven by the `osa_access_entitlements` table.\n"]
    for title, q in QUERIES:
        out.append(f"## {title}\n\n```sql\n{q}\n```\n")
        out.append("**ADMIN:**\n\n" + md(*run_sql(q)) + "\n")
        out.append("**PERSONA (South store manager):**\n\n" + md(*run_sql(q, token)) + "\n")
finally:
    cli("service-principal-secrets-proxy", "delete", sp["id"], secret["id"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(out))
print("\n".join(out))
