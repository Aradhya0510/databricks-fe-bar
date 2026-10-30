# Databricks notebook source
# MAGIC %md
# MAGIC # Agents 2/2 · Nightly intelligence briefings (tool-calling agent + MLflow evaluation)
# MAGIC
# MAGIC A tool-calling agent (Claude Sonnet on Databricks Foundation Model APIs) writes one **executive briefing** and one
# MAGIC **regional briefing** per region. It decides which governed tools to call:
# MAGIC
# MAGIC * UC functions — `osa_kpi_summary`, `osa_store_action_queue`, `osa_supplier_watchlist`, `osa_item_risk`,
# MAGIC   `osa_open_purchase_orders` (structured facts, permission-checked);
# MAGIC * the **Knowledge Assistant** (Agent Bricks) over internal SOPs/policies — so recommendations cite the procedure
# MAGIC   that applies (e.g. POL-SUP-003 escalation, GUIDE-DSD-005 DSD eligibility).
# MAGIC
# MAGIC Every run is traced with **MLflow Tracing** and the briefings are scored with `mlflow.genai.evaluate()`:
# MAGIC LLM-judge guidelines + a deterministic scorer that checks the quoted OSA % against the KPI tool output.
# MAGIC Output: `gold_intelligence_reports` (synced to Lakebase for the app's *Briefings* page).

# COMMAND ----------

# MAGIC %pip install -q "mlflow[databricks]>=3.4" openai databricks-sdk>=0.81
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
dbutils.widgets.text("llm_endpoint", "databricks-claude-sonnet-5-5")
dbutils.widgets.text("ka_endpoint", "")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
LLM = dbutils.widgets.get("llm_endpoint")
KA_ENDPOINT = dbutils.widgets.get("ka_endpoint").strip()
S = f"{catalog}.{schema}"

import json, re, time, uuid
import mlflow
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
client = w.serving_endpoints.get_open_ai_client()
me = spark.sql("select current_user()").first()[0]
mlflow.set_experiment(f"/Users/{me}/osa_intelligence_agent")
mlflow.openai.autolog()
as_of = spark.sql(f"SELECT max(date) FROM {S}.gold_osa_kpi_daily").first()[0]
print(f"as-of business date: {as_of}  | LLM: {LLM} | KA endpoint: {KA_ENDPOINT or '(none)'}")

# COMMAND ----------

# MAGIC %md ## Tools

# COMMAND ----------

def _rows(sql, limit=25):
    df = spark.sql(sql).limit(limit).toPandas()
    return json.loads(df.to_json(orient="records", date_format="iso"))

@mlflow.trace(span_type="TOOL")
def kpi_summary(region: str = "ALL"):
    return _rows(f"SELECT * FROM {S}.osa_kpi_summary('{region}')")

@mlflow.trace(span_type="TOOL")
def store_action_queue(store_id: str = "ALL", top_n: int = 10):
    return _rows(f"SELECT * FROM {S}.osa_store_action_queue('{store_id}', {int(top_n)})", 50)

@mlflow.trace(span_type="TOOL")
def region_action_queue(region: str, top_n: int = 10):
    flt = "" if region.upper() == "ALL" else f"WHERE lower(region) = lower('{region}')"
    return _rows(f"""SELECT priority_rank, store_id, region, item_id, item_name, risk_tier, round(risk_score,3) AS risk_score,
                     recommended_action, recommended_qty, revenue_at_risk_3d, rationale
                     FROM {S}.gold_replenishment_recommendations {flt}
                     ORDER BY revenue_at_risk_3d DESC""", int(top_n))

@mlflow.trace(span_type="TOOL")
def supplier_watchlist(region: str = "ALL"):
    return _rows(f"SELECT * FROM {S}.osa_supplier_watchlist('{region}')")

@mlflow.trace(span_type="TOOL")
def item_risk(store_id: str, item_search: str):
    return _rows(f"SELECT * FROM {S}.osa_item_risk('{store_id}', '{item_search}')", 10)

@mlflow.trace(span_type="TOOL")
def action_queue_summary(region: str = "ALL"):
    flt = "" if region == "ALL" else f"WHERE lower(region) = lower('{region}')"
    return _rows(f"""SELECT risk_tier, recommended_action, count(*) AS items, round(sum(revenue_at_risk_3d),0) AS revenue_at_risk_3d
                     FROM {S}.gold_replenishment_recommendations {flt} GROUP BY ALL ORDER BY revenue_at_risk_3d DESC""")

