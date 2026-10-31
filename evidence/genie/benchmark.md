# Genie Agent benchmark — space `01f1d4b044db1d4d988e71d91e6decbd`

*Run 2026-10-31 00:36 UTC via the Genie Conversation API.*

**Exact result-set match vs reference SQL: 7/8** · **same answer (reference columns all present, extra columns allowed): 8/8** (numeric values compared at 0.1 precision, row order ignored). 2 additional open-ended questions shown for answer quality.

## What was the overall on-shelf availability last week?

*Genie status: COMPLETED · 14.3s · exact match ✅*

**Genie answer:** You want to see the on-shelf availability percentage and lost revenue broken down by region for last week compared to the prior week.Would you prefer to see the on-shelf availability and lost revenue by region for the last 14 days as a single period instead of splitting into last week and prior week?The overall on-shelf availability for **last week** was **93.79%**. Based on the 7-day period ending on the latest date in the data, items were available on shelf for just under **94%** of active store-item checks.

**Genie SQL:**

```sql
WITH `mx` AS (
  SELECT MAX(`date`) AS `d`
  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`
)
SELECT ROUND(100 * (1 - try_divide(SUM(`k`.`oos_store_items`),SUM(`k`.`active_store_items`))), 2) AS `overall_osa_pct`
FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily` AS `k`
CROSS JOIN `mx`
WHERE `k`.`date` BETWEEN date_sub(`mx`.`d`, 6) AND `mx`.`d`
```

**Genie result:**

| overall_osa_pct |
|---|
| 93.79 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2) AS osa_pct FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily WHERE date > (SELECT max(date) FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily) - INTERVAL 7 DAYS
```

| osa_pct |
|---|
| 93.79 |

</details>

## How much revenue was lost to stockouts in the South region in the last 28 days?

*Genie status: COMPLETED · 14.5s · exact match ✅*

**Genie answer:** You want to see which stores lost the most revenue due to stockouts in the last 28 days, along with their regions and on-shelf availability percentages.In the **South** region, revenue lost to stockouts over the last **28 days** was **$51,935**. Based on the single result returned, the total lost revenue for the period is **$51,935**.

**Genie SQL:**

```sql
SELECT ROUND(SUM(`lost_revenue`)) AS `lost_revenue`
FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`
WHERE `region` = 'South'
  AND `date` > (SELECT MAX(`date`) FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`) - INTERVAL 28 DAYS
```

**Genie result:**

| lost_revenue |
|---|
| 51935.0 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT round(sum(lost_revenue)) AS lost_revenue FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily WHERE region = 'South' AND date > (SELECT max(date) FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily) - INTERVAL 28 DAYS
```

| lost_revenue |
|---|
| 51935.0 |

</details>

## How many stockout events by root cause since 2015-11-25?

*Genie status: COMPLETED · 13.4s · exact match ✅*

**Genie answer:** You want to see the number of stockout events broken down by their root cause since November 25, 2015.Since **2015-11-25**, there are **4** root causes shown for stockout events: - **SUPPLIER_DELAY:** **37,723** - **PHANTOM_INVENTORY:** **12,349** - **UNEXPLAINED:** **13** - **DEMAND_SPIKE:** **6**  Stockouts are overwhelmingly driven by **supplier delays** and **phantom inventory**, with the other causes appearing only rarely in the visible data.

**Genie SQL:**

```sql
SELECT `root_cause`, COUNT(*) AS `stockout_events`
FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_stockout_events`
WHERE `start_date` >= DATE '2015-11-25'
  AND `root_cause` IS NOT NULL
GROUP BY `root_cause`
ORDER BY `stockout_events` DESC, `root_cause`
```

**Genie result:**

| root_cause | stockout_events |
|---|---|
| SUPPLIER_DELAY | 37723 |
| PHANTOM_INVENTORY | 12349 |
| UNEXPLAINED | 13 |
| DEMAND_SPIKE | 6 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT root_cause, count(*) AS events FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_stockout_events WHERE start_date >= '2015-11-25' GROUP BY root_cause ORDER BY events DESC
```

| root_cause | events |
|---|---|
| SUPPLIER_DELAY | 37723 |
| PHANTOM_INVENTORY | 12349 |
| UNEXPLAINED | 13 |
| DEMAND_SPIKE | 6 |

