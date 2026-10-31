# Nightly intelligence briefings (agent output)

*Exported 2026-10-31 00:48 UTC from `serverless_stable_4hkk7k_catalog.osa_retail.gold_intelligence_reports` — the same rows the app serves from Lakebase `serving.intelligence_reports`. Each was written by the tool-calling briefing agent; `tools` lists the governed tools it chose to call; `trace` is the MLflow trace id.*

---

## Executive OSA briefing — 2016-05-24

*executive · ALL · databricks-claude-sonnet-5-5 · 28.6s · generated 2026-10-31T00:35:00.966Z · trace `tr-0e52cc9f8c62d05a0d3e4df4865b03d8`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
OSA improved to 93.79% and lost revenue fell to $39,174, down $11,504 (-22.7%) week over week. Tonight's queue still has $13,899 of 3-day revenue at risk across 1,168 items. Emergency DSD accounts for $8,808 of that.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.79% | 92.00% | +1.79 pts |
| Revenue | $953,628 | $1,020,469 | -$66,841 (-6.5%) |
| Lost revenue | $39,174 | $50,678 | -$11,504 (-22.7%) |
| Lost sales rate | 3.95% | 4.73% | -0.78 pts |
| OOS store-item-days | 9,539 | 12,183 | -2,644 |

Total revenue is down 6.5% even though availability improved, so the cause is probably demand or traffic rather than stockouts.

## Top risks tonight
- **TX_2, Great Value Tortilla Chips #120:** expedited order of 24 units, $237.05 at risk. It has 0 on hand despite 217 on order, so chase the inbound PO.
- **CA_3, Equate Cheddar Block #170:** emergency DSD of 4 units, $174.59 at risk. Stockout probability is 99%.
- **WI_2, Hearth & Home Cereal #029:** emergency DSD of 36 units, $149.98 at risk. The supplier PO is 2 days overdue.
- **WI_2, Parent's Choice Peanut Butter #316:** emergency DSD of 8 units, $131.08 at risk. The PO is 5 days late.
- **TX_3, Great Value Pasta #368:** emergency DSD of 24 units, $109.39 at risk.

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 383 stockouts, $10,897 lost, 58 still ongoing, 6.48 days late on average.
- **SUP010 Lakeshore Beverage Group (tier C):** 433 stockouts (the most of any supplier), $10,161 lost, 59 ongoing.
- **SUP018 Polaris Paper & Plastics (tier B):** $10,231 lost, 6.94 days late on average.

## Recommended actions
1. **Store managers (CA_3, WI_2, TX_3):** Submit emergency DSD requests for the 630 CRITICAL and OOS_NOW items before the 2:00 pm cut-off. Later requests arrive in two days. Only FOODS and HOUSEHOLD_1 items are eligible, and the cost is an 8% premium plus a $45 per store per day fee (GUIDE-DSD-005).
2. **Category buyers:** Make the call on late POs that are 2 or more days overdue, and open a sourcing review for SUP009, SUP010 and SUP018 (POL-SUP-003). This covers 187 items in the expedite-and-escalate and verify-shelf tiers.
3. **TX_2 store manager:** Trace the 217 units on order for Tortilla Chips #120 and place the 24-unit expedited order (POL-SUP-003).
4. **Store associates:** Physically count the 151 phantom-inventory items (OOS_PHANTOM, $1,826 at risk) within 24 hours. Managers adjust ERP the same day. If a count is zero, they place an emergency order. Adjustments of $500 or more at cost need Regional Manager sign-off (GUIDE-DSD-005).

---

## Midwest region OSA briefing — 2016-05-24

*regional · Midwest · databricks-claude-sonnet-5-5 · 39.1s · generated 2026-10-31T00:35:00.966Z · trace `tr-a4b93621116799d7c81a53e91a68de6b`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies → search_policies*

## Headline
Midwest OSA improved to 94.22% and lost revenue fell to $10,496, down $2,088 from the prior 7 days. Tonight's queue still has 342 items with $4,343 of 3-day revenue at risk, and 201 of those are OOS_NOW or CRITICAL items routed to Emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 94.22% | 93.08% | +1.14 pts |
| Revenue | $253,501 | $301,019 | -$47,518 (-15.8%) |
| Lost revenue | $10,496 | $12,584 | -$2,088 (-16.6%) |
| Lost-sales rate | 3.98% | 4.01% | -0.03 pts |
| OOS store-item-days | 2,566 | 3,057 | -491 |

Revenue fell almost as much as lost revenue, so part of the lost-revenue improvement may come from lower sales, not just better availability.

