# Task `intelligence_briefings` — SUCCESS

*Run 461064574790545 · started 2026-10-31 00:05:38 UTC · 227s*

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
/home/spark-6ab7d940-69e6-47cc-a772-3a/.ipykernel/68/command-8293210456947569-1665605417:16: DeprecationWarning: get_open_ai_client() is deprecated. Please install the databricks-openai package and use 'from databricks_openai import DatabricksOpenAI' instead. See https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_openai.html for more information.
  client = w.serving_endpoints.get_open_ai_client()
If you are using MLflow Tracing, you can migrate your traces to Unity Catalog for unlimited storage, fine-grained access controls, and queryability from notebooks, SQL, and dashboards. Learn more: https://docs.databricks.com/aws/en/mlflow3/genai/tracing/migrate-traces-to-uc
```

```text
as-of business date: 2016-05-23  | LLM: databricks-claude-sonnet-5-5 | KA endpoint: ka-35e9950a-endpoint
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
2026/10/31 00:06:56 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's... Policy: POL-SUP-003."}], input_type=list])"
```

```text

====================================================================================================
Executive OSA briefing — 2016-05-23  (31.8s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
Lost revenue fell to $40,235 in the last 7 days, down $10,332 from $50,567 the week before. Tonight's queue has 1,345 items with $15,649 of 3-day revenue at risk, and 732 of them (about $9,459) are Critical or already out of stock and need Emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.74% | 91.98% | +1.76 pts |
| Revenue | $957,303 | $1,024,462 | -6.6% |
| Lost revenue | $40,235 | $50,567 | -20.4% |
| Lost sales rate | 4.03% | 4.70% | -0.67 pts |
| OOS store-item-days | 9,609 | 12,198 | -21.2% |

## Top risks tonight
- **TX_2, Tortilla Chips #120:** Cycle count for suspected phantom inventory. The system shows 231 units but there are no recent sales. Reorder 24 units if the shelf is empty. $247.84 at risk.
- **CA_3, Cheddar Block #170:** Expedited order of 4 units. Stockout probability is 92%, with 1.53 days of cover against 10.5 units/day of demand. $163.05 at risk. The 4-unit quantity looks low for that demand, so the store should confirm it.
- **WI_2, Cereal #029:** Emergency DSD of 36 units. On hand is 0 and the PO is 1 day overdue. $150.59 at risk.
- **WI_2, Peanut Butter #316:** Emergency DSD of 8 units. The item is out of stock and the PO is 4 days late. $131.08 at risk.
- **TX_3, Pasta #368:** Emergency DSD of 24 units. The item is out of stock and the PO is overdue. $109.39 at risk.

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 394 stockouts, $11,072 lost, 61 still ongoing, average 6.46 days late.
- **SUP018 Polaris Paper & Plastics (tier B):** 288 stockouts, $10,831 lost, 27 ongoing, average 7.07 days late.
- **SUP010 Lakeshore Beverage Group (tier C):** 449 stockouts, the most of any supplier. $10,304 lost, 53 ongoing, average 6.28 days late.

## Recommended actions
1. **Store managers:** Submit Emergency DSD requests for the 732 Critical and out-of-stock items by the 2:00 pm local cut-off for next-morning delivery. Only FOODS_1/2/3 and HOUSEHOLD_1 items are eligible. Approve, Override or Reject each Critical alert within 4 business hours. Policy: GUIDE-DSD-005.
2. **Store associates and managers:** Physically count the 136 phantom-inventory items (shelf and backroom) within 24 hours. The manager adjusts the ERP same day. If the count is 0, place an emergency order immediately. Adjustments of $500 or more at cost need Regional Manager sign-off. Policy: GUIDE-DSD-005.
3. **Category buyers:** Escalate the late POs for the 127 out-of-stock and 92 Critical items on the expedite-and-escalate action. Start with SUP009, SUP018 and SUP010. Policy: POL-SUP-003.
4. **Category buyers:** Escalate HOBBIES and HOUSEHOLD_2 items to the buyer instead of using DSD. Policy: GUIDE-DSD-005.
5. **Regional managers:** Confirm the CA_3 Cheddar quantity and review the two tier-C suppliers (SUP009, SUP010). Policy: POL-SUP-003.
```

```text
2026/10/31 00:07:26 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...n't eligible for DSD."}], input_type=list])"
```

```text

====================================================================================================
West region OSA briefing — 2016-05-23  (30.7s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
West OSA improved to 93.36% and lost revenue fell to $20,105. Tonight's queue still has 579 items with $7,310 of 3-day revenue at risk, and $4,137 of that is in 300 Emergency DSD items.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.36% | 91.76% | +1.60 pts |
| Revenue | $430,923 | $440,442 | -2.2% |
| Lost revenue | $20,105 | $23,599 | -14.8% |
| Lost sales rate | 4.46% | 5.09% | -0.63 pts |
| OOS store-item days | 4,362 | 5,348 | -986 |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** Expedited order, 4 units, $163.05 at risk. Stockout probability is 92% with 1.53 days of cover. Demand is 10.5 units/day, so the buyer should confirm 4 units is enough.
- **CA_3, Northpeak Soup #183:** Verify shelf and expedite the PO, 4 units, $97.30 at risk. The system shows 20 on hand, but 1 PO is overdue.
- **CA_1, Equate Cola 12pk #682:** Emergency DSD, 48 units, $87.09 at risk. On hand is 0 and the 102 units on order are overdue.
- **CA_3, Marketside Trash Bags #249:** Emergency DSD, 24 units, $75.72 at risk. Supplier is CleanWave Home Products.
- **CA_3, Sunny Fields Coffee #574:** Emergency DSD, 20 units, $75.55 at risk.

CA_3 has four of the five top risks.

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 183 stockouts, $5,218 lost, 30 still ongoing, 6.08 days late on average.
- **SUP018 Polaris Paper & Plastics (tier B):** 129 stockouts, $5,158 lost, 11 ongoing, 6.66 days late.
- **SUP010 Lakeshore Beverage Group (tier C):** 181 stockouts, $4,317 lost, 26 ongoing, 6.26 days late.

## Recommended actions
1. **Store managers (CA_1, CA_3):** Submit Emergency DSD for eligible Critical and OOS items by 2:00 pm local so they arrive next morning. Later requests arrive in two days. The 8% premium is charged back to the supplier for late POs. (POL-SUP-003, GUIDE-DSD-005)
2. **Store managers:** For overdue POs with less than 2 days of cover, raise DSD. This covers Cheddar #170 and Soup #183. (POL-SUP-003)
3. **Category buyers:** Escalate SUP009, SUP010 and SUP018 for the late POs. Notify the buyer on every overdue-PO item. (POL-SUP-003)
4. **Store associates and managers:** Physically count the 63 phantom-inventory items within 24 hours. Managers adjust the ERP the same day and order immediately if the count is 0. Adjustments of $500 or more need Regional Manager sign-off within 2 business days. (GUIDE-DSD-005)
5. **Regional Manager:** Move HOBBIES and HOUSEHOLD_2 items to buyer escalation, because they aren't eligible for DSD.
```

```text
2026/10/31 00:07:46 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...YM1EgJxnX/L18hLgRgB'}]}], input_type=list])"
2026/10/31 00:07:54 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's...kgNf1BLqmLVBCj6GAE='}]}], input_type=list])"
2026/10/31 00:08:10 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's... weeks (POL-SUP-003)."}], input_type=list])"
```

```text

