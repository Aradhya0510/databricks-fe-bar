# Task `lakeflow_pipeline` — SUCCESS

*Run 775281851189969 · started 2026-10-30 23:24:24 UTC · 193s*

Pipeline `320292b1-a8ff-4653-80ac-e119c25b030a` · update `02869fb7-9fad-473e-b3f6-140d4608b472` · state **COMPLETED**

Metrics read from the pipeline event log (`event_log()` table-valued function).

| flow | output_rows | dropped_by_expectations | seconds |
|---|---|---|---|
| gold_stockout_features | 5488200 | 0 | 128.8 |
| silver_sell_prices | 6841121 | 0 | 18.5 |
| bronze_erp_suppliers | 0 | 0 | 7.1 |
| m5_history_unpivot | 0 | 0 | 20.7 |
| gold_store_item_daily | 59181090 | 0 | 128.8 |
| bronze_erp_po_events | 0 | 0 | 5.9 |
| gold_osa_kpi_daily | 135870 | 0 | 128.8 |
| bronze_m5_calendar | 0 | 0 | 7.3 |
| pos_daily_feed | 0 | 0 | 15.0 |
| bronze_pos_daily_sales | 0 | 0 | 5.1 |
| dim_store | 10 | 0 | 18.6 |
| bronze_m5_sales_wide | 0 | 0 | 6.3 |
| bronze_erp_stores | 0 | 0 | 9.0 |
| dim_supplier | 21 | 0 | 17.3 |
| gold_stockout_events | 444120 | 0 | 128.8 |
| silver_purchase_orders | 692298 | 0 | 21.6 |
| dim_item | 3049 | 0 | 21.6 |
| bronze_m5_sell_prices | 0 | 0 | 8.5 |
| silver_po_events | 0 | 0 | 20.7 |
| bronze_erp_inventory_snapshots | 0 | 0 | 8.0 |
| gold_supplier_performance_weekly | 567 | 0 | 128.8 |
| bronze_erp_item_master | 0 | 0 | 9.6 |
| silver_inventory_snapshots | 5488200 | 638 | 17.3 |
| silver_calendar | 1969 | 0 | 17.2 |
| missingFlowName | 0 | 0 | 108.1 |

**Data-quality expectations** (warn / drop / fail rules declared in the pipeline)

| dataset | expectation | passed | failed |
|---|---|---|---|
| dim_item | item_has_supplier | 3049 | 0 |
| gold_stockout_features | cover_known | 5488200 | 0 |
| gold_store_item_daily | price_known_when_selling | 59181090 | 0 |
| silver_calendar | date_present | 1969 | 0 |
| silver_inventory_snapshots | item_present | 5488355 | 483 |
| silver_inventory_snapshots | non_negative_on_hand | 5488838 | 0 |
| silver_inventory_snapshots | non_negative_on_order | 5488838 | 0 |
| silver_inventory_snapshots | valid_store | 5488683 | 155 |
| silver_purchase_orders | received_not_before_created | 692298 | 0 |
| silver_sell_prices | positive_price | 6841121 | 0 |