## Top risks tonight
- **WI_2, Hearth & Home Cereal #029:** Emergency DSD, 36 units, $149.98 at risk. It is CRITICAL with 0 on hand and a PO 2 days overdue.
- **WI_2, Parent's Choice Peanut Butter #316:** Emergency DSD, 8 units, $131.08 at risk. It is out of stock and the PO is 5 days late.
- **WI_1, Equate Black Beans #282:** Emergency DSD, 16 units, $78.62 at risk. It is out of stock and the PO is 3 days late.
- **WI_2, Mainstays Rice #251:** Expedited order, 16 units, $72.67 at risk.
- **WI_2, Great Value Dish Soap #488:** Emergency DSD, 24 units, $70.54 at risk. The PO is 2 days overdue.

WI_2 accounts for four of the five top items.

## Supplier watch
- **SUP009 Prime Valley Distribution (Tier C):** 110 stockouts, $3,290 lost, 15 still ongoing, average 6.38 days late.
- **SUP010 Lakeshore Beverage Group (Tier C):** 143 stockouts, $3,114 lost, 18 still ongoing, average 5.8 days late.
- **SUP007 Northstar Snacks & Beverage (Tier B):** 113 stockouts, $2,992 lost, 21 ongoing (the most in the region), average 6.04 days late.

## Recommended actions
1. **WI_2 and WI_1 store managers:** Submit the Emergency DSD orders above before the 2:00 pm local cut-off for next-morning delivery. All four items are in eligible departments (GUIDE-DSD-005).
2. **Category buyers:** Call the supplier account managers for the POs that are 2 or more days late, including the cereal, peanut butter, black beans and dish soap POs. Open a sourcing review for any supplier at 3+ days late or with 2+ stockouts in a week. SUP009, SUP010 and SUP007 all qualify on average lateness (late-PO escalation ladder; the search did not return its document ID).
3. **Procurement:** Charge the 8% Emergency DSD premium back to suppliers where a late PO is the root cause (POL-SUP-003).
4. **Store associates:** Physically count the 38 suspected-phantom items ($536 at risk) within 24 hours. Store managers adjust the ERP the same day and reorder if the count is zero. Adjustments of $500 or more at cost need Regional Manager sign-off within 2 business days (phantom-inventory cycle count procedure; the search did not return its document ID).
5. **Regional Manager:** Review Tier C status for SUP009 and SUP010 (POL-SUP-003).

---

## South region OSA briefing — 2016-05-24

*regional · South · databricks-claude-sonnet-5-5 · 25.3s · generated 2026-10-31T00:35:00.966Z · trace `tr-2a4bb4d185bc3bb6c7ea69d98826e2a7`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
South OSA improved to 93.75% and lost revenue fell to $9,726, down $4,255 from the prior week. Tonight's queue still has 336 alerts with about $3,474 of 3-day revenue at risk, and 113 of them are out-of-stock items that need Emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.75 | 91.34 | +2.41 pts |
| Revenue | $269,466 | $283,516 | -$14,050 (-5.0%) |
| Lost revenue | $9,726 | $13,981 | -$4,255 (-30.4%) |
| Lost sales rate | 3.48% | 4.70% | -1.22 pts |
| OOS store-item-days | 2,718 | 3,736 | -1,018 |

## Top risks tonight
- **TX_2, Great Value Tortilla Chips #120:** Expedited order, 24 units, $237.05 at risk. It has 0 on hand despite 217 on order, so chase that PO.
- **TX_3, Great Value Pasta #368:** Emergency DSD, 24 units, $109.39 at risk. One PO is overdue.
- **TX_1, Marketside Surface Cleaner #497:** Expedited order, 8 units, $108.71 at risk. Order from Polaris Paper & Plastics.
- **TX_2, Equate Black Beans #194:** Emergency DSD, 8 units, $56.35 at risk. Stockout probability is 97%.
- **TX_2, Northpeak Juice #695:** Emergency DSD, 8 units, $53.73 at risk. Its PO is 3 days late.

TX_2 accounts for three of the five top risks.

## Supplier watch
- **Polaris Paper & Plastics (SUP018, tier B):** 85 stockouts, $3,459 lost, 4 ongoing, 7.05 days late on average.
- **CleanWave Home Products (SUP016, tier A):** 116 stockouts, $3,128 lost, 8 ongoing.
- **Lakeshore Beverage Group (SUP010, tier C):** 118 stockouts, $2,779 lost, 18 ongoing, the most of any supplier. It has the most stockouts of the three.

## Recommended actions
1. **TX_2, TX_3 store managers:** Submit the Emergency DSD requests (pasta, black beans, juice) by 2:00 pm local so they arrive next morning. Later requests take two days, and DSD carries an 8% premium plus a $45 flat fee per store per day (GUIDE-DSD-005).
2. **Category buyers:** Call the buyer on any PO that is 2 or more days late, which includes the Northpeak Juice PO. Open a sourcing review for Polaris, CleanWave and Lakeshore, since each has 2 or more attributed stockouts in a week (POL-SUP-003).
3. **TX_2 and TX_1 managers:** Place the expedited orders for tortilla chips and surface cleaner, and confirm the delivery date of the 217 units on order for the chips (POL-SUP-003).
4. **Store associates, with managers:** Cycle-count the 39 phantom-inventory items within 24 hours. The manager adjusts the ERP record the same day and orders immediately if the count is 0 (GUIDE-DSD-005).
5. **Regional ops lead:** Review the South supplier tiers. Polaris, CleanWave and Lakeshore each have large late-PO losses, and CleanWave is tier A despite 116 stockouts (POL-SUP-003).

