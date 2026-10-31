# Governance proof: same queries, two identities

*Generated 2026-10-31 00:33:29 UTC against `serverless_stable_4hkk7k_catalog.osa_retail` on warehouse `e0a8cc3b322c1f1d`.*

* **ADMIN** – the build identity (entitlement `ADMIN`).
* **PERSONA** – service principal `osa-demo-south-store-manager` (`8e31f1c1-5055-49b6-9a53-5903b724ef03`), entitlement `REGION:South`, SELECT on curated gold/dim tables only.

Policies: `fn_region_filter` (row filter on `region`), `fn_mask_commercial_*`, `fn_mask_email` (column masks), all driven by the `osa_access_entitlements` table.

## Who am I

```sql
SELECT current_user() AS identity
```

**ADMIN:**

| identity |
|---|
| aradhya.chouhan@databricks.com |

**PERSONA (South store manager):**

| identity |
|---|
| 8e31f1c1-5055-49b6-9a53-5903b724ef03 |

## Row filter: regional KPI rows visible per region (gold_osa_kpi_daily)

```sql
SELECT region, count(*) AS rows, round(sum(lost_revenue)) AS lost_revenue FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily GROUP BY region ORDER BY region
```

**ADMIN:**

| region | rows | lost_revenue |
|---|---|---|
| Midwest | 40803 | 3680862.0 |
| South | 40803 | 3831367.0 |
| West | 54404 | 6337374.0 |

**PERSONA (South store manager):**

| region | rows | lost_revenue |
|---|---|---|
| South | 40803 | 3831367.0 |

## Row filter: stockout events visible per region (gold_stockout_events)

```sql
SELECT region, count(*) AS events FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_events GROUP BY region ORDER BY region
```

**ADMIN:**

| region | events |
|---|---|
| Midwest | 120863 |
| South | 129474 |
| West | 194306 |

**PERSONA (South store manager):**

| region | events |
|---|---|
| South | 129474 |

## Column masks: supplier commercial terms (dim_supplier)

```sql
SELECT supplier_id, supplier_name, late_penalty_pct_of_po, payment_terms, account_manager_email FROM serverless_stable_4hkk7k_catalog.osa_retail.dim_supplier ORDER BY supplier_id LIMIT 4
```

**ADMIN:**

| supplier_id | supplier_name | late_penalty_pct_of_po | payment_terms | account_manager_email |
|---|---|---|---|---|
| SUP001 | Golden Prairie Dairy Co | 1.0 | NET30 | am.golden@golden-supply.example |
| SUP002 | Riverbend Fresh Foods | 1.5 | NET45 | am.riverbend@riverbend-supply.example |
| SUP003 | Sunvale Bakery Partners | 1.0 | NET60 | am.sunvale@sunvale-supply.example |
| SUP004 | Harvest Lane Grocers Supply | 2.0 | NET30 | am.harvest@harvest-supply.example |

**PERSONA (South store manager):**

| supplier_id | supplier_name | late_penalty_pct_of_po | payment_terms | account_manager_email |
|---|---|---|---|---|
| SUP001 | Golden Prairie Dairy Co |  | ***RESTRICTED*** | ****@golden-supply.example |
| SUP002 | Riverbend Fresh Foods |  | ***RESTRICTED*** | ****@riverbend-supply.example |
| SUP003 | Sunvale Bakery Partners |  | ***RESTRICTED*** | ****@sunvale-supply.example |
| SUP004 | Harvest Lane Grocers Supply |  | ***RESTRICTED*** | ****@harvest-supply.example |

## Column masks: item cost + store manager e-mail

```sql
SELECT i.item_id, i.negotiated_cost_ratio, s.store_id, s.store_manager_email FROM serverless_stable_4hkk7k_catalog.osa_retail.dim_item i CROSS JOIN serverless_stable_4hkk7k_catalog.osa_retail.dim_store s WHERE i.item_id = 'FOODS_3_090' AND s.store_id IN ('CA_1', 'TX_1') ORDER BY s.store_id
```

**ADMIN:**

| item_id | negotiated_cost_ratio | store_id | store_manager_email |
|---|---|---|---|
| FOODS_3_090 | 0.728 | CA_1 | maria.alvarez@osa-demo-retail.example |
| FOODS_3_090 | 0.728 | TX_1 | aisha.nguyen@osa-demo-retail.example |

**PERSONA (South store manager):**

| item_id | negotiated_cost_ratio | store_id | store_manager_email |
|---|---|---|---|
| FOODS_3_090 |  | CA_1 | ****@osa-demo-retail.example |
| FOODS_3_090 |  | TX_1 | ****@osa-demo-retail.example |

## No grant: bronze table is not readable by the persona

```sql
SELECT count(*) AS n FROM serverless_stable_4hkk7k_catalog.osa_retail.bronze_erp_suppliers
```

**ADMIN:**

| n |
|---|
| 21 |

**PERSONA (South store manager):**

```text
DENIED / ERROR: [INSUFFICIENT_PERMISSIONS] Insufficient privileges:
Principal 'osa-demo-south-store-manager' does not have SELECT on Table 'serverless_stable_4hkk7k_catalog.osa_retail.bronze_erp_suppliers'. SQLSTATE: 42501
```
