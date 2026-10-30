#!/usr/bin/env python3
"""Create or update the OSA Genie Agent (serialized space v2) via the Databricks CLI.

Usage: scripts/genie_space.py [create|update SPACE_ID] [--profile fevm-bar]
"""
import hashlib, json, subprocess, sys

PROFILE = "fevm-bar"
C, S = "serverless_stable_4hkk7k_catalog", "osa_retail"
T = lambda t: f"{C}.{S}.{t}"
WAREHOUSE = "e0a8cc3b322c1f1d"


def hid(text):  # deterministic 32-hex ids so re-runs are idempotent
    return hashlib.md5(text.encode()).hexdigest()


def cols(*specs):
    out = []
    for name, desc, syn, *flags in specs:
        c = {"column_name": name}
        if desc:
            c["description"] = [desc]
        if syn:
            c["synonyms"] = syn
        if "entity" in flags:
            c["enable_entity_matching"] = True
            c["enable_format_assistance"] = True
        out.append(c)
    return sorted(out, key=lambda c: c["column_name"])


tables = [
    {"identifier": T("gold_osa_kpi_daily"), "column_configs": cols(
        ("osa_pct", "On-shelf availability % for the store x department x day", ["availability", "OSA", "in-stock rate"]),
        ("lost_revenue", "Revenue lost to stockouts in USD", ["lost sales", "missed sales"]),
        ("lost_sales_rate_pct", "Lost revenue as % of revenue + lost revenue", ["lost sales rate"]),
        ("region", "West = California, South = Texas, Midwest = Wisconsin", None, "entity"),
        ("dept_id", "Department: FOODS_1 fresh & dairy, FOODS_2 pantry, FOODS_3 snacks & beverages, HOBBIES_1/2, HOUSEHOLD_1/2", ["department"], "entity"),
        ("store_id", "Store id e.g. CA_1, TX_2, WI_3", ["store"], "entity"))},
    {"identifier": T("gold_stockout_events"), "column_configs": cols(
        ("root_cause", "SUPPLIER_DELAY, PHANTOM_INVENTORY, DEMAND_SPIKE, UNEXPLAINED, NO_OPS_DATA", ["cause", "reason"], "entity"),
        ("oos_days", "Duration of the stockout in days", ["duration"]),
        ("lost_revenue", "Revenue lost during the stockout (USD)", ["lost sales"]),
        ("is_ongoing", "Still out of stock on the latest date", ["open stockout", "current stockout"]))},
    {"identifier": T("gold_supplier_performance_weekly"), "column_configs": cols(
        ("on_time_pct", "% of POs due that week received on time", ["OTIF", "on-time rate"]),
        ("attributed_stockouts", "Stockouts caused by this supplier's late POs that week", None),
        ("supplier_name", None, ["vendor"], "entity"))},
    {"identifier": T("gold_stockout_risk_scores"), "column_configs": cols(
        ("risk_score", "Model probability of going out of stock in the next 3 days", ["stockout probability", "risk"]),
        ("risk_tier", "CRITICAL >= 0.60, HIGH >= 0.35, WATCH >= 0.15, OK; OOS_NOW / OOS_PHANTOM = already out of stock", None, "entity"),
        ("revenue_at_risk_3d", "Expected revenue at risk over the next 3 days (USD)", ["revenue at risk", "exposure"]))},
    {"identifier": T("gold_replenishment_recommendations"), "column_configs": cols(
        ("recommended_action", "EXPEDITED_ORDER, EMERGENCY_DSD, EXPEDITE_PO_AND_ESCALATE, CYCLE_COUNT", ["action"], "entity"),
        ("rationale", "GenAI one-line explanation for the store manager", None))},
    {"identifier": T("dim_item"), "column_configs": cols(("item_name", None, ["product", "sku name"], "entity"))},
    {"identifier": T("dim_store"), "column_configs": cols(("city", None, None, "entity"))},
    {"identifier": T("dim_supplier"), "column_configs": cols(("reliability_tier", "A best, C worst", ["tier"], "entity"))},
    {"identifier": T("gold_store_item_daily"), "column_configs": cols(
        ("is_oos", "Inferred out-of-stock day", ["stockout", "out of stock"]),
        ("units", "Units sold that day", ["sales units", "quantity sold"]))},
]
tables.sort(key=lambda t: t["identifier"])

