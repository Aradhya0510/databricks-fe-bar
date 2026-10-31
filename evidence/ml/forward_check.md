# Forward check on real, unseen Walmart sales

*2026-10-31 00:24 UTC.* Scores were produced for business date **2016-05-22** (model `osa_stockout_risk@champion`) before the following POS days were released into the lakehouse: **2016-05-23, 2016-05-24** (M5 evaluation-period sales, never used in training).

Only store-items that were **on the shelf** on 22-May are included. A store-item that normally sells but records zero units is the observable symptom of an empty shelf.

## By predicted risk tier

| risk_tier | store_items | store_item_days | pct_days_zero_sales | sell_through_vs_normal_demand | avg_predicted_risk |
|---|---|---|---|---|---|
| CRITICAL | 683 | 1366 | 84.1 | 0.26 | 0.911 |
| HIGH | 128 | 256 | 57.8 | 0.74 | 0.463 |
| WATCH | 469 | 938 | 40.5 | 0.93 | 0.22 |
| OK | 20003 | 40006 | 42.9 | 0.95 | 0.022 |


## Fast movers (≥ 1 unit/day normally): any zero-sales outcome over the released days

| group_ | store_items | pct_with_zero_sales_all_released_days |
|---|---|---|
| predicted >= 0.60 | 391 | 65.7 |
| predicted < 0.60 | 9797 | 7.1 |


*Reading:* if the model ranks risk correctly, higher tiers show a higher zero-sales share and lower sell-through than lower tiers on the following real days.

**Caveat — read before quoting these numbers.** The sales outcomes are real, but the supply-side inputs are simulated: to make each real stockout explainable, the ERP simulator (`src/setup/02_generate_ops_data.py`) places a late supplier PO (≈75 %) or phantom stock (≈25 %) in front of it. The overdue-PO features therefore carry planted information about upcoming stockouts that a real ERP carries only partially. Treat the lift here (and the test metrics in training) as an **upper bound**; the pilot's shadow run re-baselines precision on the customer's real ERP feed.
