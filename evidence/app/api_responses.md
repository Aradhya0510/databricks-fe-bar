# OSA Command Center — live API evidence

*App `osa-command-center` at https://osa-command-center-7474659940257593.aws.databricksapps.com · app status **RUNNING** · service principal `469361d3-732e-45be-b178-e0f3c33ad5ec` · captured 2026-10-31 00:47 UTC*

Each section is the real HTTP response of the deployed app (lists truncated to 5 items).

## Health (Lakebase connection as the app's service principal)

`GET /api/health` → HTTP 200 in 654 ms. 

```json
{
  "app": "ok",
  "lakebase": "error: consuming input failed: terminating connection due to administrator command\nSSL connection has been closed unexpectedly",
  "warehouse_id": "e0a8cc3b322c1f1d",
  "supervisor_endpoint": "mas-2ee5d824-endpoint",
  "genie_space_id": "01f1d4b044db1d4d988e71d91e6decbd"
}
```

## Context (from Lakebase synced table serving.replenishment_recommendations)

`GET /api/context` → HTTP 200 in 1333 ms. 

```json
{
  "score_date": "2016-05-24",
  "open_recommendations": 1168,
  "model_version": 2,
  "critical": 319
}
```

## KPI tiles + 8-week trend (SQL warehouse, governed gold tables)

`GET /api/kpis?region=ALL` → HTTP 200 in 3295 ms. 

```json
{
  "summary": [
    {
      "scope": "All regions",
      "period": "last_7d",
      "period_start": "2016-05-18",
      "period_end": "2016-05-24",
      "osa_pct": "93.79",
      "revenue": "953628.0",
      "lost_revenue": "39174.0",
      "lost_sales_rate_pct": "3.95",
      "oos_store_item_days": "9539"
    },
    {
      "scope": "All regions",
      "period": "prior_7d",
      "period_start": "2016-05-11",
      "period_end": "2016-05-17",
      "osa_pct": "92.0",
      "revenue": "1020469.0",
      "lost_revenue": "50678.0",
      "lost_sales_rate_pct": "4.73",
      "oos_store_item_days": "12183"
    }
  ],
  "trend": [
    {
      "date": "2016-03-30",
      "region": "South",
      "osa_pct": "89.42",
      "lost_revenue": "2249.0"
    },
    {
      "date": "2016-03-30",
      "region": "Midwest",
      "osa_pct": "89.76",
      "lost_revenue": "2650.0"
    },
    {
      "date": "2016-03-30",
      "region": "West",
      "osa_pct": "90.18",
      "lost_revenue": "3503.0"
    },
    {
      "date": "2016-03-31",
      "region": "South",
      "osa_pct": "90.49",
      "lost_revenue": "1934.0"
    },
    {
      "date": "2016-03-31",
      "region": "West",
      "osa_pct": "91.0",
      "lost_revenue": "3104.0"
    },
    "... 163 more"
  ],
  "at_risk": [
    {
      "risk_tier": "CRITICAL",
      "items": 319,
      "revenue_at_risk_3d": 4105
    },
    {
      "risk_tier": "OOS_NOW",
      "items": 586,
      "revenue_at_risk_3d": 7422
    },
    {
      "risk_tier": "HIGH",
      "items": 112,
      "revenue_at_risk_3d": 548
    },
    {
      "risk_tier": "OOS_PHANTOM",
      "items": 151,
      "revenue_at_risk_3d": 1826
    }
  ]
}
```

## Action queue — CRITICAL, all stores (Lakebase, joined with latest decision)

`GET /api/queue?tier=CRITICAL&limit=20` → HTTP 200 in 445 ms. 