</details>

## Which department has the lowest availability in the last 7 days?

*Genie status: COMPLETED · 19.2s · exact match ✅*

**Genie answer:** You want to find the department with the lowest on-shelf availability percentage over the last 7 days.In the last 7 days, **HOBBIES_2 (Party & Seasonal)** had the lowest availability at **89.27%**. Based on the result shown, **HOBBIES_2** was the lowest-performing department for availability over that 7-day period.

**Genie SQL:**

```sql
WITH `mx` AS (
  SELECT MAX(`date`) AS `max_date`
  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`
),
`dept_osa` AS (
  SELECT
    `dept_id`,
    ROUND(100 * (1 - try_divide(SUM(`oos_store_items`),SUM(`active_store_items`))), 2) AS `availability_pct`
  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`
  CROSS JOIN `mx`
  WHERE `date` BETWEEN date_sub(`mx`.`max_date`, 6) AND `mx`.`max_date`
    AND `dept_id` IS NOT NULL
  GROUP BY `dept_id`
),
`ranked` AS (
  SELECT
    `dept_id`,
    `availability_pct`,
    RANK() OVER (ORDER BY `availability_pct` ASC) AS `rnk`
  FROM `dept_osa`
)
SELECT `dept_id`, `availability_pct`
FROM `ranked`
WHERE `rnk` = 1
ORDER BY `dept_id`
```

**Genie result:**

| dept_id | availability_pct |
|---|---|
| HOBBIES_2 | 89.27 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT dept_id, round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2) AS osa_pct FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily WHERE date > (SELECT max(date) FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily) - INTERVAL 7 DAYS GROUP BY dept_id ORDER BY osa_pct ASC LIMIT 1
```

| dept_id | osa_pct |
|---|---|
| HOBBIES_2 | 89.27 |

</details>

## How many critical alerts are there tonight per store?

*Genie status: COMPLETED · 19.8s · exact match ✅*

**Genie answer:** You want to see the number of critical alerts for tonight, broken down by each store, ordered from the store with the most critical alerts to the least.Tonight, there are **10 stores** with critical alerts, ranging from **23** to **45** alerts per store. Examples include: - **WI_3**: **45** - **TX_2**: **40** - **CA_1**: **35** - **WI_2**: **35** - **CA_2**: **34** The highest count is **WI_3** with **45** critical alerts, while the lowest shown is **CA_4** with **23**.

**Genie SQL:**

```sql
SELECT `store_id`, COUNT(*) AS `critical_alerts`
FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_replenishment_recommendations`
WHERE `risk_tier` = 'CRITICAL'
  AND `store_id` IS NOT NULL
  AND `score_date` = (
    SELECT MAX(`score_date`)
    FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_replenishment_recommendations`
  )
GROUP BY `store_id`
ORDER BY `critical_alerts` DESC, `store_id`
```

**Genie result:**

| store_id | critical_alerts |
|---|---|
| WI_3 | 45 |
| TX_2 | 40 |
| CA_1 | 35 |
| WI_2 | 35 |
| CA_2 | 34 |
| CA_3 | 34 |
| TX_3 | 25 |
| TX_1 | 24 |
| WI_1 | 24 |
| CA_4 | 23 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT store_id, count(*) AS critical_alerts FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_replenishment_recommendations WHERE risk_tier = 'CRITICAL' GROUP BY store_id ORDER BY critical_alerts DESC
```

| store_id | critical_alerts |
|---|---|
| WI_3 | 45 |
| TX_2 | 40 |
| WI_2 | 35 |
| CA_1 | 35 |
| CA_3 | 34 |
| CA_2 | 34 |
| TX_3 | 25 |
| TX_1 | 24 |
| WI_1 | 24 |
| CA_4 | 23 |

</details>

## What was total revenue by year?

*Genie status: COMPLETED · 32.9s · exact match ✅*

**Genie answer:** You want to see the total revenue for each year from the sales data.Total revenue by year was **$23,891,336** in **2011**, **$32,649,201** in **2012**, **$35,923,373** in **2013**, **$37,861,913** in **2014**, **$42,416,457** in **2015**, and **$19,083,411** in **2016**. Revenue increased each year from **2011** through **2015**, with **2015** the highest and **2016** lower than prior years in the data shown.

