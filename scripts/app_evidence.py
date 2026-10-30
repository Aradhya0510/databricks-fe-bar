#!/usr/bin/env python3
"""Exercise the deployed OSA Command Center app end-to-end and record the real API responses.

Calls the app as the signed-in user (workspace OAuth token): health, context, KPIs, action queue (Lakebase),
item lookup (Lakebase latency), store decisions (Lakebase INSERT), briefings, Genie and Supervisor Q&A,
and the governance view. Writes evidence/app/api_responses.md.

Usage: scripts/app_evidence.py [--decide] [--profile fevm-bar]
"""
import json, os, subprocess, sys, time, urllib.request

PROFILE = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "fevm-bar"
DECIDE = "--decide" in sys.argv
OUT = os.path.join(os.path.dirname(__file__), "..", "evidence", "app", "api_responses.md")


def cli(*args):
    r = subprocess.run(["databricks", *args, "-p", PROFILE, "-o", "json"], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


APP = cli("apps", "get", "osa-command-center")
URL = APP["url"].rstrip("/")
TOKEN = cli("auth", "token")["access_token"]


def call(method, path, body=None):
    t0 = time.time()
    req = urllib.request.Request(URL + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read())
            code = r.status
    except urllib.error.HTTPError as e:
        data, code = e.read().decode()[:1000], e.code
    return code, data, round((time.time() - t0) * 1000)


def trim(obj, n=5):
    if isinstance(obj, list):
        return obj[:n] + ([f"... {len(obj) - n} more"] if len(obj) > n else [])
    if isinstance(obj, dict):
        return {k: trim(v, n) for k, v in obj.items()}
    if isinstance(obj, str) and len(obj) > 1500:
        return obj[:1500] + " …"
    return obj


log = [f"# OSA Command Center — live API evidence\n",
       f"*App `{APP['name']}` at {URL} · app status **{APP.get('app_status', {}).get('state')}** · service principal "
       f"`{APP.get('service_principal_client_id')}` · captured {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}*\n",
       "Each section is the real HTTP response of the deployed app (lists truncated to 5 items).\n"]


def record(title, method, path, body=None, note=""):
    code, data, ms = call(method, path, body)
    log.append(f"## {title}\n\n`{method} {path}` → HTTP {code} in {ms} ms. {note}\n")
    if body:
        log.append(f"Request body:\n\n```json\n{json.dumps(body, indent=2)}\n```\n")
    log.append(f"```json\n{json.dumps(trim(data), indent=2, default=str)[:6000]}\n```\n")
    return data


record("Health (Lakebase connection as the app's service principal)", "GET", "/api/health")
record("Context (from Lakebase synced table serving.replenishment_recommendations)", "GET", "/api/context")
record("KPI tiles + 8-week trend (SQL warehouse, governed gold tables)", "GET", "/api/kpis?region=ALL")
queue = record("Action queue — CRITICAL, all stores (Lakebase, joined with latest decision)", "GET", "/api/queue?tier=CRITICAL&limit=20")
record("Item lookup typeahead (Lakebase serving.stockout_risk_scores)", "GET", "/api/items?q=milk&store=CA_1",
       note="`latency_ms` is the Postgres query time measured inside the app.")

if DECIDE and isinstance(queue, list):
    open_items = [r for r in queue if not r.get("decision")]
    if len(open_items) >= 3:
        a, b, c = open_items[:3]
        record("Store decision 1 — APPROVE (INSERT into Lakebase osa_app.replenishment_actions)", "POST", "/api/decision",
               {"rec_id": a["rec_id"], "action": "APPROVE"})
        record("Store decision 2 — OVERRIDE with reason code (> 50% → regional approval flag)", "POST", "/api/decision",
               {"rec_id": b["rec_id"], "action": "OVERRIDE", "final_qty": int(b["recommended_qty"] * 2 + 1),
                "reason_code": "LOCAL_EVENT", "note": "Memorial Day cook-out at the community park"})
        record("Store decision 3 — OVERRIDE without reason code (rejected by SOP-REP-001 rule)", "POST", "/api/decision",
               {"rec_id": c["rec_id"], "action": "OVERRIDE", "final_qty": 5})
        record("Store decision 4 — REJECT", "POST", "/api/decision",
               {"rec_id": c["rec_id"], "action": "REJECT", "note": "item being delisted next week"})
        record("Decisions now stored in Lakebase", "GET", "/api/decisions?limit=10")
        record("Action queue reflects the decisions", "GET", f"/api/queue?store={a['store_id']}&tier=CRITICAL&limit=10")

record("Nightly briefings (Lakebase serving.intelligence_reports)", "GET", "/api/briefings")
record("Ask — Genie mode (shows generated SQL + result)", "POST", "/api/ask",
       {"question": "Which 3 stores lost the most revenue to stockouts in the last 28 days?", "mode": "genie"})
record("Ask — Assistant mode (Supervisor Agent: data + documents)", "POST", "/api/ask",
       {"question": "Which supplier is causing the most stockouts in the South region recently, and what does our "
                    "escalation policy say we must do?", "mode": "assistant"})
record("Governance view (what the app identity is allowed to see)", "GET", "/api/governance")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(log))
print(f"wrote {OUT}")