```json
[
  {
    "rec_id": "CA_3|FOODS_1_170|2016-05-24",
    "priority_rank": 2,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "FOODS_1_170",
    "item_name": "Equate Cheddar Block #170",
    "dept_id": "FOODS_1",
    "supplier_name": "Sunvale Bakery Partners",
    "risk_tier": "CRITICAL",
    "risk_score": 0.988,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 4,
    "on_hand_units": 0,
    "on_order_units": 153,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 0,
    "revenue_at_risk_3d": 174.59,
    "rationale": "Equate Cheddar Block #170 has 0 units on hand with 99% stockout probability and 10.4 units/day demand\u2014execute EMERGENCY_DSD of 4 units immediately.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  {
    "rec_id": "WI_2|FOODS_2_029|2016-05-24",
    "priority_rank": 3,
    "score_date": "2016-05-24",
    "store_id": "WI_2",
    "region": "Midwest",
    "item_id": "FOODS_2_029",
    "item_name": "Hearth & Home Cereal #029",
    "dept_id": "FOODS_2",
    "supplier_name": "Coastal Canning Co",
    "risk_tier": "CRITICAL",
    "risk_score": 0.961,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 36,
    "on_hand_units": 0,
    "on_order_units": 53,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 2,
    "revenue_at_risk_3d": 149.98,
    "rationale": "Hearth & Home Cereal #029 has 0 units on hand with 96% stockout probability; execute EMERGENCY_DSD of 36 units immediately due to 2-day overdue supplier PO.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  {
    "rec_id": "CA_3|FOODS_2_183|2016-05-24",
    "priority_rank": 7,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "FOODS_2_183",
    "item_name": "Northpeak Soup #183",
    "dept_id": "FOODS_2",
    "supplier_name": "Harvest Lane Grocers Supply",
    "risk_tier": "CRITICAL",
    "risk_score": 0.991,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 16,
    "on_hand_units": 0,
    "on_order_units": 45,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 1,
    "revenue_at_risk_3d": 99.91,
    "rationale": "Northpeak Soup #183 has 0 units on hand with 99% stockout probability; execute EMERGENCY_DSD of 16 units immediately due to 1 overdue PO and 3.7 units/day demand.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  {
    "rec_id": "CA_1|FOODS_3_682|2016-05-24",
    "priority_rank": 8,
    "score_date": "2016-05-24",
    "store_id": "CA_1",
    "region": "West",
    "item_id": "FOODS_3_682",
    "item_name": "Equate Cola 12pk #682",
    "dept_id": "FOODS_3",
    "supplier_name": "Prime Valley Distribution",
    "risk_tier": "CRITICAL",
    "risk_score": 0.994,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 48,
    "on_hand_units": 0,
    "on_order_units": 102,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 1,
    "revenue_at_risk_3d": 89.1,
    "rationale": "Item #682 has 0 units on hand with 99% stockout probability and 8.4 units/day demand; execute EMERGENCY_DSD of 48 units immediately due to 1-day overdue PO.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  {
    "rec_id": "CA_3|HOUSEHOLD_1_488|2016-05-24",
    "priority_rank": 10,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "HOUSEHOLD_1_488",
    "item_name": "Great Value Dish Soap #488",
    "dept_id": "HOUSEHOLD_1",
    "supplier_name": "Polaris Paper & Plastics",
    "risk_tier": "CRITICAL",
    "risk_score": 0.981,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 24,
    "on_hand_units": 0,
    "on_order_units": 41,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 3,
    "revenue_at_risk_3d": 75.37,
    "rationale": "Great Value Dish Soap #488 has 0 units on hand with 98% stockout probability and overdue supplier delivery; execute EMERGENCY_DSD of 24 units immediately.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  "... 15 more"
]
```

## Item lookup typeahead (Lakebase serving.stockout_risk_scores)

`GET /api/items?q=milk&store=CA_1` → HTTP 200 in 377 ms. `latency_ms` is the Postgres query time measured inside the app.

