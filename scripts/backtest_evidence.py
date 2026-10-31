#!/usr/bin/env python3
"""Forward check: predictions made on the as-of date vs. what really happened in the released M5 days.

The scores for 2016-05-22 were written before the 2016-05-23+ POS files existed in the lakehouse. After
`osa_release_feed` lands those days (real Walmart sales from the M5 evaluation period), compare per risk tier:
  * share of store-items that sold nothing on each following day (shelf likely empty)
  * sell-through vs. normal demand (units sold / demand rate)
Writes evidence/ml/forward_check.md.  Usage: scripts/backtest_evidence.py [--profile fevm-bar]
"""
import json, os, subprocess, sys, time

PROFILE = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "fevm-bar"
S = "serverless_stable_4hkk7k_catalog.osa_retail"
OUT = os.path.join(os.path.dirname(__file__), "..", "evidence", "ml", "forward_check.md")


def sql(q):
    r = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "-p", PROFILE, "-o", "json", "--json",
                        json.dumps({"statement": q, "warehouse_id": "e0a8cc3b322c1f1d", "wait_timeout": "50s"})],
                       capture_output=True, text=True, check=True)
    r = json.loads(r.stdout)
    assert r["status"]["state"] == "SUCCEEDED", r["status"]
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return cols, r.get("result", {}).get("data_array") or []


def md(cols, rows):
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows])


days = sql(f"SELECT DISTINCT date FROM {S}.silver_sales_daily WHERE source = 'POS_FEED' ORDER BY date")[1]
q = f"""
WITH p AS (SELECT * FROM {S}.gold_stockout_risk_scores_history WHERE score_date = DATE'2016-05-22' AND NOT is_oos_today),
a AS (SELECT store_id, item_id, date, units FROM {S}.silver_sales_daily WHERE source = 'POS_FEED')
SELECT p.risk_tier, count(DISTINCT p.store_id || p.item_id) AS store_items, count(*) AS store_item_days,
       round(100 * avg(CASE WHEN a.units = 0 THEN 1 ELSE 0 END), 1) AS pct_days_zero_sales,
       round(sum(a.units) / sum(p.lambda_90d), 2) AS sell_through_vs_normal_demand,
       round(avg(p.risk_score), 3) AS avg_predicted_risk
FROM p JOIN a ON a.store_id = p.store_id AND a.item_id = p.item_id
GROUP BY p.risk_tier
ORDER BY CASE p.risk_tier WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'WATCH' THEN 3 ELSE 4 END"""
cols, rows = sql(q)
q2 = f"""
WITH p AS (SELECT * FROM {S}.gold_stockout_risk_scores_history WHERE score_date = DATE'2016-05-22' AND NOT is_oos_today),
a AS (SELECT store_id, item_id, sum(units) AS units, count(*) AS days FROM {S}.silver_sales_daily
      WHERE source = 'POS_FEED' GROUP BY 1, 2)
SELECT CASE WHEN p.risk_score >= 0.6 THEN 'predicted >= 0.60' ELSE 'predicted < 0.60' END AS group_,
       count(*) AS store_items,
       round(100 * avg(CASE WHEN a.units = 0 THEN 1 ELSE 0 END), 1) AS pct_with_zero_sales_all_released_days
FROM p JOIN a USING (store_id, item_id) WHERE p.lambda_90d >= 1 GROUP BY 1 ORDER BY 1 DESC"""
cols2, rows2 = sql(q2)
text = [f"# Forward check on real, unseen Walmart sales\n",
        f"*{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}.* Scores were produced for business date **2016-05-22** "
        f"(model `osa_stockout_risk@champion`) before the following POS days were released into the lakehouse: "
        f"**{', '.join(d[0] for d in days)}** (M5 evaluation-period sales, never used in training).\n",
        "Only store-items that were **on the shelf** on 22-May are included. A store-item that normally sells but records "
        "zero units is the observable symptom of an empty shelf.\n",
        "## By predicted risk tier\n", md(cols, rows), "\n",
        "## Fast movers (≥ 1 unit/day normally): any zero-sales outcome over the released days\n", md(cols2, rows2), "\n",
        "*Reading:* if the model ranks risk correctly, higher tiers show a higher zero-sales share and lower sell-through "
        "than lower tiers on the following real days.\n",
        "**Caveat — read before quoting these numbers.** The sales outcomes are real, but the supply-side inputs are "
        "simulated: to make each real stockout explainable, the ERP simulator (`src/setup/02_generate_ops_data.py`) "
        "places a late supplier PO (≈75 %) or phantom stock (≈25 %) in front of it. The overdue-PO features therefore "
        "carry planted information about upcoming stockouts that a real ERP carries only partially. Treat the lift "
        "here (and the test metrics in training) as an **upper bound**; the pilot's shadow run re-baselines precision on "
        "the customer's real ERP feed.\n"]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(text))
print("\n".join(text))
