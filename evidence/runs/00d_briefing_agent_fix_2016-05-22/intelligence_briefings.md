# Task `intelligence_briefings` — SUCCESS

*Run 200548869254197 · started 2026-10-30 23:48:21 UTC · 237s*

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
/home/spark-1a03b06a-57fe-4c56-9a8f-96/.ipykernel/67/command-8293210456947569-1665605417:16: DeprecationWarning: get_open_ai_client() is deprecated. Please install the databricks-openai package and use 'from databricks_openai import DatabricksOpenAI' instead. See https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_openai.html for more information.
  client = w.serving_endpoints.get_open_ai_client()
If you are using MLflow Tracing, you can migrate your traces to Unity Catalog for unlimited storage, fine-grained access controls, and queryability from notebooks, SQL, and dashboards. Learn more: https://docs.databricks.com/aws/en/mlflow3/genai/tracing/migrate-traces-to-uc
```

```text
as-of business date: 2016-05-22  | LLM: databricks-claude-sonnet-5-5 | KA endpoint: ka-35e9950a-endpoint
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
2026/10/30 23:49:50 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...rVaBHfokJF4yiszGAE='}]}], input_type=list])"
2026/10/30 23:50:04 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...days (GUIDE-DSD-005)."}], input_type=list])"
```

```text