```json
{
  "latency_ms": 34.5,
  "rows": [
    {
      "store_id": "CA_1",
      "item_id": "FOODS_1_088",
      "item_name": "Great Value Whole Milk #088",
      "dept_id": "FOODS_1",
      "risk_tier": "OOS_PHANTOM",
      "risk_score": 0.94,
      "driver_1": "days_since_last_sale",
      "driver_2": "cv_units_28d",
      "driver_3": "on_hand_units",
      "on_hand_units": 15,
      "on_order_units": 0,
      "days_of_cover": 6.72,
      "demand_per_day": 2.23,
      "overdue_po_count": 0,
      "revenue_at_risk_3d": 35.37
    },
    {
      "store_id": "CA_1",
      "item_id": "FOODS_1_096",
      "item_name": "Great Value Whole Milk #096",
      "dept_id": "FOODS_1",
      "risk_tier": "CRITICAL",
      "risk_score": 0.926,
      "driver_1": "overdue_po_count",
      "driver_2": "max_days_overdue",
      "driver_3": "days_of_cover",
      "on_hand_units": 0,
      "on_order_units": 9,
      "days_of_cover": 0.0,
      "demand_per_day": 0.6,
      "overdue_po_count": 1,
      "revenue_at_risk_3d": 9.56
    },
    {
      "store_id": "CA_1",
      "item_id": "FOODS_1_040",
      "item_name": "Great Value Whole Milk #040",
      "dept_id": "FOODS_1",
      "risk_tier": "OOS_PHANTOM",
      "risk_score": 0.79,
      "driver_1": "days_since_last_sale",
      "driver_2": "lambda_90d",
      "driver_3": "on_hand_units",
      "on_hand_units": 22,
      "on_order_units": 0,
      "days_of_cover": 9.12,
      "demand_per_day": 2.41,
      "overdue_po_count": 0,
      "revenue_at_risk_3d": 12.87
    },
    {
      "store_id": "CA_1",
      "item_id": "FOODS_1_136",
      "item_name": "Great Value Whole Milk #136",
      "dept_id": "FOODS_1",
      "risk_tier": "OOS_NOW",
      "risk_score": 0.747,
      "driver_1": "overdue_po_count",
      "driver_2": "max_days_overdue",
      "driver_3": "avg_units_28d",
      "on_hand_units": 0,
      "on_order_units": 8,
      "days_of_cover": 0.0,
      "demand_per_day": 0.49,
      "overdue_po_count": 1,
      "revenue_at_risk_3d": 7.13
    },
    {
      "store_id": "CA_1",
      "item_id": "FOODS_1_144",
      "item_name": "Great Value Whole Milk #144",
      "dept_id": "FOODS_1",
      "risk_tier": "OOS_NOW",
      "risk_score": 0.543,
      "driver_1": "overdue_po_count",
      "driver_2": "max_days_overdue",
      "driver_3": "position_cover_days",
      "on_hand_units": 0,
      "on_order_units": 15,
      "days_of_cover": 0.0,
      "demand_per_day": 0.89,
      "overdue_po_count": 1,
      "revenue_at_risk_3d": 18.62
    },
    "... 20 more"
  ]
}
```

## Store decision 1 — APPROVE (INSERT into Lakebase osa_app.replenishment_actions)

`POST /api/decision` → HTTP 200 in 361 ms. 

Request body:

```json
{
  "rec_id": "CA_3|FOODS_1_170|2016-05-24",
  "action": "APPROVE"
}
```

```json
{
  "saved": {
    "action_id": "1428b347-0301-4338-8a30-f8e3b825c0bc",
    "rec_id": "CA_3|FOODS_1_170|2016-05-24",
    "store_id": "CA_3",
    "item_id": "FOODS_1_170",
    "action": "APPROVE",
    "final_qty": 4,
    "reason_code": null,
    "note": null,
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:16.034242+00:00",
    "recommended_qty": 4,
    "risk_tier": "CRITICAL"
  },
  "requires_regional_manager_approval": false
}
```

## Store decision 2 — OVERRIDE with reason code (> 50% → regional approval flag)

`POST /api/decision` → HTTP 200 in 353 ms. 

Request body:

```json
{
  "rec_id": "WI_2|FOODS_2_029|2016-05-24",
  "action": "OVERRIDE",
  "final_qty": 73,
  "reason_code": "LOCAL_EVENT",
  "note": "Memorial Day cook-out at the community park"
}
```

```json
{
  "saved": {
    "action_id": "f24a2e40-6508-4fac-ae2e-155a15abbbf5",
    "rec_id": "WI_2|FOODS_2_029|2016-05-24",
    "store_id": "WI_2",
    "item_id": "FOODS_2_029",
    "action": "OVERRIDE",
    "final_qty": 73,
    "reason_code": "LOCAL_EVENT",
    "note": "Memorial Day cook-out at the community park",
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:16.393732+00:00",
    "recommended_qty": 36,
    "risk_tier": "CRITICAL"
  },
  "requires_regional_manager_approval": true
}
```

## Store decision 3 — OVERRIDE without reason code (rejected by SOP-REP-001 rule)

`POST /api/decision` → HTTP 400 in 351 ms. 

Request body:

```json
{
  "rec_id": "CA_3|FOODS_2_183|2016-05-24",
  "action": "OVERRIDE",
  "final_qty": 5
}
```

```json
"{\"detail\":\"overrides require a reason code (SOP-REP-001 \u00a74)\"}"
```

## Store decision 4 — REJECT

