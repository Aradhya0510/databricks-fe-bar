# Task `lakeflow_pipeline` — SUCCESS

*Run 20055845787659 · started 2026-10-30 23:54:06 UTC · 213s*

Pipeline `320292b1-a8ff-4653-80ac-e119c25b030a` · update `7b2db471-1387-45fa-bbae-2da60f0c4524` · state **COMPLETED**

Metrics read from the pipeline event log (`event_log()` table-valued function).

| flow | output_rows | dropped_by_expectations | seconds |
|---|---|---|---|
| m5_history_unpivot | 0 | 0 | 21.0 |
| gold_supplier_performance_weekly | 567 | 0 | 141.0 |
| silver_purchase_orders | 700300 | 0 | 81.0 |
| bronze_m5_sell_prices | 0 | 0 | 9.3 |
| gold_store_item_daily | 59211580 | 0 | 141.0 |
| bronze_m5_sales_wide | 0 | 0 | 6.9 |
| bronze_erp_po_events | 11746 | 0 | 21.0 |
| bronze_pos_daily_sales | 30490 | 0 | 21.0 |
| silver_calendar | 1969 | 0 | 17.5 |
| silver_po_events | 11741 | 5 | 81.0 |
| silver_inventory_snapshots | 5518686 | 646 | 81.0 |
| dim_item | 3049 | 0 | 28.0 |
| gold_stockout_events | 444380 | 0 | 141.0 |
| bronze_erp_suppliers | 0 | 0 | 7.2 |
| bronze_erp_inventory_snapshots | 30538 | 0 | 21.0 |
| gold_osa_kpi_daily | 135940 | 0 | 141.0 |
| pos_daily_feed | 30490 | 0 | 81.0 |
| dim_supplier | 21 | 0 | 17.6 |
| bronze_erp_item_master | 0 | 0 | 10.3 |
| gold_stockout_features | 5518686 | 0 | 148.1 |
| bronze_m5_calendar | 0 | 0 | 7.7 |
| bronze_erp_stores | 0 | 0 | 9.8 |
| dim_store | 10 | 0 | 19.9 |
| silver_sell_prices | 6841121 | 0 | 19.9 |
| missingFlowName | 0 | 0 | 127.1 |

**Data-quality expectations** (warn / drop / fail rules declared in the pipeline)

| dataset | expectation | passed | failed |
|---|---|---|---|
| dim_item | item_has_supplier | 3049 | 0 |
| gold_stockout_features | cover_known | 5518686 | 0 |
| gold_store_item_daily | price_known_when_selling | 59211580 | 0 |
| pos_daily_feed | date_present | 30490 | 0 |
| pos_daily_feed | item_present | 30490 | 0 |
| pos_daily_feed | non_negative_units | 30490 | 0 |
| pos_daily_feed | valid_store | 30490 | 0 |
| silver_calendar | date_present | 1969 | 0 |
| silver_inventory_snapshots | item_present | 5518846 | 486 |
| silver_inventory_snapshots | non_negative_on_hand | 5519328 | 4 |
| silver_inventory_snapshots | non_negative_on_order | 5519332 | 0 |
| silver_inventory_snapshots | valid_store | 5519176 | 156 |
| silver_po_events | known_event | 11746 | 0 |
| silver_po_events | po_present | 11746 | 0 |
| silver_po_events | qty_present | 11741 | 5 |
| silver_purchase_orders | received_not_before_created | 700300 | 0 |
| silver_sell_prices | positive_price | 6841121 | 0 |