---

## West region OSA briefing — 2016-05-24

*regional · West · databricks-claude-sonnet-5-5 · 29.9s · generated 2026-10-31T00:35:00.966Z · trace `tr-c6d00e561b3614b3f75d7b54c1570190`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
West OSA improved to 93.53%, and lost revenue fell to $18,952 from $24,113 the prior week. 490 items are still flagged tonight, with $6,082 of 3-day revenue at risk. 257 of those items, worth $3,753, need emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.53% | 91.71% | +1.82 pts |
| Revenue | $430,661 | $435,934 | -$5,273 (-1.2%) |
| Lost revenue | $18,952 | $24,113 | -$5,161 (-21.4%) |
| Lost sales rate | 4.22% | 5.24% | -1.02 pts |
| OOS store-item-days | 4,255 | 5,390 | -1,135 |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** emergency DSD, 4 units, $174.59 at risk. It has 0 on hand and demand of 10.4 units/day.
- **CA_3, Northpeak Soup #183:** emergency DSD, 16 units, $99.91 at risk. It has an overdue PO.
- **CA_1, Equate Cola 12pk #682:** emergency DSD, 48 units, $89.10 at risk. Its PO is 1 day overdue.
- **CA_3, Great Value Dish Soap #488:** emergency DSD, 24 units, $75.37 at risk. Its supplier delivery is overdue.
- **CA_1, Sunny Fields Coffee #574:** emergency DSD, 12 units, $68.57 at risk. It is out of stock and its PO is 11 days overdue from Prime Valley.

CA_3 has three of the five top items.

## Supplier watch
- **Prime Valley Distribution (SUP009, tier C):** 177 stockouts, $5,103 lost, 32 still ongoing, 6.12 days late on average.
- **Polaris Paper & Plastics (SUP018, tier B):** 125 stockouts, $4,926 lost, 9 ongoing, 6.71 days late on average.
- **Lakeshore Beverage Group (SUP010, tier C):** 172 stockouts, $4,268 lost, 23 ongoing, 6.33 days late on average.

## Recommended actions
1. **CA_3 and CA_1 store managers:** Submit the five emergency DSD requests above before the 2:00 pm local cut-off to get next-morning delivery. All five items are in eligible departments (FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1). Size each order to cover demand until the PO lands plus 3 days, rounded up to case pack (POL-SUP-003, GUIDE-DSD-005).
2. **West category buyers:** Escalate the 92 late-PO items in the queue (61 out of stock, 26 critical, 5 high) and charge the 8% DSD premium back to the supplier. Start with Prime Valley's 32 ongoing stockouts and the 11-day overdue coffee PO (POL-SUP-003).
3. **Store managers:** Have associates physically count the 74 phantom-inventory items ($944 at risk) within 24 hours. Adjust the ERP the same day, and order immediately if the count is 0. Adjustments of $500 or more at cost need Regional Manager sign-off within 2 business days (GUIDE-DSD-005).
4. **Regional supply lead:** Review the corrective-action plans for Prime Valley and Lakeshore (both tier C) under POL-SUP-003. The policy search did not return the full escalation ladder, so check it directly.

---

## Executive OSA briefing — 2016-05-23

*executive · ALL · databricks-claude-sonnet-5-5 · 31.8s · generated 2026-10-31T00:08:42.023Z · trace `tr-f16d918c540b25958a601a34e64ec9f5`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
Lost revenue fell to $40,235 in the last 7 days, down $10,332 from $50,567 the week before. Tonight's queue has 1,345 items with $15,649 of 3-day revenue at risk, and 732 of them (about $9,459) are Critical or already out of stock and need Emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.74% | 91.98% | +1.76 pts |
| Revenue | $957,303 | $1,024,462 | -6.6% |
| Lost revenue | $40,235 | $50,567 | -20.4% |
| Lost sales rate | 4.03% | 4.70% | -0.67 pts |
| OOS store-item-days | 9,609 | 12,198 | -21.2% |