@mlflow.trace(span_type="RETRIEVER")
def search_policies(question: str):
    if not KA_ENDPOINT:
        return [{"note": "knowledge assistant not configured"}]
    resp = client.responses.create(model=KA_ENDPOINT, input=[{"role": "user", "content": question}])
    text = resp.output_text if hasattr(resp, "output_text") else str(resp)
    return [{"answer": text}]

TOOLS = {f.__name__: f for f in [kpi_summary, region_action_queue, store_action_queue, action_queue_summary,
                                 supplier_watchlist, item_risk, search_policies]}

def spec(name, desc, props, req):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req}}}

R = {"type": "string", "description": "West, South, Midwest or ALL"}
TOOL_SPECS = [
    spec("kpi_summary", "OSA %, revenue, lost revenue: last 7 days vs prior 7 days.", {"region": R}, ["region"]),
    spec("action_queue_summary", "Counts and revenue at risk of tonight's alerts by tier and action.", {"region": R}, ["region"]),
    spec("region_action_queue", "Top replenishment actions for a region or ALL regions (highest revenue at risk first).",
         {"region": R, "top_n": {"type": "integer"}}, ["region"]),
    spec("store_action_queue", "Top replenishment actions for one store.",
         {"store_id": {"type": "string"}, "top_n": {"type": "integer"}}, ["store_id"]),
    spec("supplier_watchlist", "Suppliers with the most stockouts caused by late POs in the last 28 days.", {"region": R}, ["region"]),
    spec("item_risk", "Risk details for an item in a store (id or name search).",
         {"store_id": {"type": "string"}, "item_search": {"type": "string"}}, ["store_id", "item_search"]),
    spec("search_policies", "Search internal SOPs, supplier policy, playbooks and memos. Use to cite the procedure "
         "that applies to a recommended action.", {"question": {"type": "string"}}, ["question"]),
]

# COMMAND ----------

# MAGIC %md ## Agent loop

# COMMAND ----------

SYSTEM = """You are the OSA (on-shelf availability) intelligence analyst for a 10-store grocery & general-merchandise
retailer (regions: West=CA, South=TX, Midwest=WI). You write the nightly briefing that leaders read at 7am.
Rules:
- Get every number from tools. Never invent figures. Quote OSA % with two decimals exactly as returned by kpi_summary.
- Always call kpi_summary and action_queue_summary first, then the action queue and supplier watchlist for the scope.
- Call search_policies at least once to cite the internal procedure (document id like POL-SUP-003) behind your
  recommendations.
- Output GitHub-flavoured markdown with these sections: '## Headline' (2 sentences, business impact in $),
  '## KPIs' (table: metric, last 7d, prior 7d, change), '## Top risks tonight' (max 5 bullets: store, item,
  action, qty, $ at risk), '## Supplier watch' (max 3 bullets), '## Recommended actions' (numbered, owner + policy id).
- Max 350 words. Be specific and decisive."""

def text_of(content):
    """Reasoning models return a list of content blocks (reasoning + text); keep only the text."""
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text").strip()
    return (content or "").strip()


@mlflow.trace(span_type="AGENT", name="osa_briefing_agent")
def run_agent(audience: str, region: str, max_steps: int = 10):
    user = (f"Write tonight's {audience} briefing for business date {as_of}. Scope: "
            f"{'all regions' if region == 'ALL' else region + ' region'}.")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    calls = []
    for _ in range(max_steps):
        r = client.chat.completions.create(model=LLM, messages=messages, tools=TOOL_SPECS, max_tokens=2000)
        msg = r.choices[0].message
        if not msg.tool_calls:
            return {"report": text_of(msg.content), "tool_calls": calls}
        messages.append({"role": "assistant", "content": text_of(msg.content),
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            try:
                result = TOOLS[tc.function.name](**args)
            except Exception as e:
                result = {"error": str(e)[:300]}
            calls.append({"tool": tc.function.name, "args": args})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, default=str)[:12000]})
    return {"report": "Agent did not finish within the step budget.", "tool_calls": calls}

# COMMAND ----------

scopes = [("executive", "ALL"), ("regional", "West"), ("regional", "South"), ("regional", "Midwest")]
reports = []
for audience, region in scopes:
    t0 = time.time()
    out = run_agent(audience, region)
    trace_id = mlflow.get_last_active_trace_id()
    reports.append(dict(report_id=f"{as_of}|{audience}|{region}", report_date=as_of, audience=audience, region=region,
                        title=f"{'Executive' if region == 'ALL' else region + ' region'} OSA briefing — {as_of}",
                        markdown=out["report"], tool_calls_json=json.dumps(out["tool_calls"]), model=LLM,
                        trace_id=trace_id, latency_s=round(time.time() - t0, 1)))
    print(f"\n{'=' * 100}\n{reports[-1]['title']}  ({reports[-1]['latency_s']}s, tools: "
          f"{[c['tool'] for c in out['tool_calls']]})\n{'=' * 100}\n{out['report']}")