====================================================================================================
South region OSA briefing — 2016-05-23  (43.3s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies', 'search_policies', 'search_policies'])
====================================================================================================
## Headline
South OSA improved to 93.61% and lost revenue fell to $10,086, down from $14,204 the week before. Tonight's queue has 372 items with $3,741 of 3-day revenue at risk. $2,082 of that sits in OOS_NOW and CRITICAL items that need emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.61% | 91.19% | +2.42 pts |
| Revenue | $270,426 | $282,414 | -$11,988 (-4.2%) |
| Lost revenue | $10,086 | $14,204 | -$4,118 (-29.0%) |
| Lost sales rate | 3.60% | 4.79% | -1.19 pts |
| OOS store-item-days | 2,776 | 3,797 | -1,021 |

## Top risks tonight
- **TX_2, Great Value Tortilla Chips #120:** Cycle count. The system shows 231 units but there are no recent sales, which points to phantom inventory. Reorder 24 units if the shelf is empty. $247.84 at risk.
- **TX_3, Great Value Pasta #368:** Emergency DSD of 24 units. The item is out of stock and has one overdue PO. $109.39 at risk.
- **TX_2, Northpeak Juice #695:** Emergency DSD of 8 units. On hand is 0 and the supplier PO is 2 days overdue. $53.64 at risk.
- **TX_2, Hearth & Home Ice Cream #661:** Cycle count. The system shows 50 units, but there are no sales against demand of 5.1 units/day. Reorder 48 units if the shelf is empty. $50.40 at risk.
- **TX_2, Equate Black Beans #194:** Expedited order of 4 units. Stockout probability is 86% and the next receipt is delayed. $49.29 at risk.

TX_2 accounts for four of the five top risks.

## Supplier watch
- **SUP018 Polaris Paper & Plastics (tier B):** 94 stockouts, $3,734 lost, 8 ongoing, 7.58 days late on average.
- **SUP016 CleanWave Home Products (tier A):** 121 stockouts, $3,231 lost, 10 ongoing, 6.66 days late on average.
- **SUP010 Lakeshore Beverage Group (tier C):** 123 stockouts, $2,776 lost, 17 ongoing (the most in the region), 6.7 days late on average.

## Recommended actions
1. **TX_3 and TX_2 store managers:** Submit the pasta and juice emergency DSD orders before the 2:00 pm local cut-off for next-morning delivery. Charge the 8% premium back to the supplier (GUIDE-DSD-005, POL-SUP-003).
2. **TX_2 store manager:** Count the shelf and backroom for the tortilla chips and ice cream within 24 hours. Adjust the ERP the same day and order immediately if the count is zero. Adjustments of $500 or more at cost need Regional Manager sign-off within 2 business days (SOP-INV-002).
3. **Category buyers:** Call the account managers at SUP018, SUP016 and SUP010 for any PO 2 or more days late or with under 2 days of cover (POL-SUP-003).
4. **Sourcing manager:** Open sourcing reviews with a corrective action plan due in 5 business days for all three suppliers. Each has far more than 2 stockouts in a week and POs 3 or more days late (POL-SUP-003).
5. **Regional Manager:** Review reallocating volume away from SUP010, a tier C supplier, if its on-time SLA has been missed for 4 consecutive weeks (POL-SUP-003).
```

```text
2026/10/31 00:08:39 WARNING mlflow.utils.autologging_utils: MLflow autologging encountered a warning: "/databricks/python/lib/python3.12/site-packages/pydantic/main.py:475: UserWarning: Pydantic serializer warnings:
  PydanticSerializationUnexpectedValue(Expected `str` - serialized value may not be as expected [field_name='content', input_value=[{'type': 'reasoning', 's... though OSA improved."}], input_type=list])"
```

```text

====================================================================================================
Midwest region OSA briefing — 2016-05-23  (29.8s, tools: ['kpi_summary', 'action_queue_summary', 'region_action_queue', 'supplier_watchlist', 'search_policies'])
====================================================================================================
## Headline
Midwest lost $10,043 in sales over the last 7 days, down from $12,763 the week before, but tonight's queue still has $4,601 of 3-day revenue at risk across 394 items. Emergency DSD items make up $3,241 of that, and WI_2 dominates the top risks.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 94.43% | 93.08% | +1.35 pts |
| Revenue | $255,954 | $301,606 | -15.1% |
| Lost revenue | $10,043 | $12,763 | -21.3% |
| Lost sales rate | 3.78% | 4.06% | -0.28 pts |
| OOS store-item-days | 2,471 | 3,053 | -19.1% |

## Top risks tonight
The queue returned ranks 3, 4, 8, 13 and 20. Ranks 1 and 2 did not appear in the tool output.
- **WI_2, Hearth & Home Cereal #029:** EMERGENCY_DSD, 36 units, $150.59 at risk (0 on hand, PO 1 day overdue).
- **WI_2, Parent's Choice Peanut Butter #316:** EMERGENCY_DSD, 8 units, $131.08 at risk (PO 4 days late).
- **WI_1, Equate Black Beans #282:** EMERGENCY_DSD, 16 units, $78.55 at risk.
- **WI_2, Great Value Dish Soap #488:** EMERGENCY_DSD, 24 units, $69.40 at risk.
- **WI_2, Sunny Fields Canned Tuna #198:** EMERGENCY_DSD, 16 units, $57.46 at risk (PO 3 days overdue).

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 111 stockouts, $3,338 lost, 14 still ongoing, 6.27 days late on average.
- **SUP010 Lakeshore Beverage Group (tier C):** 145 stockouts, $3,211 lost, 10 ongoing, 5.97 days late on average.
- **SUP007 Northstar Snacks & Beverage (tier B):** 119 stockouts, $3,005 lost, 24 ongoing (the most of any supplier), 5.95 days late on average.

## Recommended actions
1. **WI_2 and WI_1 store managers:** Submit the five emergency DSD requests above by 2:00 pm local time so they arrive next morning. A later request arrives in two days. All five items are in eligible departments (FOODS_2 or HOUSEHOLD_1). Order to cover demand until the PO lands plus 3 days, rounded up to the case pack (GUIDE-DSD-005).
2. **Midwest category buyers:** Call suppliers on any PO 2 or more days late or with under 2 days of store cover. Open a sourcing review for SUP009, SUP010 and SUP007, which all exceed the 3+ days late and 2+ stockouts-per-week thresholds (POL-SUP-003).
3. **Store managers:** Complete the 30 phantom-inventory cycle counts ($340 at risk). A store associate counts shelf and backroom within 24 hours, and the store manager adjusts the ERP record the same day. If the count is 0, the manager places an emergency order immediately after the adjustment (GUIDE-DSD-005).
4. **Regional Manager:** Sign off any inventory adjustment of $500 or more at cost within 2 business days (GUIDE-DSD-005).
5. **Regional Manager:** Review why revenue fell 15.1% week over week even though OSA improved.
```

```text
[Trace(trace_id='tr-f16d918c540b25958a601a34e64ec9f5'), Trace(trace_id='tr-fb3ceaab1776a4fd6e105fab27bbf5e3'), Trace(trace_id='tr-15b9465f500cf58527dd014f3753fb69'), Trace(trace_id='tr-7b00cc3ec241801549e7f077a17c612e')]
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
| 2016-05-23\|executive\|ALL | executive | ALL | 31.8 | 2847 |
| 2016-05-23\|regional\|Midwest | regional | Midwest | 29.8 | 2695 |
| 2016-05-23\|regional\|West | regional | West | 30.7 | 2530 |
| 2016-05-23\|regional\|South | regional | South | 43.3 | 2881 |
| 2016-05-22\|regional\|South | regional | South | 26.9 | 2463 |
| 2016-05-22\|regional\|West | regional | West | 33.5 | 2534 |
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
2026/10/31 00:08:57 INFO mlflow.models.evaluation.utils.trace: Auto tracing is temporarily enabled during the model evaluation for computing some metrics and debugging. To disable tracing, call `mlflow.autolog(disable=True)`.
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
[Trace(trace_id='tr-dc00844066a9e93265ea5db44c2b83f0'), Trace(trace_id='tr-972606bbcc072c2a0c78051e9fc567d4'), Trace(trace_id='tr-a54af9fa1dd1707ca59e46e850cb052e'), Trace(trace_id='tr-3346789c05da9ad2cb4b15aec62ccb19')]
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
actionable/value used_required_tools/value structure/value osa_pct_grounded/value safety/value business_impact/value cites_policy/value            scope
             yes                      True             yes                   True          yes                   yes               True    executive:ALL
             yes                      True             yes                   True          yes                   yes               True    regional:West
             yes                      True             yes                   True          yes                   yes               True   regional:South
             yes                      True             yes                   True          yes                   yes               True regional:Midwest
```