`POST /api/decision` → HTTP 200 in 320 ms. 

Request body:

```json
{
  "rec_id": "CA_3|FOODS_2_183|2016-05-24",
  "action": "REJECT",
  "note": "item being delisted next week"
}
```

```json
{
  "saved": {
    "action_id": "ac152259-f705-4a57-8bee-682c563fb7cc",
    "rec_id": "CA_3|FOODS_2_183|2016-05-24",
    "store_id": "CA_3",
    "item_id": "FOODS_2_183",
    "action": "REJECT",
    "final_qty": 0,
    "reason_code": null,
    "note": "item being delisted next week",
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:17.064502+00:00",
    "recommended_qty": 16,
    "risk_tier": "CRITICAL"
  },
  "requires_regional_manager_approval": false
}
```

## Decisions now stored in Lakebase

`GET /api/decisions?limit=10` → HTTP 200 in 319 ms. 

```json
[
  {
    "action_id": "ac152259-f705-4a57-8bee-682c563fb7cc",
    "rec_id": "CA_3|FOODS_2_183|2016-05-24",
    "store_id": "CA_3",
    "item_id": "FOODS_2_183",
    "action": "REJECT",
    "final_qty": 0,
    "reason_code": null,
    "note": "item being delisted next week",
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:17.064502+00:00",
    "recommended_qty": 16,
    "risk_tier": "CRITICAL"
  },
  {
    "action_id": "f24a2e40-6508-4fac-ae2e-155a15abbbf5",
    "rec_id": "WI_2|FOODS_2_029|2016-05-24",
    "store_id": "WI_2",
    "item_id": "FOODS_2_029",
    "action": "OVERRIDE",
    "final_qty": 73,
    "reason_code": "LOCAL_EVENT",
    "note": "Memorial Day cook-out at the community park",
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:16.393732+00:00",
    "recommended_qty": 36,
    "risk_tier": "CRITICAL"
  },
  {
    "action_id": "1428b347-0301-4338-8a30-f8e3b825c0bc",
    "rec_id": "CA_3|FOODS_1_170|2016-05-24",
    "store_id": "CA_3",
    "item_id": "FOODS_1_170",
    "action": "APPROVE",
    "final_qty": 4,
    "reason_code": null,
    "note": null,
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:16.034242+00:00",
    "recommended_qty": 4,
    "risk_tier": "CRITICAL"
  },
  {
    "action_id": "a0936b44-8d1d-4ea6-a45e-11667be9b0ec",
    "rec_id": "CA_3|FOODS_2_183|2016-05-23",
    "store_id": "CA_3",
    "item_id": "FOODS_2_183",
    "action": "REJECT",
    "final_qty": 0,
    "reason_code": null,
    "note": "item being delisted next week",
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:14:27.766333+00:00",
    "recommended_qty": 4,
    "risk_tier": "CRITICAL"
  },
  {
    "action_id": "6b256dbe-111d-4af8-b973-f6926bb01c6f",
    "rec_id": "WI_2|FOODS_2_029|2016-05-23",
    "store_id": "WI_2",
    "item_id": "FOODS_2_029",
    "action": "OVERRIDE",
    "final_qty": 73,
    "reason_code": "LOCAL_EVENT",
    "note": "Memorial Day cook-out at the community park",
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:14:27.113835+00:00",
    "recommended_qty": 36,
    "risk_tier": "CRITICAL"
  },
  "... 1 more"
]
```

## Action queue reflects the decisions

`GET /api/queue?store=CA_3&tier=CRITICAL&limit=10` → HTTP 200 in 351 ms. 