text = [
    "This agent covers on-shelf availability (OSA) for a 10-store grocery and general-merchandise retailer "
    "(stores CA_1-CA_4 West, TX_1-TX_3 South, WI_1-WI_3 Midwest). Sales are real Walmart M5 data 2011-01-29 to "
    "2016-05-22; inventory, POs and suppliers are synthetic. 'Today' means the latest date in the data, not current_date().",
    "OSA % must be computed as 100 * (1 - SUM(oos_store_items) / SUM(active_store_items)) from gold_osa_kpi_daily; never average osa_pct.",
    "'Last week' = the 7 days ending at the latest date in gold_osa_kpi_daily; 'prior week' = the 7 days before that.",
    "Lost sales / lost revenue questions use lost_revenue (USD). Revenue uses revenue (USD).",
    "Stockout counts and root causes use gold_stockout_events (one row per stockout). Only events with start_date >= '2015-11-25' have root-cause data; NO_OPS_DATA means earlier.",
    "Supplier performance uses gold_supplier_performance_weekly; on_time_pct is per week, aggregate with SUM(on_time_pct*pos_received)/SUM(pos_received).",
    "Tonight's alerts, risk and recommended orders use gold_replenishment_recommendations (action queue) or gold_stockout_risk_scores (all items).",
    "Department names: FOODS_1 = Fresh & Dairy, FOODS_2 = Pantry, FOODS_3 = Snacks & Beverages, HOBBIES_1 = Toys & Crafts, "
    "HOBBIES_2 = Party & Seasonal, HOUSEHOLD_1 = Cleaning & Paper, HOUSEHOLD_2 = Home Goods.",
    "Round money to whole dollars and percentages to 2 decimals.",
]

joins = [
    ("gold_stockout_events", "dim_supplier", "`gold_stockout_events`.`supplier_id` = `dim_supplier`.`supplier_id`", "MANY_TO_ONE"),
    ("gold_stockout_events", "dim_item", "`gold_stockout_events`.`item_id` = `dim_item`.`item_id`", "MANY_TO_ONE"),
    ("gold_osa_kpi_daily", "dim_store", "`gold_osa_kpi_daily`.`store_id` = `dim_store`.`store_id`", "MANY_TO_ONE"),
    ("gold_store_item_daily", "dim_item", "`gold_store_item_daily`.`item_id` = `dim_item`.`item_id`", "MANY_TO_ONE"),
]

examples = [
    ("What was on-shelf availability by region last week vs the prior week?",
     f"""WITH mx AS (SELECT max(date) d FROM {T('gold_osa_kpi_daily')})
SELECT region, CASE WHEN date > mx.d - INTERVAL 7 DAYS THEN 'last_week' ELSE 'prior_week' END AS period,
       round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2) AS osa_pct, round(sum(lost_revenue)) AS lost_revenue
FROM {T('gold_osa_kpi_daily')} CROSS JOIN mx WHERE date > mx.d - INTERVAL 14 DAYS
GROUP BY region, 2 ORDER BY region, period"""),
    ("Which stores lost the most revenue to stockouts in the last 28 days?",
     f"""SELECT store_id, region, round(sum(lost_revenue)) AS lost_revenue,
       round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2) AS osa_pct
FROM {T('gold_osa_kpi_daily')} WHERE date > (SELECT max(date) FROM {T('gold_osa_kpi_daily')}) - INTERVAL 28 DAYS
GROUP BY store_id, region ORDER BY lost_revenue DESC"""),
    ("Which suppliers caused the most stockouts in the last 4 weeks?",
     f"""SELECT s.supplier_name, s.reliability_tier, count(*) AS stockouts, round(sum(e.lost_revenue)) AS lost_revenue
FROM {T('gold_stockout_events')} e JOIN {T('dim_supplier')} s ON e.supplier_id = s.supplier_id
WHERE e.root_cause = 'SUPPLIER_DELAY' AND e.start_date > (SELECT max(end_date) FROM {T('gold_stockout_events')}) - INTERVAL 28 DAYS
GROUP BY ALL ORDER BY lost_revenue DESC LIMIT 10"""),
    ("What are the top 10 critical alerts tonight by revenue at risk?",
     f"""SELECT store_id, item_name, risk_tier, round(risk_score, 3) AS risk_score, recommended_action, recommended_qty, revenue_at_risk_3d
FROM {T('gold_replenishment_recommendations')} WHERE risk_tier = 'CRITICAL' ORDER BY revenue_at_risk_3d DESC LIMIT 10"""),
]

sample_q = ["What was on-shelf availability by region last week?", "Which stores lost the most revenue to stockouts this month?",
            "Which suppliers caused the most stockouts in the last 4 weeks?", "How many critical alerts are there tonight by store?",
            "What share of stockouts is phantom inventory vs supplier delay?"]

