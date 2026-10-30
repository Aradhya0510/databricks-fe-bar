#!/usr/bin/env python3
"""Export query results as Markdown evidence.

  briefings   -> evidence/agents/briefings.md        (agent-written reports, as stored in Delta / served from Lakebase)
  lakebase    -> evidence/lakebase/roundtrip.md      (app decisions in Lakebase, read via UC catalog, merged into Delta)
  inventory   -> evidence/data/table_inventory.md    (every table in the schema with row counts, type and origin tag)
  model       -> evidence/ml/model_registry.md       (UC registered model versions + aliases)

Usage: scripts/sql_evidence.py briefings|lakebase|inventory|model [--profile fevm-bar]
"""
import json, os, subprocess, sys, time

PROFILE = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "fevm-bar"
C, SC = "serverless_stable_4hkk7k_catalog", "osa_retail"
S = f"{C}.{SC}"
ROOT = os.path.join(os.path.dirname(__file__), "..", "evidence")
STAMP = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())


def cli(*args):
    r = subprocess.run(["databricks", *args, "-p", PROFILE, "-o", "json"], capture_output=True, text=True, check=True)
    return json.loads(r.stdout) if r.stdout.strip() else {}


def sql(q):
    r = cli("api", "post", "/api/2.0/sql/statements", "--json",
            json.dumps({"statement": q, "warehouse_id": "e0a8cc3b322c1f1d", "wait_timeout": "50s"}))
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(2)
        r = cli("api", "get", f"/api/2.0/sql/statements/{r['statement_id']}")
    if r["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(json.dumps(r["status"])[:400])
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return cols, r.get("result", {}).get("data_array") or []


def md(cols, rows):
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join("" if v is None else str(v).replace("|", "\\|").replace("\n", " ") for v in r) + " |"
                      for r in rows])


def write(rel, lines):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write("\n".join(lines))
    print(f"wrote {p}")


def briefings():
    _, rows = sql(f"""SELECT title, audience, region, model, latency_s, generated_at, tool_calls_json, markdown, trace_id
                      FROM {S}.gold_intelligence_reports ORDER BY report_date DESC,
                      CASE audience WHEN 'executive' THEN 0 ELSE 1 END, region""")
    lines = [f"# Nightly intelligence briefings (agent output)\n",
             f"*Exported {STAMP} from `{S}.gold_intelligence_reports` — the same rows the app serves from Lakebase "
             f"`serving.intelligence_reports`. Each was written by the tool-calling briefing agent; `tools` lists the governed "
             f"tools it chose to call; `trace` is the MLflow trace id.*\n"]
    for title, aud, reg, model, lat, gen, tools, body, trace in rows:
        used = " → ".join(t["tool"] for t in json.loads(tools or "[]"))
        lines += [f"---\n\n## {title}\n", f"*{aud} · {reg} · {model} · {lat}s · generated {gen} · trace `{trace}`*  ",
                  f"*tools: {used}*\n", body, ""]
    write("agents/briefings.md", lines)