```json
[
  {
    "rec_id": "CA_3|FOODS_1_170|2016-05-24",
    "priority_rank": 2,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "FOODS_1_170",
    "item_name": "Equate Cheddar Block #170",
    "dept_id": "FOODS_1",
    "supplier_name": "Sunvale Bakery Partners",
    "risk_tier": "CRITICAL",
    "risk_score": 0.988,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 4,
    "on_hand_units": 0,
    "on_order_units": 153,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 0,
    "revenue_at_risk_3d": 174.59,
    "rationale": "Equate Cheddar Block #170 has 0 units on hand with 99% stockout probability and 10.4 units/day demand\u2014execute EMERGENCY_DSD of 4 units immediately.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": "APPROVE",
    "decision_qty": 4,
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:16.034242+00:00"
  },
  {
    "rec_id": "CA_3|FOODS_2_183|2016-05-24",
    "priority_rank": 7,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "FOODS_2_183",
    "item_name": "Northpeak Soup #183",
    "dept_id": "FOODS_2",
    "supplier_name": "Harvest Lane Grocers Supply",
    "risk_tier": "CRITICAL",
    "risk_score": 0.991,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 16,
    "on_hand_units": 0,
    "on_order_units": 45,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 1,
    "revenue_at_risk_3d": 99.91,
    "rationale": "Northpeak Soup #183 has 0 units on hand with 99% stockout probability; execute EMERGENCY_DSD of 16 units immediately due to 1 overdue PO and 3.7 units/day demand.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": "REJECT",
    "decision_qty": 0,
    "decided_by": "aradhya.chouhan@databricks.com",
    "decided_at": "2026-10-31T00:47:17.064502+00:00"
  },
  {
    "rec_id": "CA_3|HOUSEHOLD_1_488|2016-05-24",
    "priority_rank": 10,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "HOUSEHOLD_1_488",
    "item_name": "Great Value Dish Soap #488",
    "dept_id": "HOUSEHOLD_1",
    "supplier_name": "Polaris Paper & Plastics",
    "risk_tier": "CRITICAL",
    "risk_score": 0.981,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 24,
    "on_hand_units": 0,
    "on_order_units": 41,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 3,
    "revenue_at_risk_3d": 75.37,
    "rationale": "Great Value Dish Soap #488 has 0 units on hand with 98% stockout probability and overdue supplier delivery; execute EMERGENCY_DSD of 24 units immediately.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  {
    "rec_id": "CA_3|HOUSEHOLD_2_044|2016-05-24",
    "priority_rank": 18,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "HOUSEHOLD_2_044",
    "item_name": "Parent's Choice Bath Towels #044",
    "dept_id": "HOUSEHOLD_2",
    "supplier_name": "Crestview Hardware Wholesale",
    "risk_tier": "CRITICAL",
    "risk_score": 0.987,
    "recommended_action": "EXPEDITE_PO_AND_ESCALATE",
    "recommended_qty": 4,
    "on_hand_units": 0,
    "on_order_units": 75,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 0,
    "revenue_at_risk_3d": 61.14,
    "rationale": "Parent's Choice Bath Towels #044 is out of stock with 99% stockout probability and 1 overdue PO from Crestview Hardware Wholesale\u2014expedite and escalate 4 units immediately.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  {
    "rec_id": "CA_3|FOODS_3_067|2016-05-24",
    "priority_rank": 30,
    "score_date": "2016-05-24",
    "store_id": "CA_3",
    "region": "West",
    "item_id": "FOODS_3_067",
    "item_name": "Mainstays Granola Bars #067",
    "dept_id": "FOODS_3",
    "supplier_name": "Lakeshore Beverage Group",
    "risk_tier": "CRITICAL",
    "risk_score": 0.989,
    "recommended_action": "EMERGENCY_DSD",
    "recommended_qty": 6,
    "on_hand_units": 0,
    "on_order_units": 57,
    "days_of_cover": 0.0,
    "overdue_po_count": 1,
    "max_days_overdue": 3,
    "revenue_at_risk_3d": 49.58,
    "rationale": "Mainstays Granola Bars #067 has 0 units on hand with 99% stockout probability and 1 overdue PO; execute EMERGENCY_DSD of 6 units immediately.",
    "rationale_source": "databricks-claude-sonnet-4-5",
    "decision": null,
    "decision_qty": null,
    "decided_by": null,
    "decided_at": null
  },
  "... 5 more"
]
```

## Nightly briefings (Lakebase serving.intelligence_reports)

`GET /api/briefings` → HTTP 200 in 411 ms. 

