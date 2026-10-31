# Table inventory — `serverless_stable_4hkk7k_catalog.osa_retail`

*2026-10-31 00:48 UTC; row counts via SQL warehouse; tags from information_schema.table_tags.*

| table | type | rows | layer | osa_data_origin | domain |
|---|---|---|---|---|---|
| bronze_erp_inventory_snapshots | STREAMING_TABLE | 5556487 | bronze | synthetic | supply_chain |
| bronze_erp_item_master | STREAMING_TABLE | 3049 | bronze | synthetic | supply_chain |
| bronze_erp_po_events | STREAMING_TABLE | 1401597 | bronze | synthetic | supply_chain |
| bronze_erp_stores | STREAMING_TABLE | 10 | bronze | synthetic | supply_chain |
| bronze_erp_suppliers | STREAMING_TABLE | 21 | bronze | synthetic | supply_chain |
| bronze_m5_calendar | STREAMING_TABLE | 1969 | bronze | public_m5 | supply_chain |
| bronze_m5_sales_wide | STREAMING_TABLE | 30490 | bronze | public_m5 | supply_chain |
| bronze_m5_sell_prices | STREAMING_TABLE | 6841121 | bronze | public_m5 | supply_chain |
| bronze_pos_daily_sales | STREAMING_TABLE | 60980 | bronze | public_m5 | supply_chain |
| dim_item | MATERIALIZED_VIEW | 3049 | silver | derived | supply_chain |
| dim_store | MATERIALIZED_VIEW | 10 | silver | synthetic | supply_chain |
| dim_supplier | MATERIALIZED_VIEW | 21 | silver | synthetic | supply_chain |
| event_log_320292b1_a8ff_4653_80ac_e119c25b030a | MANAGED | 1230 |  | derived | supply_chain |
| event_log_3b3c9c11_4a13_481b_90c4_a82d34ee6102 | MANAGED | 45 |  | derived | supply_chain |
| event_log_87d43533_ad93_46d6_8647_9a7724fcd75c | MANAGED | 45 |  | derived | supply_chain |
| event_log_fa08392a_1518_4d6a_88eb_f935c53c7ba5 | MANAGED | 45 |  | derived | supply_chain |
| gold_intelligence_reports | MANAGED | 12 | gold | derived | supply_chain |
| gold_osa_kpi_daily | MATERIALIZED_VIEW | 136010 | gold | derived | supply_chain |
| gold_replenishment_recommendations | MANAGED | 1168 | gold | derived | supply_chain |
| gold_stockout_events | MATERIALIZED_VIEW | 444643 | gold | derived | supply_chain |
| gold_stockout_features | MATERIALIZED_VIEW | 5549173 | gold | derived | supply_chain |
| gold_stockout_risk_scores | MANAGED | 21980 | gold | derived | supply_chain |
| gold_stockout_risk_scores_history | MANAGED | 65858 | gold | derived | supply_chain |
| gold_store_item_daily | MATERIALIZED_VIEW | 59242070 | gold | derived | supply_chain |
| gold_supplier_performance_weekly | MATERIALIZED_VIEW | 567 | gold | derived | supply_chain |
| osa_access_entitlements | MANAGED | 3 |  | derived | supply_chain |
| replenishment_actions | MANAGED | 3 | gold | derived | supply_chain |
| silver_calendar | MATERIALIZED_VIEW | 1969 | silver | public_m5 | supply_chain |
| silver_inventory_snapshots | MATERIALIZED_VIEW | 5549173 | silver | synthetic | supply_chain |
| silver_po_events | STREAMING_TABLE | 1400862 | silver | synthetic | supply_chain |
| silver_purchase_orders | MATERIALIZED_VIEW | 708458 | silver | synthetic | supply_chain |
| silver_sales_daily | STREAMING_TABLE | 59242070 | silver | public_m5 | supply_chain |
| silver_sell_prices | MATERIALIZED_VIEW | 6841121 | silver | public_m5 | supply_chain |