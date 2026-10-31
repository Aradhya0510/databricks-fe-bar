# Task `intelligence_briefings` — SUCCESS

*Run 1089221284268949 · started 2026-10-31 00:32:20 UTC · 203s*

# Agents 2/2 · Nightly intelligence briefings (tool-calling agent + MLflow evaluation)

A tool-calling agent (Claude Sonnet on Databricks Foundation Model APIs) writes one **executive briefing** and one
**regional briefing** per region. It decides which governed tools to call:

* UC functions — `osa_kpi_summary`, `osa_store_action_queue`, `osa_supplier_watchlist`, `osa_item_risk`,
  `osa_open_purchase_orders` (structured facts, permission-checked);
* the **Knowledge Assistant** (Agent Bricks) over internal SOPs/policies — so recommendations cite the procedure
  that applies (e.g. POL-SUP-003 escalation, GUIDE-DSD-005 DSD eligibility).

Every run is traced with **MLflow Tracing** and the briefings are scored with `mlflow.genai.evaluate()`:
LLM-judge guidelines + a deterministic scorer that checks the quoted OSA % against the KPI tool output.
Output: `gold_intelligence_reports` (synced to Lakebase for the app's *Briefings* page).

```python
%pip install -q "mlflow[databricks]>=3.4" openai databricks-sdk>=0.81
%restart_python
```

**Output:**

```text
Note: you may need to restart the kernel using %restart_python or dbutils.library.restartPython() to use updated packages.
```

```python
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
```

**Output:**

```text
/home/spark-ce1af1f1-c096-447d-8efa-b1/.ipykernel/67/command-8293210456947569-1665605417:16: DeprecationWarning: get_open_ai_client() is deprecated. Please install the databricks-openai package and use 'from databricks_openai import DatabricksOpenAI' instead. See https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_openai.html for more information.
  client = w.serving_endpoints.get_open_ai_client()
If you are using MLflow Tracing, you can migrate your traces to Unity Catalog for unlimited storage, fine-grained access controls, and queryability from notebooks, SQL, and dashboards. Learn more: https://docs.databricks.com/aws/en/mlflow3/genai/tracing/migrate-traces-to-uc
```

```text
as-of business date: 2016-05-24  | LLM: databricks-claude-sonnet-5-5 | KA endpoint: ka-35e9950a-endpoint
```

## Tools

```python
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
```

## Agent loop

```python
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
```

```python
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
```

**Output:**

```text
2026/10/31 00:33:25 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...-off (GUIDE-DSD-005)."}], input_type=list])"
```

```text

====================================================================================================
Executive OSA briefing — 2016-05-24  (28.6s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
OSA improved to 93.79% and lost revenue fell to $39,174, down $11,504 (-22.7%) week over week. Tonight's queue still has $13,899 of 3-day revenue at risk across 1,168 items. Emergency DSD accounts for $8,808 of that.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.79% | 92.00% | +1.79 pts |
| Revenue | $953,628 | $1,020,469 | -$66,841 (-6.5%) |
| Lost revenue | $39,174 | $50,678 | -$11,504 (-22.7%) |
| Lost sales rate | 3.95% | 4.73% | -0.78 pts |
| OOS store-item-days | 9,539 | 12,183 | -2,644 |

Total revenue is down 6.5% even though availability improved, so the cause is probably demand or traffic rather than stockouts.

## Top risks tonight
- **TX_2, Great Value Tortilla Chips #120:** expedited order of 24 units, $237.05 at risk. It has 0 on hand despite 217 on order, so chase the inbound PO.
- **CA_3, Equate Cheddar Block #170:** emergency DSD of 4 units, $174.59 at risk. Stockout probability is 99%.
- **WI_2, Hearth & Home Cereal #029:** emergency DSD of 36 units, $149.98 at risk. The supplier PO is 2 days overdue.
- **WI_2, Parent's Choice Peanut Butter #316:** emergency DSD of 8 units, $131.08 at risk. The PO is 5 days late.
- **TX_3, Great Value Pasta #368:** emergency DSD of 24 units, $109.39 at risk.

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 383 stockouts, $10,897 lost, 58 still ongoing, 6.48 days late on average.
- **SUP010 Lakeshore Beverage Group (tier C):** 433 stockouts (the most of any supplier), $10,161 lost, 59 ongoing.
- **SUP018 Polaris Paper & Plastics (tier B):** $10,231 lost, 6.94 days late on average.

## Recommended actions
1. **Store managers (CA_3, WI_2, TX_3):** Submit emergency DSD requests for the 630 CRITICAL and OOS_NOW items before the 2:00 pm cut-off. Later requests arrive in two days. Only FOODS and HOUSEHOLD_1 items are eligible, and the cost is an 8% premium plus a $45 per store per day fee (GUIDE-DSD-005).
2. **Category buyers:** Make the call on late POs that are 2 or more days overdue, and open a sourcing review for SUP009, SUP010 and SUP018 (POL-SUP-003). This covers 187 items in the expedite-and-escalate and verify-shelf tiers.
3. **TX_2 store manager:** Trace the 217 units on order for Tortilla Chips #120 and place the 24-unit expedited order (POL-SUP-003).
4. **Store associates:** Physically count the 151 phantom-inventory items (OOS_PHANTOM, $1,826 at risk) within 24 hours. Managers adjust ERP the same day. If a count is zero, they place an emergency order. Adjustments of $500 or more at cost need Regional Manager sign-off (GUIDE-DSD-005).
```

```text
2026/10/31 00:33:55 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...so check it directly."}], input_type=list])"
```

```text

====================================================================================================
West region OSA briefing — 2016-05-24  (29.9s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
West OSA improved to 93.53%, and lost revenue fell to $18,952 from $24,113 the prior week. 490 items are still flagged tonight, with $6,082 of 3-day revenue at risk. 257 of those items, worth $3,753, need emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.53% | 91.71% | +1.82 pts |
| Revenue | $430,661 | $435,934 | -$5,273 (-1.2%) |
| Lost revenue | $18,952 | $24,113 | -$5,161 (-21.4%) |
| Lost sales rate | 4.22% | 5.24% | -1.02 pts |
| OOS store-item-days | 4,255 | 5,390 | -1,135 |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** emergency DSD, 4 units, $174.59 at risk. It has 0 on hand and demand of 10.4 units/day.
- **CA_3, Northpeak Soup #183:** emergency DSD, 16 units, $99.91 at risk. It has an overdue PO.
- **CA_1, Equate Cola 12pk #682:** emergency DSD, 48 units, $89.10 at risk. Its PO is 1 day overdue.
- **CA_3, Great Value Dish Soap #488:** emergency DSD, 24 units, $75.37 at risk. Its supplier delivery is overdue.
- **CA_1, Sunny Fields Coffee #574:** emergency DSD, 12 units, $68.57 at risk. It is out of stock and its PO is 11 days overdue from Prime Valley.

CA_3 has three of the five top items.

## Supplier watch
- **Prime Valley Distribution (SUP009, tier C):** 177 stockouts, $5,103 lost, 32 still ongoing, 6.12 days late on average.
- **Polaris Paper & Plastics (SUP018, tier B):** 125 stockouts, $4,926 lost, 9 ongoing, 6.71 days late on average.
- **Lakeshore Beverage Group (SUP010, tier C):** 172 stockouts, $4,268 lost, 23 ongoing, 6.33 days late on average.

## Recommended actions
1. **CA_3 and CA_1 store managers:** Submit the five emergency DSD requests above before the 2:00 pm local cut-off to get next-morning delivery. All five items are in eligible departments (FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1). Size each order to cover demand until the PO lands plus 3 days, rounded up to case pack (POL-SUP-003, GUIDE-DSD-005).
2. **West category buyers:** Escalate the 92 late-PO items in the queue (61 out of stock, 26 critical, 5 high) and charge the 8% DSD premium back to the supplier. Start with Prime Valley's 32 ongoing stockouts and the 11-day overdue coffee PO (POL-SUP-003).
3. **Store managers:** Have associates physically count the 74 phantom-inventory items ($944 at risk) within 24 hours. Adjust the ERP the same day, and order immediately if the count is 0. Adjustments of $500 or more at cost need Regional Manager sign-off within 2 business days (GUIDE-DSD-005).
4. **Regional supply lead:** Review the corrective-action plans for Prime Valley and Lakeshore (both tier C) under POL-SUP-003. The policy search did not return the full escalation ladder, so check it directly.
```

```text
2026/10/31 00:34:20 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...ckouts (POL-SUP-003)."}], input_type=list])"
```

```text

====================================================================================================
South region OSA briefing — 2016-05-24  (25.3s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
South OSA improved to 93.75% and lost revenue fell to $9,726, down $4,255 from the prior week. Tonight's queue still has 336 alerts with about $3,474 of 3-day revenue at risk, and 113 of them are out-of-stock items that need Emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.75 | 91.34 | +2.41 pts |
| Revenue | $269,466 | $283,516 | -$14,050 (-5.0%) |
| Lost revenue | $9,726 | $13,981 | -$4,255 (-30.4%) |
| Lost sales rate | 3.48% | 4.70% | -1.22 pts |
| OOS store-item-days | 2,718 | 3,736 | -1,018 |

## Top risks tonight
- **TX_2, Great Value Tortilla Chips #120:** Expedited order, 24 units, $237.05 at risk. It has 0 on hand despite 217 on order, so chase that PO.
- **TX_3, Great Value Pasta #368:** Emergency DSD, 24 units, $109.39 at risk. One PO is overdue.
- **TX_1, Marketside Surface Cleaner #497:** Expedited order, 8 units, $108.71 at risk. Order from Polaris Paper & Plastics.
- **TX_2, Equate Black Beans #194:** Emergency DSD, 8 units, $56.35 at risk. Stockout probability is 97%.
- **TX_2, Northpeak Juice #695:** Emergency DSD, 8 units, $53.73 at risk. Its PO is 3 days late.

TX_2 accounts for three of the five top risks.

## Supplier watch
- **Polaris Paper & Plastics (SUP018, tier B):** 85 stockouts, $3,459 lost, 4 ongoing, 7.05 days late on average.
- **CleanWave Home Products (SUP016, tier A):** 116 stockouts, $3,128 lost, 8 ongoing.
- **Lakeshore Beverage Group (SUP010, tier C):** 118 stockouts, $2,779 lost, 18 ongoing, the most of any supplier. It has the most stockouts of the three.

## Recommended actions
1. **TX_2, TX_3 store managers:** Submit the Emergency DSD requests (pasta, black beans, juice) by 2:00 pm local so they arrive next morning. Later requests take two days, and DSD carries an 8% premium plus a $45 flat fee per store per day (GUIDE-DSD-005).
2. **Category buyers:** Call the buyer on any PO that is 2 or more days late, which includes the Northpeak Juice PO. Open a sourcing review for Polaris, CleanWave and Lakeshore, since each has 2 or more attributed stockouts in a week (POL-SUP-003).
3. **TX_2 and TX_1 managers:** Place the expedited orders for tortilla chips and surface cleaner, and confirm the delivery date of the 217 units on order for the chips (POL-SUP-003).
4. **Store associates, with managers:** Cycle-count the 39 phantom-inventory items within 24 hours. The manager adjusts the ERP record the same day and orders immediately if the count is 0 (GUIDE-DSD-005).
5. **Regional ops lead:** Review the South supplier tiers. Polaris, CleanWave and Lakeshore each have large late-PO losses, and CleanWave is tier A despite 116 stockouts (POL-SUP-003).
```

```text
2026/10/31 00:34:40 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...zLh1EDqOquxQou3GAE='}]}], input_type=list])"
2026/10/31 00:34:59 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...SUP010 (POL-SUP-003)."}], input_type=list])"
```

```text

====================================================================================================
Midwest region OSA briefing — 2016-05-24  (39.1s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies', 'search_policies'])
====================================================================================================
## Headline
Midwest OSA improved to 94.22% and lost revenue fell to $10,496, down $2,088 from the prior 7 days. Tonight's queue still has 342 items with $4,343 of 3-day revenue at risk, and 201 of those are OOS_NOW or CRITICAL items routed to Emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 94.22% | 93.08% | +1.14 pts |
| Revenue | $253,501 | $301,019 | -$47,518 (-15.8%) |
| Lost revenue | $10,496 | $12,584 | -$2,088 (-16.6%) |
| Lost-sales rate | 3.98% | 4.01% | -0.03 pts |
| OOS store-item-days | 2,566 | 3,057 | -491 |

Revenue fell almost as much as lost revenue, so part of the lost-revenue improvement may come from lower sales, not just better availability.

## Top risks tonight
- **WI_2, Hearth & Home Cereal #029:** Emergency DSD, 36 units, $149.98 at risk. It is CRITICAL with 0 on hand and a PO 2 days overdue.
- **WI_2, Parent's Choice Peanut Butter #316:** Emergency DSD, 8 units, $131.08 at risk. It is out of stock and the PO is 5 days late.
- **WI_1, Equate Black Beans #282:** Emergency DSD, 16 units, $78.62 at risk. It is out of stock and the PO is 3 days late.
- **WI_2, Mainstays Rice #251:** Expedited order, 16 units, $72.67 at risk.
- **WI_2, Great Value Dish Soap #488:** Emergency DSD, 24 units, $70.54 at risk. The PO is 2 days overdue.

WI_2 accounts for four of the five top items.

## Supplier watch
- **SUP009 Prime Valley Distribution (Tier C):** 110 stockouts, $3,290 lost, 15 still ongoing, average 6.38 days late.
- **SUP010 Lakeshore Beverage Group (Tier C):** 143 stockouts, $3,114 lost, 18 still ongoing, average 5.8 days late.
- **SUP007 Northstar Snacks & Beverage (Tier B):** 113 stockouts, $2,992 lost, 21 ongoing (the most in the region), average 6.04 days late.

## Recommended actions
1. **WI_2 and WI_1 store managers:** Submit the Emergency DSD orders above before the 2:00 pm local cut-off for next-morning delivery. All four items are in eligible departments (GUIDE-DSD-005).
2. **Category buyers:** Call the supplier account managers for the POs that are 2 or more days late, including the cereal, peanut butter, black beans and dish soap POs. Open a sourcing review for any supplier at 3+ days late or with 2+ stockouts in a week. SUP009, SUP010 and SUP007 all qualify on average lateness (late-PO escalation ladder; the search did not return its document ID).
3. **Procurement:** Charge the 8% Emergency DSD premium back to suppliers where a late PO is the root cause (POL-SUP-003).
4. **Store associates:** Physically count the 38 suspected-phantom items ($536 at risk) within 24 hours. Store managers adjust the ERP the same day and reorder if the count is zero. Adjustments of $500 or more at cost need Regional Manager sign-off within 2 business days (phantom-inventory cycle count procedure; the search did not return its document ID).
5. **Regional Manager:** Review Tier C status for SUP009 and SUP010 (POL-SUP-003).
```

```text
[Trace(trace_id='tr-0e52cc9f8c62d05a0d3e4df4865b03d8'), Trace(trace_id='tr-c6d00e561b3614b3f75d7b54c1570190'), Trace(trace_id='tr-2a4bb4d185bc3bb6c7ea69d98826e2a7'), Trace(trace_id='tr-a4b93621116799d7c81a53e91a68de6b')]
```

```python
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
```

**Output:**

| report_id | audience | region | latency_s | chars |
|---|---|---|---|---|
| 2016-05-24\|regional\|West | regional | West | 29.9 | 2701 |
| 2016-05-24\|regional\|Midwest | regional | Midwest | 39.1 | 2925 |
| 2016-05-24\|executive\|ALL | executive | ALL | 28.6 | 2600 |
| 2016-05-24\|regional\|South | regional | South | 25.3 | 2682 |
| 2016-05-23\|regional\|Midwest | regional | Midwest | 29.8 | 2695 |
| 2016-05-23\|executive\|ALL | executive | ALL | 31.8 | 2847 |
| 2016-05-23\|regional\|South | regional | South | 43.3 | 2881 |
| 2016-05-23\|regional\|West | regional | West | 30.7 | 2530 |

## Evaluate the briefings (`mlflow.genai.evaluate`)

```python
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
```

**Output:**

```text
2026/10/31 00:35:12 INFO mlflow.models.evaluation.utils.trace: Auto tracing is temporarily enabled during the model evaluation for computing some metrics and debugging. To disable tracing, call `mlflow.autolog(disable=True)`.
```

```text
Evaluating:   0%|          | 0/4 [Elapsed: 00:00, Remaining: ?]
```

```text
<IPython.core.display.HTML object>
```

```text
aggregate metrics:
  actionable/mean                               1.0
  business_impact/mean                          1.0
  cites_policy/mean                             1.0
  osa_pct_grounded/mean                         1.0
  safety/mean                                   1.0
  structure/mean                                1.0
  used_required_tools/mean                      1.0
```

```text
[Trace(trace_id='tr-1c33d889fe87666dbcdc843cbaf00d49'), Trace(trace_id='tr-77a0ea74ecd53cabfec68a1dcdfbe521'), Trace(trace_id='tr-c00399913755d30071e74af040c1e3b9'), Trace(trace_id='tr-c130106d01c617af3ef6f145fa4281ed')]
```

```python
ev = results.result_df if getattr(results, "result_df", None) is not None else results.tables["eval_results"]
cols = [c for c in ev.columns if c.endswith("/value")]
summary = ev[["request"] + cols].copy() if "request" in ev.columns else ev[cols].copy()
if "request" in summary.columns:
    summary["scope"] = summary.request.apply(lambda x: f"{x.get('audience')}:{x.get('region')}" if isinstance(x, dict) else str(x))
    summary = summary.drop(columns=["request"])
print(summary.astype(str).to_string(index=False))
```

**Output:**

```text
business_impact/value actionable/value used_required_tools/value cites_policy/value safety/value structure/value osa_pct_grounded/value            scope
                  yes              yes                      True               True          yes             yes                   True    executive:ALL
                  yes              yes                      True               True          yes             yes                   True    regional:West
                  yes              yes                      True               True          yes             yes                   True   regional:South
                  yes              yes                      True               True          yes             yes                   True regional:Midwest
```