```json
[
  {
    "report_id": "2016-05-24|executive|ALL",
    "report_date": "2016-05-24",
    "audience": "executive",
    "region": "ALL",
    "title": "Executive OSA briefing \u2014 2016-05-24",
    "markdown": "## Headline\nOSA improved to 93.79% and lost revenue fell to $39,174, down $11,504 (-22.7%) week over week. Tonight's queue still has $13,899 of 3-day revenue at risk across 1,168 items. Emergency DSD accounts for $8,808 of that.\n\n## KPIs\n| Metric | Last 7d | Prior 7d | Change |\n|---|---|---|---|\n| OSA % | 93.79% | 92.00% | +1.79 pts |\n| Revenue | $953,628 | $1,020,469 | -$66,841 (-6.5%) |\n| Lost revenue | $39,174 | $50,678 | -$11,504 (-22.7%) |\n| Lost sales rate | 3.95% | 4.73% | -0.78 pts |\n| OOS store-item-days | 9,539 | 12,183 | -2,644 |\n\nTotal revenue is down 6.5% even though availability improved, so the cause is probably demand or traffic rather than stockouts.\n\n## Top risks tonight\n- **TX_2, Great Value Tortilla Chips #120:** expedited order of 24 units, $237.05 at risk. It has 0 on hand despite 217 on order, so chase the inbound PO.\n- **CA_3, Equate Cheddar Block #170:** emergency DSD of 4 units, $174.59 at risk. Stockout probability is 99%.\n- **WI_2, Hearth & Home Cereal #029:** emergency DSD of 36 units, $149.98 at risk. The supplier PO is 2 days overdue.\n- **WI_2, Parent's Choice Peanut Butter #316:** emergency DSD of 8 units, $131.08 at risk. The PO is 5 days late.\n- **TX_3, Great Value Pasta #368:** emergency DSD of 24 units, $109.39 at risk.\n\n## Supplier watch\n- **SUP009 Prime Valley Distribution (tier C):** 383 stockouts, $10,897 lost, 58 still ongoing, 6.48 days late on average.\n- **SUP010 Lakeshore Beverage Group (tier C):** 433 stockouts (the most of any supplier), $10,161 lost, 59 ongoing.\n- **SUP018 Polaris Paper & Plastics (tier B):** $10,231 lost, 6.94 days late on average.\n\n## Recommended actions\n1. **Store managers (CA_3, WI_2, TX_3):** Submit emergency DSD requests for the 630 CRITICAL and OOS_NOW items before the 2:00 pm cut-off. Later requests arrive in two days. Only FOODS and HOUSEHOLD_1 items are eligible, and the cost is an 8% premium plus a $45 per store per day fee (GUIDE-DSD-005).\n2. **Category buyers:** Make the call on late POs that are 2 or more days overdue, and open a sourcing review for SUP009, SUP010 and SUP018 (POL-SUP-003). This covers 187 items in the expedite-and-escalate and verify-shelf tiers.\n3. **TX_2 store manager:** Trace the 217 units on order for Tortilla Chips #120 and place the 24-unit expedited order (POL-SUP-003).\n4. **Store associates:** Physically count the 151 phantom-inventory items (OOS_PHANTOM, $1,826 at risk) within 24 hours. Managers adjust ERP the same day. If a count is zero, they place an emergency order. Adjustments of $500 or more at cost need Regional Manager sign-off (GUIDE-DSD-005).",
    "model": "databricks-claude-sonnet-5-5",
    "generated_at": "2026-10-31T00:35:00.966995+00:00"
  },
  {
    "report_id": "2016-05-24|regional|Midwest",
    "report_date": "2016-05-24",
    "audience": "regional",
    "region": "Midwest",
    "title": "Midwest region OSA briefing \u2014 2016-05-24",
    "markdown": "## Headline\nMidwest OSA improved to 94.22% and lost revenue fell to $10,496, down $2,088 from the prior 7 days. Tonight's queue still has 342 items with $4,343 of 3-day revenue at risk, and 201 of those are OOS_NOW or CRITICAL items routed to Emergency DSD.\n\n## KPIs\n| Metric | Last 7d | Prior 7d | Change |\n|---|---|---|---|\n| OSA % | 94.22% | 93.08% | +1.14 pts |\n| Revenue | $253,501 | $301,019 | -$47,518 (-15.8%) |\n| Lost revenue | $10,496 | $12,584 | -$2,088 (-16.6%) |\n| Lost-sales rate | 3.98% | 4.01% | -0.03 pts |\n| OOS store-item-days | 2,566 | 3,057 | -491 |\n\nRevenue fell almost as much as lost revenue, so part of the lost-revenue improvement may come from lower sales, not just better availability.\n\n## Top risks tonight\n- **WI_2, Hearth & Home Cereal #029:** Emergency DSD, 36 units, $149.98 at risk. It is CRITICAL with 0 on hand and a PO 2 days overdue.\n- **WI_2, Parent's Choice Peanut Butter #316:** Emergency DSD, 8 units, $131.08 at risk. It is out of stock and the PO is 5 days late.\n- **WI_1, Equate Black Beans #282:** Emergency DSD, 16 units, $78.62 at risk. It is out of stock and the PO is 3 days late.\n- **WI_2, Mainstays Rice #251:** Expedited order, 16 units, $72.67 at risk.\n- **WI_2, Great Value Dish Soap #488:** Emergency DSD, 24 units, $70.54 at risk. The PO is 2 days overdue.\n\nWI_2 accounts for four of the five top items.\n\n## Supplier watch\n- **SUP009 Prime Valley Distribution (Tier C):** 110 stockouts, $3,290 lost, 15 still ongoing, average 6.38 days late.\n- **SUP010 Lakeshore Beverage Group (Tier C):** 143 stockouts, $3,114 lost, 18 still ongoing, average 5.8 days late.\n- **SUP007 Northstar Snacks & Beverage (Tier B):** 113 stockouts, $2,992 lost, 21 ongoing (the most in the region), average 6.04 days late.\n\n## Recommended actions\n1. **WI_2 and WI_1 store managers:** Submit the Emergency DSD orders above before the 2:00 pm local cut-off for next-morning delivery. All four items are in eligible departments (GUIDE-DSD-005).\n2. **Category buyers:** Call the supplier account managers for the POs that are 2 or more days late, including the cereal, peanut butter, black beans and dish soap POs. Open a sourcing review for any supplier at 3+ days late or with 2+ stockouts in a week. SUP009, SUP010 and SUP007 all qualify on average lateness (late-PO escalation ladder; the search did not return its document ID).\n3. **Procurement:** Charge the 8% Emergency DSD premium back to suppliers where a late PO is the root cause (POL-SUP-003).\n4. **Store associates:** Physically count the 38 suspected-phantom items ($536 at risk) within 24 hours. Store managers adjust the ERP the same day and reorder if the count is zero. Adjustments of $500 or more at cost need Regional Manager sign-off within 2 business days (phantom-inventory cycle count procedure; the se
```