## Top risks tonight
- **TX_2, Tortilla Chips #120:** Cycle count for suspected phantom inventory. The system shows 231 units but there are no recent sales. Reorder 24 units if the shelf is empty. $247.84 at risk.
- **CA_3, Cheddar Block #170:** Expedited order of 4 units. Stockout probability is 92%, with 1.53 days of cover against 10.5 units/day of demand. $163.05 at risk. The 4-unit quantity looks low for that demand, so the store should confirm it.
- **WI_2, Cereal #029:** Emergency DSD of 36 units. On hand is 0 and the PO is 1 day overdue. $150.59 at risk.
- **WI_2, Peanut Butter #316:** Emergency DSD of 8 units. The item is out of stock and the PO is 4 days late. $131.08 at risk.
- **TX_3, Pasta #368:** Emergency DSD of 24 units. The item is out of stock and the PO is overdue. $109.39 at risk.

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 394 stockouts, $11,072 lost, 61 still ongoing, average 6.46 days late.
- **SUP018 Polaris Paper & Plastics (tier B):** 288 stockouts, $10,831 lost, 27 ongoing, average 7.07 days late.
- **SUP010 Lakeshore Beverage Group (tier C):** 449 stockouts, the most of any supplier. $10,304 lost, 53 ongoing, average 6.28 days late.

## Recommended actions
1. **Store managers:** Submit Emergency DSD requests for the 732 Critical and out-of-stock items by the 2:00 pm local cut-off for next-morning delivery. Only FOODS_1/2/3 and HOUSEHOLD_1 items are eligible. Approve, Override or Reject each Critical alert within 4 business hours. Policy: GUIDE-DSD-005.
2. **Store associates and managers:** Physically count the 136 phantom-inventory items (shelf and backroom) within 24 hours. The manager adjusts the ERP same day. If the count is 0, place an emergency order immediately. Adjustments of $500 or more at cost need Regional Manager sign-off. Policy: GUIDE-DSD-005.
3. **Category buyers:** Escalate the late POs for the 127 out-of-stock and 92 Critical items on the expedite-and-escalate action. Start with SUP009, SUP018 and SUP010. Policy: POL-SUP-003.
4. **Category buyers:** Escalate HOBBIES and HOUSEHOLD_2 items to the buyer instead of using DSD. Policy: GUIDE-DSD-005.
5. **Regional managers:** Confirm the CA_3 Cheddar quantity and review the two tier-C suppliers (SUP009, SUP010). Policy: POL-SUP-003.

---

## Midwest region OSA briefing — 2016-05-23

*regional · Midwest · databricks-claude-sonnet-5-5 · 29.8s · generated 2026-10-31T00:08:42.023Z · trace `tr-7b00cc3ec241801549e7f077a17c612e`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
Midwest lost $10,043 in sales over the last 7 days, down from $12,763 the week before, but tonight's queue still has $4,601 of 3-day revenue at risk across 394 items. Emergency DSD items make up $3,241 of that, and WI_2 dominates the top risks.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 94.43% | 93.08% | +1.35 pts |
| Revenue | $255,954 | $301,606 | -15.1% |
| Lost revenue | $10,043 | $12,763 | -21.3% |
| Lost sales rate | 3.78% | 4.06% | -0.28 pts |
| OOS store-item-days | 2,471 | 3,053 | -19.1% |

## Top risks tonight
The queue returned ranks 3, 4, 8, 13 and 20. Ranks 1 and 2 did not appear in the tool output.
- **WI_2, Hearth & Home Cereal #029:** EMERGENCY_DSD, 36 units, $150.59 at risk (0 on hand, PO 1 day overdue).
- **WI_2, Parent's Choice Peanut Butter #316:** EMERGENCY_DSD, 8 units, $131.08 at risk (PO 4 days late).
- **WI_1, Equate Black Beans #282:** EMERGENCY_DSD, 16 units, $78.55 at risk.
- **WI_2, Great Value Dish Soap #488:** EMERGENCY_DSD, 24 units, $69.40 at risk.
- **WI_2, Sunny Fields Canned Tuna #198:** EMERGENCY_DSD, 16 units, $57.46 at risk (PO 3 days overdue).

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 111 stockouts, $3,338 lost, 14 still ongoing, 6.27 days late on average.
- **SUP010 Lakeshore Beverage Group (tier C):** 145 stockouts, $3,211 lost, 10 ongoing, 5.97 days late on average.
- **SUP007 Northstar Snacks & Beverage (tier B):** 119 stockouts, $3,005 lost, 24 ongoing (the most of any supplier), 5.95 days late on average.

## Recommended actions
1. **WI_2 and WI_1 store managers:** Submit the five emergency DSD requests above by 2:00 pm local time so they arrive next morning. A later request arrives in two days. All five items are in eligible departments (FOODS_2 or HOUSEHOLD_1). Order to cover demand until the PO lands plus 3 days, rounded up to the case pack (GUIDE-DSD-005).
2. **Midwest category buyers:** Call suppliers on any PO 2 or more days late or with under 2 days of store cover. Open a sourcing review for SUP009, SUP010 and SUP007, which all exceed the 3+ days late and 2+ stockouts-per-week thresholds (POL-SUP-003).
3. **Store managers:** Complete the 30 phantom-inventory cycle counts ($340 at risk). A store associate counts shelf and backroom within 24 hours, and the store manager adjusts the ERP record the same day. If the count is 0, the manager places an emergency order immediately after the adjustment (GUIDE-DSD-005).
4. **Regional Manager:** Sign off any inventory adjustment of $500 or more at cost within 2 business days (GUIDE-DSD-005).
5. **Regional Manager:** Review why revenue fell 15.1% week over week even though OSA improved.