# COMMAND ----------

import pandas as pd
from pyspark.sql import functions as F
rdf = spark.createDataFrame(pd.DataFrame(reports)).withColumn("generated_at", F.current_timestamp())
spark.sql(f"""CREATE TABLE IF NOT EXISTS {S}.gold_intelligence_reports (
  report_id STRING NOT NULL, report_date DATE, audience STRING, region STRING, title STRING, markdown STRING,
  tool_calls_json STRING, model STRING, trace_id STRING, latency_s DOUBLE, generated_at TIMESTAMP,
  CONSTRAINT gold_intelligence_reports_pk PRIMARY KEY (report_id))
  COMMENT 'Nightly agent-written OSA briefings (executive + per region). Synced to Lakebase for the app.'
  TBLPROPERTIES (delta.enableChangeDataFeed = true)""")
rdf.createOrReplaceTempView("new_reports")
spark.sql(f"""MERGE INTO {S}.gold_intelligence_reports t USING new_reports s ON t.report_id = s.report_id
              WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")
display(spark.sql(f"SELECT report_id, audience, region, latency_s, length(markdown) AS chars FROM {S}.gold_intelligence_reports ORDER BY generated_at DESC LIMIT 8"))

# COMMAND ----------

# MAGIC %md ## Evaluate the briefings (`mlflow.genai.evaluate`)

# COMMAND ----------

from mlflow.genai.scorers import Guidelines, Safety, scorer
from mlflow.entities import Feedback

facts = {r: kpi_summary(r) for _, r in scopes}

@scorer
def osa_pct_grounded(inputs, outputs):
    """Every OSA % quoted for the last 7 days must equal the KPI tool's figure."""
    truth = [x["osa_pct"] for x in facts[inputs["region"]] if x["period"] == "last_7d"]
    if not truth:
        return Feedback(value=False, rationale="no KPI facts")
    want = f"{truth[0]:.2f}"
    ok = want in outputs["report"]
    return Feedback(value=ok, rationale=f"expected last-7d OSA {want}% to appear in the report: {'found' if ok else 'missing'}")

@scorer
def cites_policy(outputs):
    ids = sorted(set(re.findall(r"\b(?:SOP|POL|GUIDE|PLAY|RACI|MEMO|PM|GLOSSARY|FAQ|CONTRACT)-[A-Z0-9-]+", outputs["report"])))
    return Feedback(value=len(ids) > 0, rationale=f"policy ids cited: {ids}")

@scorer
def used_required_tools(outputs):
    used = {c["tool"] for c in outputs["tool_calls"]}
    need = {"kpi_summary", "action_queue_summary", "search_policies"}
    return Feedback(value=need.issubset(used), rationale=f"used={sorted(used)}")

scorers = [
    osa_pct_grounded, cites_policy, used_required_tools, Safety(),
    Guidelines(name="actionable", guidelines="The response must contain specific recommended actions, each with an "
               "owner role and a store or supplier it applies to."),
    Guidelines(name="business_impact", guidelines="The response must quantify business impact in dollars (revenue "
               "at risk or lost revenue)."),
    Guidelines(name="structure", guidelines="The response must contain the sections Headline, KPIs, Top risks tonight, "
               "Supplier watch and Recommended actions."),
]
eval_data = [{"inputs": {"audience": r["audience"], "region": r["region"]},
              "outputs": {"report": r["markdown"], "tool_calls": json.loads(r["tool_calls_json"])}} for r in reports]
results = mlflow.genai.evaluate(data=eval_data, scorers=scorers)
print("aggregate metrics:")
for k, v in sorted(results.metrics.items()):
    print(f"  {k:45s} {v}")

# COMMAND ----------

ev = results.result_df if getattr(results, "result_df", None) is not None else results.tables["eval_results"]
cols = [c for c in ev.columns if c.endswith("/value")]
summary = ev[["request"] + cols].copy() if "request" in ev.columns else ev[cols].copy()
if "request" in summary.columns:
    summary["scope"] = summary.request.apply(lambda x: f"{x.get('audience')}:{x.get('region')}" if isinstance(x, dict) else str(x))
    summary = summary.drop(columns=["request"])
print(summary.astype(str).to_string(index=False))