**Genie SQL:**

```sql
SELECT YEAR(`date`) AS `year`, ROUND(SUM(`revenue`)) AS `total_revenue`
FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_store_item_daily`
WHERE `date` IS NOT NULL
GROUP BY YEAR(`date`)
ORDER BY `year` ASC
```

**Genie result:**

| year | total_revenue |
|---|---|
| 2011 | 2.3891336E7 |
| 2012 | 3.2649201E7 |
| 2013 | 3.5923373E7 |
| 2014 | 3.7861913E7 |
| 2015 | 4.2416457E7 |
| 2016 | 1.9083411E7 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT year(date) AS year, round(sum(revenue)) AS revenue FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_osa_kpi_daily GROUP BY 1 ORDER BY 1
```

| year | revenue |
|---|---|
| 2011 | 2.3891336E7 |
| 2012 | 3.2649201E7 |
| 2013 | 3.5923373E7 |
| 2014 | 3.7861913E7 |
| 2015 | 4.2416457E7 |
| 2016 | 1.9083411E7 |

</details>

## Which C-tier suppliers missed their on-time SLA most often in 2016?

*Genie status: COMPLETED · 19.5s · same answer, extra columns ✅*

**Genie answer:** You want to see the ranking of C-tier suppliers based on how many weeks they missed their on-time SLA during 2016.In 2016, **4 C-tier suppliers** tied for missing their on-time SLA most often, with **21 missed weeks** each. The suppliers were **Brightline Toys & Crafts**, **Harvest Lane Grocers Supply**, **Lakeshore Beverage Group**, and **Prime Valley Distribution**; across the full 4-row result, they were all tied at the same highest miss count.

**Genie SQL:**

```sql
WITH `supplier_misses` AS (
  SELECT
    `supplier_id`,
    `supplier_name`,
    `reliability_tier`,
    SUM(CASE WHEN `meets_on_time_sla` = false THEN 1 ELSE 0 END) AS `sla_miss_weeks`
  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_supplier_performance_weekly`
  WHERE `reliability_tier` = 'C'
    AND `week_start` >= DATE '2016-01-01'
    AND `week_start` < DATE '2017-01-01'
    AND `supplier_id` IS NOT NULL
    AND `supplier_name` IS NOT NULL
  GROUP BY `supplier_id`, `supplier_name`, `reliability_tier`
), `ranked` AS (
  SELECT
    `supplier_id`,
    `supplier_name`,
    `reliability_tier`,
    `sla_miss_weeks`,
    RANK() OVER (ORDER BY `sla_miss_weeks` DESC, `supplier_name` ASC) AS `supplier_rank`
  FROM `supplier_misses`
)
SELECT
  `supplier_rank`,
  `supplier_id`,
  `supplier_name`,
  `reliability_tier`,
  `sla_miss_weeks`
FROM `ranked`
ORDER BY `supplier_rank` ASC, `supplier_name` ASC;
```

**Genie result:**

| supplier_rank | supplier_id | supplier_name | reliability_tier | sla_miss_weeks |
|---|---|---|---|---|
| 1 | SUP011 | Brightline Toys & Crafts | C | 21 |
| 2 | SUP004 | Harvest Lane Grocers Supply | C | 21 |
| 3 | SUP010 | Lakeshore Beverage Group | C | 21 |
| 4 | SUP009 | Prime Valley Distribution | C | 21 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT supplier_name, count(*) AS weeks_missed FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_supplier_performance_weekly WHERE reliability_tier = 'C' AND NOT meets_on_time_sla AND week_start >= '2016-01-01' GROUP BY supplier_name ORDER BY weeks_missed DESC
```

| supplier_name | weeks_missed |
|---|---|
| Prime Valley Distribution | 21 |
| Lakeshore Beverage Group | 21 |
| Brightline Toys & Crafts | 21 |
| Harvest Lane Grocers Supply | 21 |

</details>

## What is the total revenue at risk over the next 3 days across all open alerts?

*Genie status: COMPLETED · 19.2s · exact match ✅*

**Genie answer:** You want to see the total expected revenue at risk over the next 3 days from all open alerts in the replenishment recommendations.The total revenue at risk over the next 3 days is **$13,900** based on all records with a non-null 3-day revenue-at-risk value. This result reflects the full returned dataset of **1 aggregated row**.