---

## South region OSA briefing — 2016-05-23

*regional · South · databricks-claude-sonnet-5-5 · 43.3s · generated 2026-10-31T00:08:42.023Z · trace `tr-15b9465f500cf58527dd014f3753fb69`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies → search_policies → search_policies*

## Headline
South OSA improved to 93.61% and lost revenue fell to $10,086, down from $14,204 the week before. Tonight's queue has 372 items with $3,741 of 3-day revenue at risk. $2,082 of that sits in OOS_NOW and CRITICAL items that need emergency DSD.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.61% | 91.19% | +2.42 pts |
| Revenue | $270,426 | $282,414 | -$11,988 (-4.2%) |
| Lost revenue | $10,086 | $14,204 | -$4,118 (-29.0%) |
| Lost sales rate | 3.60% | 4.79% | -1.19 pts |
| OOS store-item-days | 2,776 | 3,797 | -1,021 |

## Top risks tonight
- **TX_2, Great Value Tortilla Chips #120:** Cycle count. The system shows 231 units but there are no recent sales, which points to phantom inventory. Reorder 24 units if the shelf is empty. $247.84 at risk.
- **TX_3, Great Value Pasta #368:** Emergency DSD of 24 units. The item is out of stock and has one overdue PO. $109.39 at risk.
- **TX_2, Northpeak Juice #695:** Emergency DSD of 8 units. On hand is 0 and the supplier PO is 2 days overdue. $53.64 at risk.
- **TX_2, Hearth & Home Ice Cream #661:** Cycle count. The system shows 50 units, but there are no sales against demand of 5.1 units/day. Reorder 48 units if the shelf is empty. $50.40 at risk.
- **TX_2, Equate Black Beans #194:** Expedited order of 4 units. Stockout probability is 86% and the next receipt is delayed. $49.29 at risk.

TX_2 accounts for four of the five top risks.

## Supplier watch
- **SUP018 Polaris Paper & Plastics (tier B):** 94 stockouts, $3,734 lost, 8 ongoing, 7.58 days late on average.
- **SUP016 CleanWave Home Products (tier A):** 121 stockouts, $3,231 lost, 10 ongoing, 6.66 days late on average.
- **SUP010 Lakeshore Beverage Group (tier C):** 123 stockouts, $2,776 lost, 17 ongoing (the most in the region), 6.7 days late on average.

## Recommended actions
1. **TX_3 and TX_2 store managers:** Submit the pasta and juice emergency DSD orders before the 2:00 pm local cut-off for next-morning delivery. Charge the 8% premium back to the supplier (GUIDE-DSD-005, POL-SUP-003).
2. **TX_2 store manager:** Count the shelf and backroom for the tortilla chips and ice cream within 24 hours. Adjust the ERP the same day and order immediately if the count is zero. Adjustments of $500 or more at cost need Regional Manager sign-off within 2 business days (SOP-INV-002).
3. **Category buyers:** Call the account managers at SUP018, SUP016 and SUP010 for any PO 2 or more days late or with under 2 days of cover (POL-SUP-003).
4. **Sourcing manager:** Open sourcing reviews with a corrective action plan due in 5 business days for all three suppliers. Each has far more than 2 stockouts in a week and POs 3 or more days late (POL-SUP-003).
5. **Regional Manager:** Review reallocating volume away from SUP010, a tier C supplier, if its on-time SLA has been missed for 4 consecutive weeks (POL-SUP-003).

---

## West region OSA briefing — 2016-05-23

*regional · West · databricks-claude-sonnet-5-5 · 30.7s · generated 2026-10-31T00:08:42.023Z · trace `tr-fb3ceaab1776a4fd6e105fab27bbf5e3`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
West OSA improved to 93.36% and lost revenue fell to $20,105. Tonight's queue still has 579 items with $7,310 of 3-day revenue at risk, and $4,137 of that is in 300 Emergency DSD items.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.36% | 91.76% | +1.60 pts |
| Revenue | $430,923 | $440,442 | -2.2% |
| Lost revenue | $20,105 | $23,599 | -14.8% |
| Lost sales rate | 4.46% | 5.09% | -0.63 pts |
| OOS store-item days | 4,362 | 5,348 | -986 |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** Expedited order, 4 units, $163.05 at risk. Stockout probability is 92% with 1.53 days of cover. Demand is 10.5 units/day, so the buyer should confirm 4 units is enough.
- **CA_3, Northpeak Soup #183:** Verify shelf and expedite the PO, 4 units, $97.30 at risk. The system shows 20 on hand, but 1 PO is overdue.
- **CA_1, Equate Cola 12pk #682:** Emergency DSD, 48 units, $87.09 at risk. On hand is 0 and the 102 units on order are overdue.
- **CA_3, Marketside Trash Bags #249:** Emergency DSD, 24 units, $75.72 at risk. Supplier is CleanWave Home Products.
- **CA_3, Sunny Fields Coffee #574:** Emergency DSD, 20 units, $75.55 at risk.