====================================================================================================
Executive OSA briefing — 2016-05-22  (42.3s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies', 'search_policies'])
====================================================================================================
## Headline
Lost revenue fell to $41,418 in the last 7 days, down from $50,591 the week before. Tonight's queue still has 1,435 store-items with $16,490 of 3-day revenue at risk, and $10,484 of that is in 815 emergency-DSD items.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.77% | 91.96% | +1.81 pts |
| Revenue | $962,773 | $1,036,102 | -7.1% |
| Lost revenue | $41,418 | $50,591 | -18.1% |
| Lost-sales rate | 4.12% | 4.66% | -0.54 pts |
| OOS store-item-days | 9,542 | 12,226 | -22.0% |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** expedited order, 4 units, $156.15 at risk (88% stockout probability, 1.73 days of cover).
- **WI_2, Hearth & Home Cereal #029:** emergency DSD, 36 units, $149.25 at risk (0 on hand, PO overdue).
- **WI_2, Parent's Choice Peanut Butter #316:** emergency DSD, 8 units, $131.74 at risk (out of stock, 51-unit order 3 days overdue).
- **TX_3, Great Value Pasta #368:** emergency DSD, 24 units, $111.23 at risk (out of stock, PO 2 days late).
- **CA_3, Northpeak Soup #183:** expedited order, 4 units, $89.24 at risk (88% stockout probability).

## Supplier watch
- **SUP018 Polaris Paper & Plastics (B):** $11,274 lost revenue, 295 stockouts, 25 still ongoing, 7.25 days late on average.
- **SUP009 Prime Valley Distribution (C):** $11,095 lost revenue, 400 stockouts, 56 still ongoing, 6.5 days late on average.
- **SUP010 Lakeshore Beverage Group (C):** $10,490 lost revenue, 463 stockouts, 54 still ongoing, 6.17 days late on average.

## Recommended actions
1. **Store managers:** submit emergency DSD for the 815 critical and out-of-stock items before the 2:00 pm local cut-off, so they arrive next morning instead of in two days. Only FOODS_1, FOODS_2, FOODS_3 and HOUSEHOLD_1 items are eligible (GUIDE-DSD-005).
2. **Category buyers:** call the account managers at SUP018, SUP009 and SUP010 today. Their POs are 3 or more days late, so open a sourcing review with a corrective action plan due in 5 business days (POL-SUP-003).
3. **Store associates:** physically count the 111 suspected phantom-inventory items ($1,499 at risk) within 24 hours. Store managers then adjust the ERP the same day and place an emergency order for any item that counts at zero (GUIDE-DSD-005).
4. **Replenishment planners:** place the 96 critical expedited orders ($1,381), starting with CA_3 cheddar and soup.
5. **Regional managers:** sign off any inventory adjustment of $500 or more at cost within 2 business days (GUIDE-DSD-005).
```

```text
2026/10/30 23:50:24 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...c1wpTYjcdSn5VMYAQ=='}]}], input_type=list])"
2026/10/30 23:50:37 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...s days (SOP-INV-002).'}], input_type=list])"
```

```text

====================================================================================================
West region OSA briefing — 2016-05-22  (33.5s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies', 'search_policies'])
====================================================================================================
## Headline
West OSA improved to 93.27% from 91.76%, and lost revenue fell $2,632 week over week to $20,942. 624 alerts tonight still put $7,767 of 3-day revenue at risk. 338 of them (173 critical and 165 out of stock now) need Emergency DSD, with $4,499 at risk.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.27% | 91.76% | +1.51 pts |
| Revenue | $432,220 | $443,402 | -$11,182 |
| Lost revenue | $20,942 | $23,574 | -$2,632 |
| Lost sales rate | 4.62% | 5.05% | -0.43 pts |
| OOS store-item days | 4,411 | 5,342 | -931 |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** expedited order, 4 units, $156.15 at risk (88% stockout probability, 1.73 days of cover).
- **CA_3, Northpeak Soup #183:** expedited order, 4 units, $89.24 at risk.
- **CA_1, Equate Cola 12pk #682:** expedited order, 48 units, $84.83 at risk (0 on hand).
- **CA_3, Marketside Trash Bags #489:** expedited order, 12 units, $79.44 at risk (out of stock).
- **CA_3, Sunny Fields Coffee #574:** Emergency DSD, 24 units, $76.14 at risk. The Prime Valley PO is 3 days overdue.

CA_3 has four of the five top items, so it is the store to focus on.

## Supplier watch
- **Polaris Paper & Plastics (SUP018, tier B):** 134 stockouts, $5,248 lost, 13 ongoing, average 6.65 days late.
- **Prime Valley Distribution (SUP009, tier C):** 188 stockouts, $5,224 lost, 31 ongoing (the most of any supplier), average 6.19 days late.
- **Northstar Snacks & Beverage (SUP007, tier B):** 177 stockouts, $4,357 lost, 18 ongoing, average 6.64 days late.

## Recommended actions
1. **Store managers, CA_3 and CA_1:** Submit Emergency DSD for eligible FOODS and HOUSEHOLD_1 items before the 2:00 pm cut-off, so they arrive next morning. Size each order to cover demand until the PO lands plus 3 days (GUIDE-DSD-005).
2. **Category buyers:** Call the account managers for the 117 expedite-and-escalate alerts (65 critical, 52 out of stock now). Where item cover is under 2 days or the PO is 2+ days late, the buyer call is required (POL-SUP-003).
3. **Sourcing:** Open a review with a corrective action plan due in 5 business days for Prime Valley, Polaris and Northstar. Each has POs 3+ days late and 2+ attributed stockouts (POL-SUP-003).
4. **Store associates:** Physically count the 53 suspected phantom items within 24 hours. The store manager adjusts ERP the same day and reorders any item that counts as 0 (SOP-INV-002).
5. **Regional Manager:** Sign off on any adjustment of $500 or more at cost within 2 business days (SOP-INV-002).
```

```text
2026/10/30 23:51:04 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...days (GUIDE-DSD-005)."}], input_type=list])"
```

```text

====================================================================================================
South region OSA briefing — 2016-05-22  (26.9s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
South OSA improved to 93.64%, and lost revenue fell $3,851 to $10,396 week over week. Tonight's queue still has 406 items with $3,890 of 3-day revenue at risk. About $2,412 of that is in emergency DSD items, which are CRITICAL or already out of stock.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.64% | 91.09% | +2.55 pts |
| Revenue | $273,063 | $282,504 | -$9,441 (-3.3%) |
| Lost revenue | $10,396 | $14,247 | -$3,851 (-27.0%) |
| Lost sales rate | 3.67% | 4.80% | -1.13 pts |
| OOS store-item-days | 2,758 | 3,839 | -1,081 |

## Top risks tonight
- **TX_3, Great Value Pasta #368:** OOS now, PO 2 days late. EMERGENCY_DSD, 24 units, $111.23 at risk.
- **TX_3, Mainstays Butter #107:** OOS now, PO 2 days overdue. EMERGENCY_DSD, 24 units, $72.50 at risk.
- **TX_3, Sunny Fields Paper Towels #222:** 0 on hand. EXPEDITED_ORDER, 24 units, $53.54 at risk.
- **TX_2, Northpeak Juice #695:** CRITICAL (98% stockout probability) with an overdue PO. EMERGENCY_DSD, 8 units, $52.90 at risk.
- **TX_2, Hearth & Home Ice Cream #661:** suspected phantom inventory. CYCLE_COUNT, 48 units, $51.17 at risk.

## Supplier watch
- **SUP018 Polaris Paper & Plastics (tier B):** 94 stockouts, $3,876 lost, average 8.0 days late, 5 ongoing.
- **SUP016 CleanWave Home Products (tier A):** 125 stockouts, $3,382 lost, 14 ongoing.
- **SUP010 Lakeshore Beverage Group (tier C):** 128 stockouts, $2,922 lost, 15 ongoing, average 6.79 days late.

## Recommended actions
1. **TX_3 and TX_2 store managers:** Submit emergency DSD for the pasta, butter and juice before the 2:00 pm local cut-off so they arrive tomorrow morning. Later requests take two days. Charge the 8% premium back to the supplier as a late-PO root cause (POL-SUP-003).
2. **Category buyers:** Escalate the 57 late-PO items in the EXPEDITE_PO_AND_ESCALATE queue. Start with SUP018, SUP016 and SUP010 (POL-SUP-003, GUIDE-DSD-005).
3. **Category buyer (household/paper):** Handle the HOUSEHOLD_2 and HOBBIES items through buyer escalation, because DSD isn't allowed for those departments (POL-SUP-003).
4. **TX_2 store manager:** Have an associate count the ice cream, shelf and backroom, within 24 hours. Adjust in ERP the same day. If the count is 0, place an emergency order right away (GUIDE-DSD-005). The same applies to the other 31 phantom flags.
5. **South Regional Manager:** Sign off any adjustment of $500 or more at cost within 2 business days (GUIDE-DSD-005).
```

```text
2026/10/30 23:51:33 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's... Policy: SOP-INV-002.'}], input_type=list])"
```

```text