def lakebase():
    lines = [f"# Lakebase round-trip evidence\n", f"*{STAMP}*\n",
             "1. Gold Delta tables are **synced** into Lakebase Postgres (`osa_lakebase.serving.*`).",
             "2. The app's service principal **writes** store decisions transactionally into its own Postgres schema "
             "(`osa_app.replenishment_actions`).",
             "3. Because the Lakebase database is registered as Unity Catalog catalog `osa_lakebase`, the nightly job "
             "reads those rows with SQL and MERGEs them into governed Delta (`replenishment_actions`).\n"]
    for title, q in [
        ("Synced serving tables: Delta source vs Lakebase Postgres row counts",
         f"""SELECT 'replenishment_recommendations' AS lakebase_table, (SELECT count(*) FROM {S}.gold_replenishment_recommendations) AS delta_rows,
                    (SELECT count(*) FROM osa_lakebase.serving.replenishment_recommendations) AS postgres_rows
             UNION ALL SELECT 'stockout_risk_scores', (SELECT count(*) FROM {S}.gold_stockout_risk_scores),
                    (SELECT count(*) FROM osa_lakebase.serving.stockout_risk_scores)
             UNION ALL SELECT 'intelligence_reports', (SELECT count(*) FROM {S}.gold_intelligence_reports),
                    (SELECT count(*) FROM osa_lakebase.serving.intelligence_reports)"""),
        ("Decisions written by the app — read live from Postgres through the UC catalog",
         "SELECT action_id, rec_id, action, final_qty, reason_code, note, decided_by, decided_at, recommended_qty, risk_tier "
         "FROM osa_lakebase.osa_app.replenishment_actions ORDER BY decided_at"),
        ("Same decisions after the nightly MERGE into governed Delta",
         f"SELECT action_id, rec_id, action, final_qty, reason_code, decided_by, decided_at, ingested_at FROM {S}.replenishment_actions ORDER BY decided_at"),
        ("Alert response KPI computed from the merged decisions",
         f"""SELECT r.score_date, r.risk_tier, count(*) AS alerts, count(a.action_id) AS actioned
             FROM {S}.gold_replenishment_recommendations r LEFT JOIN {S}.replenishment_actions a ON a.rec_id = r.rec_id
             GROUP BY ALL ORDER BY 1, 2"""),
    ]:
        try:
            lines += [f"## {title}\n", f"```sql\n{q.strip()}\n```\n", md(*sql(q)), ""]
        except Exception as e:
            lines += [f"## {title}\n", f"```text\n{e}\n```\n"]
    write("lakebase/roundtrip.md", lines)


def inventory():
    _, tables = sql(f"SELECT table_name, table_type FROM {C}.information_schema.tables WHERE table_schema = '{SC}' "
                    f"AND table_name NOT LIKE '\\_\\_%' ORDER BY table_name")
    _, tags = sql(f"SELECT table_name, tag_name, tag_value FROM {C}.information_schema.table_tags WHERE schema_name = '{SC}'")
    tagmap = {}
    for t, k, v in tags:
        tagmap.setdefault(t, {})[k] = v
    rows = []
    for t, typ in tables:
        try:
            n = sql(f"SELECT count(*) FROM {S}.{t}")[1][0][0]
        except Exception:
            n = "n/a"
        tg = tagmap.get(t, {})
        rows.append([t, typ, n, tg.get("layer", ""), tg.get("osa_data_origin", ""), tg.get("domain", "")])
    write("data/table_inventory.md", [f"# Table inventory — `{S}`\n", f"*{STAMP}; row counts via SQL warehouse; tags from "
                                      f"information_schema.table_tags.*\n",
                                      md(["table", "type", "rows", "layer", "osa_data_origin", "domain"], rows)])


def model():
    name = f"{S}.osa_stockout_risk"
    rm = cli("registered-models", "get", name, "--include-aliases")
    vers = cli("model-versions", "list", name)
    vers = vers if isinstance(vers, list) else vers.get("model_versions", [])
    lines = [f"# Unity Catalog model registry — `{name}`\n", f"*{STAMP}*\n", f"**Description:** {rm.get('comment')}\n",
             f"**Aliases:** " + ", ".join(f"`@{a['alias_name']}` → v{a['version_num']}" for a in rm.get("aliases", [])) + "\n",
             md(["version", "status", "run_id", "created_at", "source"],
                [[v.get("version"), v.get("status"), v.get("run_id"),
                  time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(v.get("created_at", 0) / 1000)), v.get("source", "")[:90]]
                 for v in sorted(vers, key=lambda v: v.get("version", 0))])]
    write("ml/model_registry.md", lines)


{"briefings": briefings, "lakebase": lakebase, "inventory": inventory, "model": model}[sys.argv[1]]()