CA_3 has four of the five top risks.

## Supplier watch
- **SUP009 Prime Valley Distribution (tier C):** 183 stockouts, $5,218 lost, 30 still ongoing, 6.08 days late on average.
- **SUP018 Polaris Paper & Plastics (tier B):** 129 stockouts, $5,158 lost, 11 ongoing, 6.66 days late.
- **SUP010 Lakeshore Beverage Group (tier C):** 181 stockouts, $4,317 lost, 26 ongoing, 6.26 days late.

## Recommended actions
1. **Store managers (CA_1, CA_3):** Submit Emergency DSD for eligible Critical and OOS items by 2:00 pm local so they arrive next morning. Later requests arrive in two days. The 8% premium is charged back to the supplier for late POs. (POL-SUP-003, GUIDE-DSD-005)
2. **Store managers:** For overdue POs with less than 2 days of cover, raise DSD. This covers Cheddar #170 and Soup #183. (POL-SUP-003)
3. **Category buyers:** Escalate SUP009, SUP010 and SUP018 for the late POs. Notify the buyer on every overdue-PO item. (POL-SUP-003)
4. **Store associates and managers:** Physically count the 63 phantom-inventory items within 24 hours. Managers adjust the ERP the same day and order immediately if the count is 0. Adjustments of $500 or more need Regional Manager sign-off within 2 business days. (GUIDE-DSD-005)
5. **Regional Manager:** Move HOBBIES and HOUSEHOLD_2 items to buyer escalation, because they aren't eligible for DSD.

---

## Executive OSA briefing — 2016-05-22

*executive · ALL · databricks-claude-sonnet-5-5 · 42.3s · generated 2026-10-30T23:51:35.271Z · trace `tr-9fbf99ae6c9b60a476a0a9790b0c2787`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies → search_policies*

## Headline
Lost revenue fell to $41,418 in the last 7 days, down from $50,591 the week before. Tonight's queue still has 1,435 store-items with $16,490 of 3-day revenue at risk, and $10,484 of that is in 815 emergency-DSD items.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.77% | 91.96% | +1.81 pts |
| Revenue | $962,773 | $1,036,102 | -7.1% |
| Lost revenue | $41,418 | $50,591 | -18.1% |
| Lost-sales rate | 4.12% | 4.66% | -0.54 pts |
| OOS store-item-days | 9,542 | 12,226 | -22.0% |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** expedited order, 4 units, $156.15 at risk (88% stockout probability, 1.73 days of cover).
- **WI_2, Hearth & Home Cereal #029:** emergency DSD, 36 units, $149.25 at risk (0 on hand, PO overdue).
- **WI_2, Parent's Choice Peanut Butter #316:** emergency DSD, 8 units, $131.74 at risk (out of stock, 51-unit order 3 days overdue).
- **TX_3, Great Value Pasta #368:** emergency DSD, 24 units, $111.23 at risk (out of stock, PO 2 days late).
- **CA_3, Northpeak Soup #183:** expedited order, 4 units, $89.24 at risk (88% stockout probability).

## Supplier watch
- **SUP018 Polaris Paper & Plastics (B):** $11,274 lost revenue, 295 stockouts, 25 still ongoing, 7.25 days late on average.
- **SUP009 Prime Valley Distribution (C):** $11,095 lost revenue, 400 stockouts, 56 still ongoing, 6.5 days late on average.
- **SUP010 Lakeshore Beverage Group (C):** $10,490 lost revenue, 463 stockouts, 54 still ongoing, 6.17 days late on average.

## Recommended actions
1. **Store managers:** submit emergency DSD for the 815 critical and out-of-stock items before the 2:00 pm local cut-off, so they arrive next morning instead of in two days. Only FOODS_1, FOODS_2, FOODS_3 and HOUSEHOLD_1 items are eligible (GUIDE-DSD-005).
2. **Category buyers:** call the account managers at SUP018, SUP009 and SUP010 today. Their POs are 3 or more days late, so open a sourcing review with a corrective action plan due in 5 business days (POL-SUP-003).
3. **Store associates:** physically count the 111 suspected phantom-inventory items ($1,499 at risk) within 24 hours. Store managers then adjust the ERP the same day and place an emergency order for any item that counts at zero (GUIDE-DSD-005).
4. **Replenishment planners:** place the 96 critical expedited orders ($1,381), starting with CA_3 cheddar and soup.
5. **Regional managers:** sign off any inventory adjustment of $500 or more at cost within 2 business days (GUIDE-DSD-005).

---

## Midwest region OSA briefing — 2016-05-22