benchmarks = [
    ("What was the overall on-shelf availability last week?",
     f"SELECT round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2) AS osa_pct FROM {T('gold_osa_kpi_daily')} "
     f"WHERE date > (SELECT max(date) FROM {T('gold_osa_kpi_daily')}) - INTERVAL 7 DAYS"),
    ("How much revenue was lost to stockouts in the South region in the last 28 days?",
     f"SELECT round(sum(lost_revenue)) AS lost_revenue FROM {T('gold_osa_kpi_daily')} WHERE region = 'South' "
     f"AND date > (SELECT max(date) FROM {T('gold_osa_kpi_daily')}) - INTERVAL 28 DAYS"),
    ("How many stockout events by root cause since 2015-11-25?",
     f"SELECT root_cause, count(*) AS events FROM {T('gold_stockout_events')} WHERE start_date >= '2015-11-25' GROUP BY root_cause ORDER BY events DESC"),
    ("Which department has the lowest availability in the last 7 days?",
     f"SELECT dept_id, round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2) AS osa_pct FROM {T('gold_osa_kpi_daily')} "
     f"WHERE date > (SELECT max(date) FROM {T('gold_osa_kpi_daily')}) - INTERVAL 7 DAYS GROUP BY dept_id ORDER BY osa_pct ASC LIMIT 1"),
    ("How many critical alerts are there tonight per store?",
     f"SELECT store_id, count(*) AS critical_alerts FROM {T('gold_replenishment_recommendations')} WHERE risk_tier = 'CRITICAL' GROUP BY store_id ORDER BY critical_alerts DESC"),
    ("What was total revenue by year?",
     f"SELECT year(date) AS year, round(sum(revenue)) AS revenue FROM {T('gold_osa_kpi_daily')} GROUP BY 1 ORDER BY 1"),
    ("Which C-tier suppliers missed their on-time SLA most often in 2016?",
     f"SELECT supplier_name, count(*) AS weeks_missed FROM {T('gold_supplier_performance_weekly')} WHERE reliability_tier = 'C' "
     f"AND NOT meets_on_time_sla AND week_start >= '2016-01-01' GROUP BY supplier_name ORDER BY weeks_missed DESC"),
    ("What is the total revenue at risk over the next 3 days across all open alerts?",
     f"SELECT round(sum(revenue_at_risk_3d)) AS revenue_at_risk FROM {T('gold_replenishment_recommendations')}"),
]

payload = {
    "version": 2,
    "config": {"sample_questions": sorted([{"id": hid("sq" + q), "question": [q]} for q in sample_q], key=lambda x: x["id"])},
    "data_sources": {"tables": tables},
    "instructions": {
        "text_instructions": [{"id": hid("text-instructions"), "content": [t + "\n" for t in text]}],
        "example_question_sqls": sorted([{"id": hid("ex" + q), "question": [q], "sql": [s]} for q, s in examples], key=lambda x: x["id"]),
        "join_specs": sorted([{"id": hid("join" + l + r), "left": {"identifier": T(l), "alias": l}, "right": {"identifier": T(r), "alias": r},
                               "sql": [cond, f"--rt=FROM_RELATIONSHIP_TYPE_{rt}--"]} for l, r, cond, rt in joins], key=lambda x: x["id"]),
    },
    "benchmarks": {"questions": sorted([{"id": hid("bm" + q), "question": [q], "answer": [{"format": "SQL", "content": [s]}]}
                                        for q, s in benchmarks], key=lambda x: x["id"])},
}

if __name__ == "__main__":  # noqa
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    body = {"warehouse_id": WAREHOUSE, "serialized_space": json.dumps(payload),
            "title": "OSA Analyst — On-Shelf Availability",
            "description": "Ask about on-shelf availability, lost sales, stockout root causes, supplier performance and tonight's alerts."}
    if not args or args[0] == "create":
        me = json.loads(subprocess.check_output(["databricks", "current-user", "me", "-p", PROFILE, "-o", "json"]))["userName"]
        body["parent_path"] = f"/Workspace/Users/{me}"
        cmd = ["databricks", "genie", "create-space", "--json", json.dumps(body), "-p", PROFILE, "-o", "json"]
    else:
        cmd = ["databricks", "genie", "update-space", args[1], "--json", json.dumps(body), "-p", PROFILE, "-o", "json"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    print(out.stdout[:2000] or out.stderr[:4000])
    sys.exit(out.returncode)
