# Task `lakeflow_pipeline` — SUCCESS

*Run 193340423596860 · started 2026-10-31 00:17:17 UTC · 193s*

Pipeline `320292b1-a8ff-4653-80ac-e119c25b030a` · update `7b15224f-b0a5-4391-888e-33d52c1beafb` · state **COMPLETED**

Metrics read from the pipeline event log (`event_log()` table-valued function).

| flow | output_rows | dropped_by_expectations | seconds |
|---|---|---|---|
| gold_osa_kpi_daily | 136010 | 0 | 134.5 |
| gold_store_item_daily | 59242070 | 0 | 134.5 |
| bronze_pos_daily_sales | 30490 | 0 | 22.7 |
| bronze_m5_sell_prices | 0 | 0 | 7.9 |
| silver_inventory_snapshots | 5549173 | 655 | 82.6 |
| pos_daily_feed | 30490 | 0 | 22.6 |
| gold_stockout_features | 5549173 | 0 | 134.5 |
| bronze_m5_calendar | 0 | 0 | 6.9 |
| silver_sell_prices | 6841121 | 0 | 16.2 |
| silver_purchase_orders | 708458 | 0 | 82.6 |
| bronze_erp_po_events | 10392 | 0 | 22.7 |
| gold_stockout_events | 444643 | 0 | 134.5 |
| dim_item | 3049 | 0 | 25.6 |
| bronze_erp_stores | 0 | 0 | 8.6 |
| bronze_erp_item_master | 0 | 0 | 9.4 |
| silver_po_events | 10387 | 5 | 22.7 |
| dim_supplier | 21 | 0 | 16.4 |
| bronze_m5_sales_wide | 0 | 0 | 6.6 |
| silver_calendar | 1969 | 0 | 16.3 |
| m5_history_unpivot | 0 | 0 | 22.6 |
| bronze_erp_suppliers | 0 | 0 | 7.3 |
| dim_store | 10 | 0 | 18.9 |
| gold_supplier_performance_weekly | 567 | 0 | 134.5 |
| bronze_erp_inventory_snapshots | 30539 | 0 | 22.6 |
| missingFlowName | 0 | 0 | 111.9 |

**Data-quality expectations** (warn / drop / fail rules declared in the pipeline)

| dataset | expectation | passed | failed |
|---|---|---|---|
| dim_item | item_has_supplier | 3049 | 0 |
| gold_stockout_features | cover_known | 5549173 | 0 |
| gold_store_item_daily | price_known_when_selling | 59242070 | 0 |
| pos_daily_feed | date_present | 30490 | 0 |
| pos_daily_feed | item_present | 30490 | 0 |
| pos_daily_feed | non_negative_units | 30490 | 0 |
| pos_daily_feed | valid_store | 30490 | 0 |
| silver_calendar | date_present | 1969 | 0 |
| silver_inventory_snapshots | item_present | 5549338 | 490 |
| silver_inventory_snapshots | non_negative_on_hand | 5549821 | 7 |
| silver_inventory_snapshots | non_negative_on_order | 5549828 | 0 |
| silver_inventory_snapshots | valid_store | 5549670 | 158 |
| silver_po_events | known_event | 10392 | 0 |
| silver_po_events | po_present | 10392 | 0 |
| silver_po_events | qty_present | 10387 | 5 |
| silver_purchase_orders | received_not_before_created | 708458 | 0 |
| silver_sell_prices | positive_price | 6841121 | 0 |