*regional · Midwest · databricks-claude-sonnet-5-5 · 28.5s · generated 2026-10-30T23:51:35.271Z · trace `tr-1772a205592b1bbc26ccbd31726ba5eb`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
Midwest has 405 store-items in tonight's queue with **$4,834** of 3-day revenue at risk. $3,574 of that is in 254 Emergency DSD items. Lost revenue fell to $10,080 from $12,770 (-21.1%), but late supplier POs are still driving most stockouts.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 94.65% | 93.09% | +1.56 pts |
| Revenue | $257,490 | $310,197 | -17.0% |
| Lost revenue | $10,080 | $12,770 | -21.1% |
| Lost-sales rate | 3.77% | 3.95% | -0.18 pts |
| OOS store-item-days | 2,373 | 3,045 | -22.1% |

## Top risks tonight
- **WI_2, Hearth & Home Cereal #029:** Emergency DSD, 36 units, $149.25 at risk. On-hand is 0 and the PO is overdue.
- **WI_2, Parent's Choice Peanut Butter #316:** Emergency DSD, 8 units, $131.74 at risk. It is out of stock and the 51-unit PO is 3 days overdue.
- **WI_1, Parent's Choice Large Eggs #012:** Emergency DSD, 6 units, $82.88 at risk. It is out of stock and the Golden Prairie Dairy PO is overdue.
- **WI_1, Equate Black Beans #282:** Emergency DSD, 8 units, $77.92 at risk. The system shows 48 units on hand but 100% stockout probability. Verify the stock on the shelf before ordering, because it may be phantom inventory.
- **WI_2, Mainstays Granola Bars #083:** Expedited order, 24 units, $68.66 at risk. Demand is 2.6 units/day.

## Supplier watch
- **SUP009 Prime Valley Distribution (Tier C):** 114 stockouts, $3,426 lost, 14 still ongoing, 6.41 days late on average.
- **SUP010 Lakeshore Beverage Group (Tier C):** 153 stockouts, $3,294 lost, 14 ongoing, 5.78 days late.
- **SUP007 Northstar Snacks & Beverage (Tier B):** 120 stockouts, $3,076 lost, 22 ongoing (the most), 6.11 days late.

## Recommended actions
1. **Store managers (WI_1, WI_2):** Submit the Emergency DSD requests for cereal #029, peanut butter #316 and eggs #012 **before the 2:00 pm local cut-off** for next-morning delivery. Policy: POL-SUP-003 / GUIDE-DSD-005.
2. **WI_1 store manager:** Count shelf and backroom for Black Beans #282 within 24 hours. If the count is zero, order immediately after the ERP adjustment. Policy: SOP-INV-002.
3. **Category buyers:** Place the expedited order for granola bars #083. Call suppliers on the 64 items in "Expedite PO and Escalate", $388 at risk. Policy: POL-SUP-003.
4. **Sourcing:** Open a sourcing review for SUP009, SUP010 and SUP007. All three average more than 5 days late, past the 3+ day trigger. Policy: POL-SUP-003.
5. **Finance and AP:** Charge back the 8% DSD premium to suppliers where a late PO is the cause. Policy: POL-SUP-003.
6. **Store teams:** Cycle-count the 26 phantom-inventory items, $320 at risk, before reordering. Policy: SOP-INV-002.

---

## South region OSA briefing — 2016-05-22

*regional · South · databricks-claude-sonnet-5-5 · 26.9s · generated 2026-10-30T23:51:35.271Z · trace `tr-c31f0cf0caf2582ed6657d16696e144f`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies*

## Headline
South OSA improved to 93.64%, and lost revenue fell $3,851 to $10,396 week over week. Tonight's queue still has 406 items with $3,890 of 3-day revenue at risk. About $2,412 of that is in emergency DSD items, which are CRITICAL or already out of stock.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.64% | 91.09% | +2.55 pts |
| Revenue | $273,063 | $282,504 | -$9,441 (-3.3%) |
| Lost revenue | $10,396 | $14,247 | -$3,851 (-27.0%) |
| Lost sales rate | 3.67% | 4.80% | -1.13 pts |
| OOS store-item-days | 2,758 | 3,839 | -1,081 |

## Top risks tonight
- **TX_3, Great Value Pasta #368:** OOS now, PO 2 days late. EMERGENCY_DSD, 24 units, $111.23 at risk.
- **TX_3, Mainstays Butter #107:** OOS now, PO 2 days overdue. EMERGENCY_DSD, 24 units, $72.50 at risk.
- **TX_3, Sunny Fields Paper Towels #222:** 0 on hand. EXPEDITED_ORDER, 24 units, $53.54 at risk.
- **TX_2, Northpeak Juice #695:** CRITICAL (98% stockout probability) with an overdue PO. EMERGENCY_DSD, 8 units, $52.90 at risk.
- **TX_2, Hearth & Home Ice Cream #661:** suspected phantom inventory. CYCLE_COUNT, 48 units, $51.17 at risk.