====================================================================================================
Midwest region OSA briefing — 2016-05-22  (28.5s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
Midwest has 405 store-items in tonight's queue with **$4,834** of 3-day revenue at risk. $3,574 of that is in 254 Emergency DSD items. Lost revenue fell to $10,080 from $12,770 (-21.1%), but late supplier POs are still driving most stockouts.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 94.65% | 93.09% | +1.56 pts |
| Revenue | $257,490 | $310,197 | -17.0% |
| Lost revenue | $10,080 | $12,770 | -21.1% |
| Lost-sales rate | 3.77% | 3.95% | -0.18 pts |
| OOS store-item-days | 2,373 | 3,045 | -22.1% |

## Top risks tonight
- **WI_2, Hearth & Home Cereal #029:** Emergency DSD, 36 units, $149.25 at risk. On-hand is 0 and the PO is overdue.
- **WI_2, Parent's Choice Peanut Butter #316:** Emergency DSD, 8 units, $131.74 at risk. It is out of stock and the 51-unit PO is 3 days overdue.
- **WI_1, Parent's Choice Large Eggs #012:** Emergency DSD, 6 units, $82.88 at risk. It is out of stock and the Golden Prairie Dairy PO is overdue.
- **WI_1, Equate Black Beans #282:** Emergency DSD, 8 units, $77.92 at risk. The system shows 48 units on hand but 100% stockout probability. Verify the stock on the shelf before ordering, because it may be phantom inventory.
- **WI_2, Mainstays Granola Bars #083:** Expedited order, 24 units, $68.66 at risk. Demand is 2.6 units/day.

## Supplier watch
- **SUP009 Prime Valley Distribution (Tier C):** 114 stockouts, $3,426 lost, 14 still ongoing, 6.41 days late on average.
- **SUP010 Lakeshore Beverage Group (Tier C):** 153 stockouts, $3,294 lost, 14 ongoing, 5.78 days late.
- **SUP007 Northstar Snacks & Beverage (Tier B):** 120 stockouts, $3,076 lost, 22 ongoing (the most), 6.11 days late.

## Recommended actions
1. **Store managers (WI_1, WI_2):** Submit the Emergency DSD requests for cereal #029, peanut butter #316 and eggs #012 **before the 2:00 pm local cut-off** for next-morning delivery. Policy: POL-SUP-003 / GUIDE-DSD-005.
2. **WI_1 store manager:** Count shelf and backroom for Black Beans #282 within 24 hours. If the count is zero, order immediately after the ERP adjustment. Policy: SOP-INV-002.
3. **Category buyers:** Place the expedited order for granola bars #083. Call suppliers on the 64 items in "Expedite PO and Escalate", $388 at risk. Policy: POL-SUP-003.
4. **Sourcing:** Open a sourcing review for SUP009, SUP010 and SUP007. All three average more than 5 days late, past the 3+ day trigger. Policy: POL-SUP-003.
5. **Finance and AP:** Charge back the 8% DSD premium to suppliers where a late PO is the cause. Policy: POL-SUP-003.
6. **Store teams:** Cycle-count the 26 phantom-inventory items, $320 at risk, before reordering. Policy: SOP-INV-002.
```

```text
[Trace(trace_id='tr-9fbf99ae6c9b60a476a0a9790b0c2787'), Trace(trace_id='tr-93a82135bc39acbde8d11fa1264dbc04'), Trace(trace_id='tr-c31f0cf0caf2582ed6657d16696e144f'), Trace(trace_id='tr-1772a205592b1bbc26ccbd31726ba5eb')]
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
| 2016-05-22\|regional\|West | regional | West | 33.5 | 2534 |
| 2016-05-22\|regional\|South | regional | South | 26.9 | 2463 |
| 2016-05-22\|regional\|Midwest | regional | Midwest | 28.5 | 2665 |
| 2016-05-22\|executive\|ALL | executive | ALL | 42.3 | 2502 |

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
2026/10/30 23:51:52 INFO mlflow.models.evaluation.utils.trace: Auto tracing is temporarily enabled during the model evaluation for computing some metrics and debugging. To disable tracing, call `mlflow.autolog(disable=True)`.
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
[Trace(trace_id='tr-25031548ef904e548f2fe4f5f03e4932'), Trace(trace_id='tr-5d9ea7d41c2f2a8e91d2a439bbce74b5'), Trace(trace_id='tr-877719c55ac915527ede1d444115300d'), Trace(trace_id='tr-acf94d4e92fd31688b70f3fff71fd7da')]
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
used_required_tools/value business_impact/value safety/value actionable/value structure/value osa_pct_grounded/value cites_policy/value            scope
                     True                   yes          yes              yes             yes                   True               True    executive:ALL
                     True                   yes          yes              yes             yes                   True               True    regional:West
                     True                   yes          yes              yes             yes                   True               True   regional:South
                     True                   yes          yes              yes             yes                   True               True regional:Midwest
```