## Ask — Genie mode (shows generated SQL + result)

`POST /api/ask` → HTTP 200 in 20534 ms. 

Request body:

```json
{
  "question": "Which 3 stores lost the most revenue to stockouts in the last 28 days?",
  "mode": "genie"
}
```

```json
{
  "mode": "genie",
  "conversation_id": "01f1d4c49fdb1a3b8b862aa3bac7b2d2",
  "answer": "You want to see the top 3 stores that lost the most revenue due to stockouts in the last 28 days, along with their regions and on-shelf availability percentages.\n\nThe **3 stores** with the highest lost revenue from stockouts over the last 28 days are **CA_3** in the **West** at **$32,718**, **CA_1** in the **West** at **$23,509**, and **CA_2** in the **West** at **$21,547**. Across these top 3 stores, lower on-shelf availability aligns with higher lost revenue, with **CA_3** also having the lowest availability at **91.23%**.",
  "sql": "WITH `store_losses` AS (\n  SELECT\n    `store_id`,\n    `region`,\n    ROUND(SUM(`lost_revenue`)) AS `lost_revenue`,\n    ROUND(100 * (1 - try_divide(SUM(`oos_store_items`),SUM(`active_store_items`))), 2) AS `osa_pct`\n  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`\n  WHERE `date` > (SELECT MAX(`date`) FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`) - INTERVAL 28 DAYS\n    AND `store_id` IS NOT NULL\n    AND `region` IS NOT NULL\n  GROUP BY `store_id`, `region`\n), `ranked` AS (\n  SELECT\n    `store_id`,\n    `region`,\n    `lost_revenue`,\n    `osa_pct`,\n    RANK() OVER (ORDER BY `lost_revenue` DESC) AS `store_rank`\n  FROM `store_losses`\n)\nSELECT\n  `store_id`,\n  `region`,\n  `lost_revenue`,\n  `osa_pct`\nFROM `ranked`\nWHERE `store_rank` <= 3\nORDER BY `store_rank`, `lost_revenue` DESC, `store_id`",
  "columns": [
    "store_id",
    "region",
    "lost_revenue",
    "osa_pct"
  ],
  "rows": [
    [
      "CA_3",
      "West",
      "32718.0",
      "91.23"
    ],
    [
      "CA_1",
      "West",
      "23509.0",
      "91.65"
    ],
    [
      "CA_2",
      "West",
      "21547.0",
      "93.21"
    ]
  ],
  "latency_s": 20.2
}
```

## Ask — Assistant mode (Supervisor Agent: data + documents)

`POST /api/ask` → HTTP 200 in 44039 ms. 

Request body:

```json
{
  "question": "Which supplier is causing the most stockouts in the South region recently, and what does our escalation policy say we must do?",
  "mode": "assistant"
}
```

```json
{
  "mode": "assistant",
  "answer": "I'll help you identify the supplier causing the most stockouts in the South region and then check our escalation policy. Let me start by querying the stockout data.<name>osa_analyst</name>||supplier_rank|supplier_name|reliability_tier|stockout_events|lost_revenue|\n|-|-|-|-|-|-|\n|0|1|Lakeshore Beverage Group|C|126|2908|\n|1|2|CleanWave Home Products|A|122|3271|\n|2|3|Ironwood Household Supply|B|103|2482|\n|3|4|Prime Valley Distribution|C|100|2542|\n|4|5|Coastal Canning Co|A|97|2525|\n|5|6|Northstar Snacks & Beverage|B|96|2262|\n|6|7|Polaris Paper & Plastics|B|94|3748|\n|7|8|Summit Hobby Wholesale|B|89|1460|\n|8|9|Blue Ridge Pantry Distributors|B|77|2326|\n|9|10|Maker's Mark Supply Co|B|74|832|\n|10|11|Brightline Toys & Crafts|C|71|1190|\n|11|12|Harvest Lane Grocers Supply|C|58|1941|\n|12|13|Evergreen Foods Wholesale|B|58|814|\n|13|14|Riverbend Fresh Foods|B|50|1298|\n|14|15|Crestview Hardware Wholesale|A|41|1123|\n|15|16|Golden Prairie Dairy Co|A|38|1374|\n|16|17|Meridian Kitchen & Bath|B|32|771|\n|17|18|Sunvale Bakery Partners|A|32|575|\n|18|19|Hearthstone Home Goods|A|24|530|\n|19|20|Atlas Party & Seasonal|A|24|127|\n|20|21|Pinecrest Leisure Goods|A|20|136|<name>OSA Assistant</name>Now let me check our escalation policy for suppliers causing stockouts.<name>OSA Policy & Procedures Assistant</name>\n\nAccording to POL-SUP-003, the escalation ladder for suppliers is as follows:\n\n| Trigger | Action | Owner |\n|---|---|---|\n| PO 1 day late | Automatic notification to supplier account manager | System  \u2026",
  "steps": [
    {
      "tool": "osa_analyst",
      "arguments": "{\"genie_query\": \"Which supplier caused the most stockouts in the South region recently? Show me the top suppliers ranked by number of stockout events.\"}"
    },
    {
      "tool": "osa_policies",
      "arguments": "{\"ka_query\": \"What is our escalation policy for suppliers causing stockouts? What are the required steps we must take?\"}"
    }
  ],
  "latency_s": 43.7
}
```

## Governance view (what the app identity is allowed to see)

`GET /api/governance` → HTTP 200 in 3823 ms. 

```json
{
  "identity": [
    {
      "identity": "469361d3-732e-45be-b178-e0f3c33ad5ec"
    }
  ],
  "dim_supplier_sample": [
    {
      "supplier_id": "SUP001",
      "supplier_name": "Golden Prairie Dairy Co",
      "late_penalty_pct_of_po": "1.0",
      "payment_terms": "NET30",
      "account_manager_email": "am.golden@golden-supply.example"
    },
    {
      "supplier_id": "SUP002",
      "supplier_name": "Riverbend Fresh Foods",
      "late_penalty_pct_of_po": "1.5",
      "payment_terms": "NET45",
      "account_manager_email": "am.riverbend@riverbend-supply.example"
    },
    {
      "supplier_id": "SUP003",
      "supplier_name": "Sunvale Bakery Partners",
      "late_penalty_pct_of_po": "1.0",
      "payment_terms": "NET60",
      "account_manager_email": "am.sunvale@sunvale-supply.example"
    }
  ],
  "kpi_rows_by_region": [
    {
      "region": "Midwest",
      "rows": "40803"
    },
    {
      "region": "South",
      "rows": "40803"
    },
    {
      "region": "West",
      "rows": "54404"
    }
  ]
}
```