**Genie SQL:**

```sql
SELECT ROUND(SUM(`revenue_at_risk_3d`)) AS `total_revenue_at_risk_3d`
FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_replenishment_recommendations`
WHERE `revenue_at_risk_3d` IS NOT NULL
```

**Genie result:**

| total_revenue_at_risk_3d |
|---|
| 13900.0 |

<details><summary>Reference SQL and result</summary>

```sql
SELECT round(sum(revenue_at_risk_3d)) AS revenue_at_risk FROM serverless_stable_4hkk7k_catalog.osa_retail.gold_replenishment_recommendations
```

| revenue_at_risk |
|---|
| 13900.0 |

</details>

## Which South region stores have the lowest availability last week, and how much revenue did they lose?

*Genie status: COMPLETED · 19.4s · open question (no reference SQL)*

**Genie answer:** You want to find the South region stores that had the lowest on-shelf availability last week and see how much revenue they lost due to stockouts.In the **South** region last week, **store TX_3** had the lowest availability at **93.33%** and lost **$3,539** in revenue. Based on the result shown, **TX_3** is the lowest-availability South store for that period.

**Genie SQL:**

```sql
WITH `mx` AS (
  SELECT MAX(`date`) AS `max_date`
  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`
),
`store_week` AS (
  SELECT
    `store_id`,
    `region`,
    ROUND(100 * (1 - try_divide(SUM(`oos_store_items`),SUM(`active_store_items`))), 2) AS `osa_pct`,
    ROUND(SUM(`lost_revenue`)) AS `lost_revenue`
  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_osa_kpi_daily`
  CROSS JOIN `mx`
  WHERE `region` = 'South'
    AND `store_id` IS NOT NULL
    AND `region` IS NOT NULL
    AND `date` > `mx`.`max_date` - INTERVAL 7 DAYS
  GROUP BY `store_id`, `region`
),
`ranked` AS (
  SELECT
    `store_id`,
    `region`,
    `osa_pct`,
    `lost_revenue`,
    RANK() OVER (ORDER BY `osa_pct` ASC, `lost_revenue` DESC) AS `rnk`
  FROM `store_week`
)
SELECT
  `store_id`,
  `region`,
  `osa_pct`,
  `lost_revenue`
FROM `ranked`
WHERE `rnk` = 1
ORDER BY `store_id`
```

**Genie result:**

| store_id | region | osa_pct | lost_revenue |
|---|---|---|---|
| TX_3 | South | 93.33 | 3539.0 |

## What share of stockouts since November 2015 were caused by phantom inventory vs supplier delays?

*Genie status: COMPLETED · 19.1s · open question (no reference SQL)*

**Genie answer:** You want to see the share of stockouts since November 25, 2015, that were caused by phantom inventory compared to those caused by supplier delays.Since **2015-11-25**, **supplier delays** accounted for **75.31%** of stockouts (**37,723** events), while **phantom inventory** accounted for **24.65%** (**12,349** events). In this period, supplier delays made up about **three times** the share of phantom-inventory stockouts.

**Genie SQL:**

```sql
WITH `base` AS (
  SELECT `root_cause`
  FROM `serverless_stable_4hkk7k_catalog`.`osa_retail`.`gold_stockout_events`
  WHERE `start_date` >= DATE '2015-11-25'
    AND `root_cause` IS NOT NULL
),
`totals` AS (
  SELECT COUNT(*) AS `total_stockouts`
  FROM `base`
)
SELECT
  `base`.`root_cause`,
  COUNT(*) AS `stockout_count`,
  ROUND(try_divide(100 * COUNT(*),`totals`.`total_stockouts`), 2) AS `stockout_share_pct`
FROM `base`
CROSS JOIN `totals`
WHERE `base`.`root_cause` IN ('PHANTOM_INVENTORY', 'SUPPLIER_DELAY')
GROUP BY `base`.`root_cause`, `totals`.`total_stockouts`
ORDER BY `stockout_share_pct` DESC
```

**Genie result:**

| root_cause | stockout_count | stockout_share_pct |
|---|---|---|
| SUPPLIER_DELAY | 37723 | 75.31 |
| PHANTOM_INVENTORY | 12349 | 24.65 |