## Supplier watch
- **SUP018 Polaris Paper & Plastics (tier B):** 94 stockouts, $3,876 lost, average 8.0 days late, 5 ongoing.
- **SUP016 CleanWave Home Products (tier A):** 125 stockouts, $3,382 lost, 14 ongoing.
- **SUP010 Lakeshore Beverage Group (tier C):** 128 stockouts, $2,922 lost, 15 ongoing, average 6.79 days late.

## Recommended actions
1. **TX_3 and TX_2 store managers:** Submit emergency DSD for the pasta, butter and juice before the 2:00 pm local cut-off so they arrive tomorrow morning. Later requests take two days. Charge the 8% premium back to the supplier as a late-PO root cause (POL-SUP-003).
2. **Category buyers:** Escalate the 57 late-PO items in the EXPEDITE_PO_AND_ESCALATE queue. Start with SUP018, SUP016 and SUP010 (POL-SUP-003, GUIDE-DSD-005).
3. **Category buyer (household/paper):** Handle the HOUSEHOLD_2 and HOBBIES items through buyer escalation, because DSD isn't allowed for those departments (POL-SUP-003).
4. **TX_2 store manager:** Have an associate count the ice cream, shelf and backroom, within 24 hours. Adjust in ERP the same day. If the count is 0, place an emergency order right away (GUIDE-DSD-005). The same applies to the other 31 phantom flags.
5. **South Regional Manager:** Sign off any adjustment of $500 or more at cost within 2 business days (GUIDE-DSD-005).

---

## West region OSA briefing — 2016-05-22

*regional · West · databricks-claude-sonnet-5-5 · 33.5s · generated 2026-10-30T23:51:35.271Z · trace `tr-93a82135bc39acbde8d11fa1264dbc04`*  
*tools: kpi_summary → action_queue_summary → region_action_queue → supplier_watchlist → search_policies → search_policies*

## Headline
West OSA improved to 93.27% from 91.76%, and lost revenue fell $2,632 week over week to $20,942. 624 alerts tonight still put $7,767 of 3-day revenue at risk. 338 of them (173 critical and 165 out of stock now) need Emergency DSD, with $4,499 at risk.

## KPIs
| Metric | Last 7d | Prior 7d | Change |
|---|---|---|---|
| OSA % | 93.27% | 91.76% | +1.51 pts |
| Revenue | $432,220 | $443,402 | -$11,182 |
| Lost revenue | $20,942 | $23,574 | -$2,632 |
| Lost sales rate | 4.62% | 5.05% | -0.43 pts |
| OOS store-item days | 4,411 | 5,342 | -931 |

## Top risks tonight
- **CA_3, Equate Cheddar Block #170:** expedited order, 4 units, $156.15 at risk (88% stockout probability, 1.73 days of cover).
- **CA_3, Northpeak Soup #183:** expedited order, 4 units, $89.24 at risk.
- **CA_1, Equate Cola 12pk #682:** expedited order, 48 units, $84.83 at risk (0 on hand).
- **CA_3, Marketside Trash Bags #489:** expedited order, 12 units, $79.44 at risk (out of stock).
- **CA_3, Sunny Fields Coffee #574:** Emergency DSD, 24 units, $76.14 at risk. The Prime Valley PO is 3 days overdue.

CA_3 has four of the five top items, so it is the store to focus on.

## Supplier watch
- **Polaris Paper & Plastics (SUP018, tier B):** 134 stockouts, $5,248 lost, 13 ongoing, average 6.65 days late.
- **Prime Valley Distribution (SUP009, tier C):** 188 stockouts, $5,224 lost, 31 ongoing (the most of any supplier), average 6.19 days late.
- **Northstar Snacks & Beverage (SUP007, tier B):** 177 stockouts, $4,357 lost, 18 ongoing, average 6.64 days late.

## Recommended actions
1. **Store managers, CA_3 and CA_1:** Submit Emergency DSD for eligible FOODS and HOUSEHOLD_1 items before the 2:00 pm cut-off, so they arrive next morning. Size each order to cover demand until the PO lands plus 3 days (GUIDE-DSD-005).
2. **Category buyers:** Call the account managers for the 117 expedite-and-escalate alerts (65 critical, 52 out of stock now). Where item cover is under 2 days or the PO is 2+ days late, the buyer call is required (POL-SUP-003).
3. **Sourcing:** Open a review with a corrective action plan due in 5 business days for Prime Valley, Polaris and Northstar. Each has POs 3+ days late and 2+ attributed stockouts (POL-SUP-003).
4. **Store associates:** Physically count the 53 suspected phantom items within 24 hours. The store manager adjusts ERP the same day and reorders any item that counts as 0 (SOP-INV-002).
5. **Regional Manager:** Sign off on any adjustment of $500 or more at cost within 2 business days (SOP-INV-002).
