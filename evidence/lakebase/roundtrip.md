# Lakebase round-trip evidence

*2026-10-31 00:48 UTC*

1. Gold Delta tables are **synced** into Lakebase Postgres (`osa_lakebase.serving.*`).
2. The app's service principal **writes** store decisions transactionally into its own Postgres schema (`osa_app.replenishment_actions`).
3. Because the Lakebase database is registered as Unity Catalog catalog `osa_lakebase`, the nightly job reads those rows with SQL and MERGEs them into governed Delta (`replenishment_actions`).

## Synced serving tables: Delta source vs Lakebase Postgres row counts

```sql
SELECT 'replenishment_recommendations' AS lakebase_table, (SELECT count(*) FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_replenishment_recommendations) AS delta_rows,
                    (SELECT count(*) FROM osa_lakebase.serving.replenishment_recommendations) AS postgres_rows
             UNION ALL SELECT 'stockout_risk_scores', (SELECT count(*) FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_risk_scores),
                    (SELECT count(*) FROM osa_lakebase.serving.stockout_risk_scores)
             UNION ALL SELECT 'intelligence_reports', (SELECT count(*) FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_intelligence_reports),
                    (SELECT count(*) FROM osa_lakebase.serving.intelligence_reports)
```

| lakebase_table | delta_rows | postgres_rows |
|---|---|---|
| replenishment_recommendations | 1168 | 1168 |
| stockout_risk_scores | 21980 | 21980 |
| intelligence_reports | 12 | 12 |

## Decisions written by the app — read live from Postgres through the UC catalog

```sql
SELECT action_id, rec_id, action, final_qty, reason_code, note, decided_by, decided_at, recommended_qty, risk_tier FROM osa_lakebase.osa_app.replenishment_actions ORDER BY decided_at
```

| action_id | rec_id | action | final_qty | reason_code | note | decided_by | decided_at | recommended_qty | risk_tier |
|---|---|---|---|---|---|---|---|---|---|
| 84924557-2b58-4a92-9c18-e8b9006c9f47 | CA_3\|FOODS_1_170\|2016-05-23 | APPROVE | 4 |  |  | aradhya.chouhan@databricks.com | 2026-10-31T00:14:26.779Z | 4 | CRITICAL |
| 6b256dbe-111d-4af8-b973-f6926bb01c6f | WI_2\|FOODS_2_029\|2016-05-23 | OVERRIDE | 73 | LOCAL_EVENT | Memorial Day cook-out at the community park | aradhya.chouhan@databricks.com | 2026-10-31T00:14:27.113Z | 36 | CRITICAL |
| a0936b44-8d1d-4ea6-a45e-11667be9b0ec | CA_3\|FOODS_2_183\|2016-05-23 | REJECT | 0 |  | item being delisted next week | aradhya.chouhan@databricks.com | 2026-10-31T00:14:27.766Z | 4 | CRITICAL |
| 1428b347-0301-4338-8a30-f8e3b825c0bc | CA_3\|FOODS_1_170\|2016-05-24 | APPROVE | 4 |  |  | aradhya.chouhan@databricks.com | 2026-10-31T00:47:16.034Z | 4 | CRITICAL |
| f24a2e40-6508-4fac-ae2e-155a15abbbf5 | WI_2\|FOODS_2_029\|2016-05-24 | OVERRIDE | 73 | LOCAL_EVENT | Memorial Day cook-out at the community park | aradhya.chouhan@databricks.com | 2026-10-31T00:47:16.393Z | 36 | CRITICAL |
| ac152259-f705-4a57-8bee-682c563fb7cc | CA_3\|FOODS_2_183\|2016-05-24 | REJECT | 0 |  | item being delisted next week | aradhya.chouhan@databricks.com | 2026-10-31T00:47:17.064Z | 16 | CRITICAL |

## Same decisions after the nightly MERGE into governed Delta

```sql
SELECT action_id, rec_id, action, final_qty, reason_code, decided_by, decided_at, ingested_at FROM serverless_stable_4hkk7k_catalog.osa_retail.replenishment_actions ORDER BY decided_at
```

| action_id | rec_id | action | final_qty | reason_code | decided_by | decided_at | ingested_at |
|---|---|---|---|---|---|---|---|
| 84924557-2b58-4a92-9c18-e8b9006c9f47 | CA_3\|FOODS_1_170\|2016-05-23 | APPROVE | 4 |  | aradhya.chouhan@databricks.com | 2026-10-31T00:14:26.779Z | 2026-10-31T00:20:45.535Z |
| 6b256dbe-111d-4af8-b973-f6926bb01c6f | WI_2\|FOODS_2_029\|2016-05-23 | OVERRIDE | 73 | LOCAL_EVENT | aradhya.chouhan@databricks.com | 2026-10-31T00:14:27.113Z | 2026-10-31T00:20:45.535Z |
| a0936b44-8d1d-4ea6-a45e-11667be9b0ec | CA_3\|FOODS_2_183\|2016-05-23 | REJECT | 0 |  | aradhya.chouhan@databricks.com | 2026-10-31T00:14:27.766Z | 2026-10-31T00:20:45.535Z |

## Alert response KPI computed from the merged decisions

```sql
SELECT r.score_date, r.risk_tier, count(*) AS alerts, count(a.action_id) AS actioned
             FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_replenishment_recommendations r LEFT JOIN serverless_stable_4hkk7k_catalog.osa_retail.replenishment_actions a ON a.rec_id = r.rec_id
             GROUP BY ALL ORDER BY 1, 2
```

| score_date | risk_tier | alerts | actioned |
|---|---|---|---|
| 2016-05-24 | CRITICAL | 319 | 0 |
| 2016-05-24 | HIGH | 112 | 0 |
| 2016-05-24 | OOS_NOW | 586 | 0 |
| 2016-05-24 | OOS_PHANTOM | 151 | 0 |
