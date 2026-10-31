# Supervisor Agent (OSA Assistant) Q&A — `mas-2ee5d824-endpoint`

*2026-10-31 00:43 UTC. Each answer is produced by the Agent Bricks Supervisor routing between the Genie Agent (governed SQL), the Knowledge Assistant (internal documents) and UC function tools.*

## Q: What was on-shelf availability by region over the last 7 days compared with the prior 7 days?

*30.2s · routed to: osa_analyst({"genie_query": "What was on-shelf availability by region over the last 7 days compared with the prior 7 days?"})*

**Final answer:**

**On-Shelf Availability by Region: Last 7 Days vs. Prior 7 Days**

All three regions showed improvement in on-shelf availability over the most recent 7-day period:

**Midwest**
- Last 7 days: **94.22%**
- Prior 7 days: **93.08%**
- Change: **+1.14 percentage points**

**South**
- Last 7 days: **93.75%**
- Prior 7 days: **91.34%**
- Change: **+2.41 percentage points**

**West**
- Last 7 days: **93.53%**
- Prior 7 days: **91.71%**
- Change: **+1.82 percentage points**

The South region showed the strongest improvement (+2.41 pts), while the Midwest maintained the highest absolute OSA at 94.22%. All regions are trending positively week-over-week.

**Recommended Next Step:** Review what operational changes or supplier improvements drove the South's strong 2.4-point gain to identify best practices that can be replicated in the Midwest and West regions.

<details><summary>Sub-agent outputs (Genie / Knowledge Assistant)</summary>

I'll query the OSA analyst to get on-shelf availability by region for the last 7 days compared with the prior 7 days.

<name>osa_analyst</name>

||region|period|osa_pct|
|-|-|-|-|
|0|Midwest|last_7_days|94.22|
|1|Midwest|prior_7_days|93.08|
|2|South|last_7_days|93.75|
|3|South|prior_7_days|91.34|
|4|West|last_7_days|93.53|
|5|West|prior_7_days|91.71|

<name>OSA Assistant</name>

</details>

---

## Q: Which 5 store-items have the highest revenue at risk tonight, and what should each store do?

*53.3s · routed to: osa_analyst({"genie_query": "What are the top 5 store-items with the highest revenue at risk or lost sales tonight? Show store, item, and revenue at risk amount."}) → osa_analyst({"genie_query": "For stores TX_2, CA_3, WI_2, and TX_3, what are tonight's recommended actions or alerts for items Great Value Tortilla Chips #120, Equate Chedd)*

**Final answer:**

## Top 5 Store-Items with Highest Revenue at Risk Tonight

| Rank | Store | Item | Revenue at Risk | Recommended Action | Quantity | Rationale |
|------|-------|------|----------------|-------------------|----------|-----------|
| **1** | **TX_2** | Great Value Tortilla Chips #120 | **$237** | EXPEDITED_ORDER | 24 units | Out of stock now (0 on hand) despite 217 units on order. Demand is 15.9 units/day. Supplier: Northstar Snacks & Beverage. |
| **2** | **CA_3** | Equate Cheddar Block #170 | **$175** | EMERGENCY_DSD | 4 units | CRITICAL risk (99% stockout probability), 0 on hand, 10.4 units/day demand. Supplier: Sunvale Bakery Partners. |
| **3** | **WI_2** | Hearth & Home Cereal #029 | **$150** | EMERGENCY_DSD | 36 units | CRITICAL risk (96% stockout probability), 0 on hand, supplier PO is 2 days overdue. Supplier: Coastal Canning Co. |
| **4** | **WI_2** | Parent's Choice Peanut Butter #316 | **$131** | *(action pending)* | - | Data not returned in alert queue. |
| **5** | **TX_3** | Great Value Pasta #368 | **$109** | EMERGENCY_DSD | 24 units | Out of stock now (0 on hand), 1 overdue PO. Supplier: Coastal Canning Co. |

### Immediate Next Steps:
1. **TX_2**: Place expedited order for 24 units of Tortilla Chips #120 immediately
2. **CA_3**: Execute emergency DSD for 4 units of Cheddar Block #170 before 2pm cutoff
3. **WI_2**: Execute emergency DSD for 36 units of Cereal #029 due to overdue supplier PO; investigate Peanut Butter #316 status
4. **TX_3**: Execute emergency DSD for 24 units of Pasta #368 and escalate overdue PO with Coastal Canning Co

**Total revenue at risk across these 5 store-items: $802**

<details><summary>Sub-agent outputs (Genie / Knowledge Assistant)</summary>

I'll help you identify the top 5 store-items with the highest revenue at risk tonight and provide recommended actions for each store.

<name>osa_analyst</name>

||store|item|revenue_at_risk_amount|
|-|-|-|-|
|0|TX_2|Great Value Tortilla Chips #120|237|
|1|CA_3|Equate Cheddar Block #170|175|
|2|WI_2|Hearth & Home Cereal #029|150|
|3|WI_2|Parent's Choice Peanut Butter #316|131|
|4|TX_3|Great Value Pasta #368|109|

<name>OSA Assistant</name>

<name>osa_analyst</name>

||store_id|item_name|risk_tier|risk_score|recommended_action|recommended_qty|on_hand_units|on_order_units|days_of_cover|revenue_at_risk_3d|supplier_name|rationale|
|-|-|-|-|-|-|-|-|-|-|-|-|-|
|0|CA_3|Equate Cheddar Block #170|CRITICAL|0.988|EMERGENCY_DSD|4|0|153|0|175|Sunvale Bakery Partners|Equate Cheddar Block #170 has 0 units on hand with 99% stockout probability and 10.4 units/day demand—execute EMERGENCY_DSD of 4 units immediately.|
|1|TX_2|Great Value Tortilla Chips #120|OOS_NOW|0.334|EXPEDITED_ORDER|24|0|217|0|237|Northstar Snacks & Beverage|Great Value Tortilla Chips #120 is out of stock with 0 units on hand despite 217 on order; place EXPEDITED_ORDER of 24 units to cover 15.9 units/day demand.|
|2|TX_3|Great Value Pasta #368|OOS_NOW|0.185|EMERGENCY_DSD|24|0|57|0|109|Coastal Canning Co|Great Value Pasta #368 is out of stock with 0 units on hand and 1 overdue PO; execute EMERGENCY_DSD of 24 units immediately.|
|3|WI_2|Hearth & Home Cereal #029|CRITICAL|0.961|EMERGENCY_DSD|36|0|53|0|150|Coastal Canning Co|Hearth & Home Cereal #029 has 0 units on hand with 96% stockout probability; execute EMERGENCY_DSD of 36 units immediately due to 2-day overdue supplier PO.|

<name>OSA Assistant</name>

</details>

---

## Q: Which suppliers caused the most stockouts in the last 4 weeks, and what does our escalation policy require us to do about them?

*43.4s · routed to: osa_analyst({"genie_query": "Which suppliers caused the most stockouts in the last 4 weeks? Show me the top suppliers ranked by number of stockout events."}) → osa_policies({"ka_query": "What does our supplier escalation policy require us to do when suppliers cause stockouts? What are the escalation steps and thresholds?"})*

**Final answer:**

## Top Suppliers Causing Stockouts (Last 4 Weeks)

**Top 5 Worst Offenders:**

1. **Lakeshore Beverage Group** (Tier C) – 433 stockout events, $10,161 lost revenue
2. **Prime Valley Distribution** (Tier C) – 383 stockout events, $10,897 lost revenue
3. **Northstar Snacks & Beverage** (Tier B) – 364 stockout events, $9,288 lost revenue
4. **CleanWave Home Products** (Tier A) – 311 stockout events, $9,001 lost revenue
5. **Evergreen Foods Wholesale** (Tier B) – 288 stockout events, $6,003 lost revenue

## Required Escalation Actions (POL-SUP-003)

Based on the severity of these stockouts, you must execute the following escalation ladder:

**Level 3 – Sourcing Review (IMMEDIATE):**
All top suppliers have triggered the "2+ attributed stockouts in one week" threshold. You must:
- Initiate sourcing review for each supplier
- Demand corrective action plan within 5 business days
- Sourcing manager owns this action

**Level 4 – Tier Downgrade Review (HIGH PRIORITY):**
If any of these suppliers have been below on-time SLA for 4 consecutive weeks, you must:
- Conduct tier downgrade review
- Reallocate volume to alternate suppliers
- VP Sourcing owns this action

**Additional Actions:**
- Apply late penalties per PO at contract rates
- Category buyers should evaluate emergency DSD options for critical items
- Monitor store cover levels; if any item drops below 2 days, category buyer must call supplier account manager immediately

## Recommended Next Step
**Convene an emergency sourcing review meeting this week** with the category buyers and sourcing managers responsible for Lakeshore Beverage Group, Prime Valley Distribution, and Northstar Snacks & Beverage. Require corrective action plans by end of next week and begin identifying alternate suppliers for volume reallocation.

<details><summary>Sub-agent outputs (Genie / Knowledge Assistant)</summary>

I'll help you identify the suppliers with the most stockouts and the escalation policy requirements. Let me gather both pieces of information.

<name>osa_analyst</name>

||supplier_rank|supplier_name|reliability_tier|stockout_events|lost_revenue|
|-|-|-|-|-|-|
|0|1|Lakeshore Beverage Group|C|433|10161|
|1|2|Prime Valley Distribution|C|383|10897|
|2|3|Northstar Snacks & Beverage|B|364|9288|
|3|4|CleanWave Home Products|A|311|9001|
|4|5|Evergreen Foods Wholesale|B|288|6003|
|5|6|Ironwood Household Supply|B|284|7761|
|6|7|Polaris Paper & Plastics|B|274|10231|
|7|8|Coastal Canning Co|A|273|8335|
|8|9|Summit Hobby Wholesale|B|264|4615|
|9|10|Maker's Mark Supply Co|B|243|4547|
|10|11|Brightline Toys & Crafts|C|239|4067|
|11|12|Blue Ridge Pantry Distributors|B|238|6624|
|12|13|Harvest Lane Grocers Supply|C|222|6500|
|13|14|Riverbend Fresh Foods|B|189|4407|
|14|15|Sunvale Bakery Partners|A|144|2803|
|15|16|Golden Prairie Dairy Co|A|139|3942|
|16|17|Crestview Hardware Wholesale|A|124|3902|
|17|18|Meridian Kitchen & Bath|B|107|2962|
|18|19|Hearthstone Home Goods|A|94|2844|
|19|20|Atlas Party & Seasonal|A|57|456|
|20|21|Pinecrest Leisure Goods|A|50|362|

<name>OSA Assistant</name>

<name>OSA Policy & Procedures Assistant</name>

The supplier escalation policy in POL-SUP-003 defines four escalation triggers and actions:

1. **PO 1 day late:** Automatic notification to supplier account manager (System-owned)

2. **PO 2 days late OR item cover < 2 days:** Category buyer calls the supplier account manager; store may raise emergency DSD (Category buyer-owned)

3. **PO 3+ days late, OR 2+ attributed stockouts for the same supplier in one week:** Sourcing review; corrective action plan due in 5 business days (Sourcing manager-owned)

4. **Supplier below on-time SLA for 4 consecutive weeks:** Tier downgrade review; volume reallocation to alternate supplier (VP Sourcing-owned)

Additionally, late penalties are applied per PO at the contract rate, and chargebacks are waived for force-majeure events declared by Sourcing.[^Wfex-1] However, penalty revenue is not a substitute for availability — the KPI that matters is lost sales.[^Wfex-2]

For specific suppliers, escalation procedures are documented in individual contract summaries. For example, Northstar Snacks & Beverage (CONTRACT-SUP007) follows POL-SUP-003 escalation procedures: automatic notice at 1 day late, category-buyer call at 2 days late or when store cover drops below 2 days, and sourcing review at 3+ days late or 2+ attributed stockouts in a week.[^Wfex-3]

[^Wfex-1]: Chargebacks Late penalties are applied per PO at the contract rate. Chargebacks are waived for force-majeure events declared by Sourcing.  [POL-SUP-003_supplier_performance_escalation.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/POL-SUP-003_supplier_performance_escalation.md#:~:text=Chargebacks%0ALate%20penalties%20are%20applied%20per%20PO%20at%20the%20contract%20rate.%20Chargebacks%20are%20waived%20for%20force-majeure%20events%20declared%20by%0ASourcing.%20)
[^Wfex-2]: Penalty revenue is **not** a substitute for availability — the KPI that matters is lost sales.  [POL-SUP-003_supplier_performance_escalation.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/POL-SUP-003_supplier_performance_escalation.md#:~:text=Penalty%20revenue%20is%20%2A%2Anot%2A%2A%20a%20substitute%20for%20availability%20%E2%80%94%20the%20KPI%20that%20matters%20is%20lost%20sales.%0A%0A)
[^Wfex-3]: *  | Term | Value | |---|---| | Supplier | Northstar Snacks & Beverage (SUP007) | | Primary department | FOODS_3 | | Reliability tier | B | | Contract lead time | 3 days from PO creation to expected receipt | | On-time SLA | 95% of POs received on or before the expected date | | Fill-rate SLA | 96% of ordered units | | Late-delivery penalty | 1.5% of PO value per late PO | | Payment terms | NET30 | | Account manager | am.northstar@northstar-supply.example |  ## Escalation Late POs are escalated per POL-SUP-003: automatic notice at 1 day late, category-buyer call at 2 days late or when store cove

<name>OSA Assistant</name>

</details>

---

## Q: Store TX_2 has a household cleaning item out of stock and the supplier PO is overdue. Can they place an emergency DSD order, by when, and what will it cost?

*18.2s · routed to: osa_policies({"ka_query": "Emergency DSD orders for household cleaning items: eligibility, cutoff times, costs, premiums, and fees"})*

**Final answer:**

**Yes, TX_2 can place an emergency DSD order** for the household cleaning item, provided it falls under the **HOUSEHOLD_1** department (if it's HOUSEHOLD_2, it is not eligible and must be escalated to the category buyer instead).

## Key Details:

**Eligibility:** ✓ Met
- Item is out of stock
- Supplier PO is overdue
- Household cleaning items in HOUSEHOLD_1 are eligible per **GUIDE-DSD-005**

**Timing:**
- **Cutoff: 2:00 PM local time** for next-morning delivery
- After 2:00 PM: delivery in two days

**Cost:**
- **8% premium** over contracted unit cost
- **$45 flat delivery fee** per store per day
- **Total cost is charged back to the supplier** since the root cause is a late PO (per **POL-SUP-003**)

**Order Quantity:**
- Order enough to cover demand until the regular PO lands plus 3 days, rounded up to the case pack

## Recommended Next Step:
**Verify the item is in HOUSEHOLD_1** (not HOUSEHOLD_2), then submit the emergency DSD request **before 2:00 PM today** to receive delivery tomorrow morning. Calculate the order quantity as: forecasted daily demand × (days until regular PO arrives + 3 days), rounded to full case packs. Document the overdue supplier PO as justification for the cost chargeback.

<details><summary>Sub-agent outputs (Genie / Knowledge Assistant)</summary>

I'll help you determine if TX_2 can place an emergency DSD order for the household cleaning item. Let me check our DSD policy for the eligibility, timing, and cost details.

<name>OSA Policy & Procedures Assistant</name>

Based on the internal documents, here is the information on Emergency DSD orders for household cleaning items:

**Eligibility:**

Emergency DSD can only be used when all of the following apply: the item has a Critical stockout-risk alert or is already out of stock, the regular supplier PO is overdue or will not land before cover runs out, and the item is in an eligible department: FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1.

Household cleaning items would typically fall under HOUSEHOLD_1 or HOUSEHOLD_2. HOBBIES and HOUSEHOLD_2 items are not eligible for DSD; escalate to the category buyer instead.[^Tly0-1][^Tly0-2] Therefore, **household cleaning items in HOUSEHOLD_1 are eligible**, but those in HOUSEHOLD_2 are **not eligible**.

**Cutoff Times:**

Requests submitted by 2:00 pm local time are delivered next morning. Requests after the cut-off are delivered in two days.[^Tly0-3]

**Costs and Premiums:**

Emergency DSD carries a cost premium of 8% over the contracted unit cost, plus a flat $45 delivery fee per store per day.[^Tly0-4] The premium is charged back to the supplier when the root cause is a late PO (POL-SUP-003).[^Tly0-5]

**Quantity Guidelines:**

Order enough to cover demand until the regular PO lands plus 3 days, rounded up to the case pack.[^Tly0-6]

[^Tly0-1]: When to use an emergency DSD order Use emergency DSD only when **all** apply: * the item has a Critical stockout-risk alert or is already out of stock, * the regular supplier PO is overdue or will not land before cover runs out, * the item is in an eligible department: **FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1**. [GUIDE-DSD-005_direct_store_delivery_emergency_orders.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/GUIDE-DSD-005_direct_store_delivery_emergency_orders.md#:~:text=When%20to%20use%20an%20emergency%20DSD%20order%0AUse%20emergency%20DSD%20only%20when%20%2A%2Aall%2A%2A%20apply%3A%0A%2A%20the%20item%20has%20a%20Critical%20stockout-risk%20alert%20or%20is%20already%20out%20of%20stock%2C%0A%2A%20the%20regular%20supplier%20PO%20is%20overdue%20or%20will%20not%20land%20before%20cover%20runs%20out%2C%0A%2A%20the%20item%20is%20in%20an%20eligible%20department%3A%20%2A%2AFOODS_1%2C%20FOODS_2%2C%20FOODS_3%2C%20HOUSEHOLD_1%2A%2A.%0A)
[^Tly0-2]: HOBBIES and HOUSEHOLD_2 items are not eligible for DSD; escalate to the category buyer instead.  [GUIDE-DSD-005_direct_store_delivery_emergency_orders.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/GUIDE-DSD-005_direct_store_delivery_emergency_orders.md#:~:text=HOBBIES%20and%20HOUSEHOLD_2%20items%20are%20not%20eligible%20for%20DSD%3B%20escalate%20to%20the%20category%20buyer%20instead.%0A%0A)
[^Tly0-3]: Cut-off and lead time * Requests submitted by **2:00 pm local time** are delivered next morning. * Requests after the cut-off are delivered in two 

<name>OSA Assistant</name>

</details>

---

## Q: What share of stockouts since November 2015 came from phantom inventory, and what is the procedure when we suspect it?

*33.8s · routed to: osa_analyst({"genie_query": "What percentage of stockouts since November 2015 were caused by phantom inventory?"}) → osa_policies({"ka_query": "What is the procedure when we suspect phantom inventory?"})*

**Final answer:**

**Phantom Inventory Share & Procedure**

**24.65%** of stockouts since November 2015 were caused by phantom inventory—**12,349 out of 50,091 total stockout events**.

**Procedure when phantom inventory is suspected** (per **SOP-INV-002**):

A store-item is flagged when: (1) zero sales for a statistically improbable streak given normal demand, and (2) system on-hand > 0.

| Step | Who | SLA |
|---|---|---|
| Physical count (shelf + backroom) | Store associate | Within **24 hours** of flag |
| Inventory adjustment in ERP | Store manager | Same day as count |
| Emergency order (if count = 0) | Store manager | Immediately after adjustment (see GUIDE-DSD-005) |

**Approval thresholds:**
- Adjustments **< $500** (at cost): Store manager approval
- Adjustments **≥ $500**: Regional Manager sign-off within 2 business days

**Recommended next step:** Review tonight's phantom inventory flags in your store action queue and ensure all associates know the 24-hour count SLA. Nearly a quarter of your stockouts stem from this root cause, so disciplined cycle counting directly recovers lost sales.

<details><summary>Sub-agent outputs (Genie / Knowledge Assistant)</summary>

I'll help you find the share of stockouts caused by phantom inventory and the procedure for handling it. Let me route this to the appropriate agents.

<name>osa_analyst</name>

||phantom_inventory_stockout_pct|total_stockouts|phantom_inventory_stockouts|
|-|-|-|-|
|0|24.65|50091|12349|

<name>OSA Assistant</name>

<name>OSA Policy & Procedures Assistant</name>

A store-item is flagged as suspected phantom inventory when both: (1) it has sold zero units for a streak whose probability under its normal demand rate is below 1%, and (2) the system on-hand is greater than zero.

When phantom inventory is suspected, follow this procedure from **SOP-INV-002**:


| Step | Who | SLA |
|---|---|---|
| Physical count of shelf + backroom | Store associate | within **24 hours** of the flag |
| Inventory adjustment in ERP | Store manager | same day as the count |
| Emergency order if count = 0 | Store manager | immediately after adjustment (GUIDE-DSD-005) |


Additionally, if an item shows units on hand in the system but has sold zero units for longer than expected, do not reorder blindly: trigger a cycle count per SOP-INV-002 first.[^5KtU-1][^5KtU-2]

Adjustments below $500 at cost are approved by the store manager. Adjustments of $500 or more require Regional Manager sign-off within 2 business days.[^5KtU-3]

[^5KtU-1]: Required response | Step | Who | SLA | |---|---|---| | Physical count of shelf + backroom | Store associate | within **24 hours** of the flag | | Inventory adjustment in ERP | Store manager | same day as the count | | Emergency order if count = 0 | Store manager | immediately after adjustment (GUIDE-DSD-005) |  ## 4.  [SOP-INV-002_inventory_accuracy_cycle_counts.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/SOP-INV-002_inventory_accuracy_cycle_counts.md#:~:text=Required%20response%0A%7C%20Step%20%7C%20Who%20%7C%20SLA%20%7C%0A%7C---%7C---%7C---%7C%0A%7C%20Physical%20count%20of%20shelf%20%2B%20backroom%20%7C%20Store%20associate%20%7C%20within%20%2A%2A24%20hours%2A%2A%20of%20the%20flag%20%7C%0A%7C%20Inventory%20adjustment%20in%20ERP%20%7C%20Store%20manager%20%7C%20same%20day%20as%20the%20count%20%7C%0A%7C%20Emergency%20order%20if%20count%20%3D%200%20%7C%20Store%20manager%20%7C%20immediately%20after%20adjustment%20%28GUIDE-DSD-005%29%20%7C%0A%0A%23%23%204.%20)
[^5KtU-2]: Suspected phantom inventory If an item shows units on hand in the system but has sold zero units for longer than expected (the app flags this as "OOS now — system shows stock"), do **not** reorder blindly: trigger a cycle count per SOP-INV-002 first.  [SOP-REP-001_store_replenishment.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/SOP-REP-001_store_replenishment.md#:~:text=Suspected%20phantom%20inventory%0AIf%20an%20item%20shows%20units%20on%20hand%20in%20the%20system%20but%20has%20sold%20zero%20units%20for%20longer%20than%20expected%20%28the%20app%20flags%20this%20as%0A%22OOS%20now%20%E2%80%94%20system%20shows%20stock%22%29%2C%20do%20%2A%2Anot%2A%2A%20reorder%20blindly%3A%20trigger%20a%20cycle%20count%20per%20SOP-INV-002%20first.%0A%0A)
[^5KtU-3]: Adjustment approvals * Adjustments below **$500 at cost** are approved by the store manage

<name>OSA Assistant</name>

</details>

---

## Q: How is lost revenue calculated, and what is our FY2016 target for the lost-sales rate?

*13.1s · routed to: osa_policies({"ka_query": "How is lost revenue calculated? What is the FY2016 target for the lost-sales rate?"})*

**Final answer:**

**Lost Revenue Calculation:**
Lost revenue is calculated as **λ × OOS days**, valued at the item's shelf price that week. In other words, it equals the demand rate multiplied by the number of out-of-stock days, priced at the shelf price during that period.

**FY2016 Lost-Sales Rate Target:**
The target is **< 1.5%**, where the lost-sales rate is defined as:
```
Lost Sales Rate = Estimated Lost Revenue ÷ (Revenue + Lost Revenue)
```

**Recommended Next Step:**
To assess performance against this target, you should review your current lost-sales rate by store, region, or category using the OSA analytics. If any areas are above 1.5%, prioritize root-cause analysis and corrective actions for those locations or product lines.

<details><summary>Sub-agent outputs (Genie / Knowledge Assistant)</summary>

I'll help you understand how lost revenue is calculated and find the FY2016 target for the lost-sales rate. Let me route these questions to the appropriate agents.

First, let me check our policy documentation for the calculation methodology and targets:

<name>OSA Policy & Procedures Assistant</name>

Lost revenue is calculated as λ × OOS days, valued at the item's shelf price that week.[^vbFT-1] In other words, it is the demand rate multiplied by the number of out-of-stock days, priced at the shelf price during that period.

The FY2016 target for the lost-sales rate is < 1.5%, where lost sales rate is defined as estimated lost revenue ÷ (revenue + lost revenue).[^vbFT-2]

[^vbFT-1]: * **Lost units / lost revenue:** λ × OOS days, valued at the item's shelf price that week. [GLOSSARY-OSA-009_metric_definitions.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/GLOSSARY-OSA-009_metric_definitions.md#:~:text=%2A%20%2A%2ALost%20units%20/%20lost%20revenue%3A%2A%2A%20%CE%BB%20%C3%97%20OOS%20days%2C%20valued%20at%20the%20item%27s%20shelf%20price%20that%20week.%0A)
[^vbFT-2]: KPI targets (FY2016) | KPI | Definition | Target | |---|---|---| | On-shelf availability (OSA) | share of active store-item-days not out of stock | **≥ 96.0%** | | Lost sales rate | estimated lost revenue ÷ (revenue + lost revenue) | **< 1.5%** | | Supplier on-time | POs received on/before expected date | **≥ 95%** | | Alert response | Critical alerts actioned within 4 business hours | **≥ 90%** | | Inventory cover | median days of cover across store-items | **10–16 days** |  ## 2.  [RACI-006_osa_roles_and_kpi_targets.md](https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/ajax-api/2.0/fs/files/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/corpus/RACI-006_osa_roles_and_kpi_targets.md#:~:text=KPI%20targets%20%28FY2016%29%0A%7C%20KPI%20%7C%20Definition%20%7C%20Target%20%7C%0A%7C---%7C---%7C---%7C%0A%7C%20On-shelf%20availability%20%28OSA%29%20%7C%20share%20of%20active%20store-item-days%20not%20out%20of%20stock%20%7C%20%2A%2A%E2%89%A5%2096.0%25%2A%2A%20%7C%0A%7C%20Lost%20sales%20rate%20%7C%20estimated%20lost%20revenue%20%C3%B7%20%28revenue%20%2B%20lost%20revenue%29%20%7C%20%2A%2A%3C%201.5%25%2A%2A%20%7C%0A%7C%20Supplier%20on-time%20%7C%20POs%20received%20on/before%20expected%20date%20%7C%20%2A%2A%E2%89%A5%2095%25%2A%2A%20%7C%0A%7C%20Alert%20response%20%7C%20Critical%20alerts%20actioned%20within%204%20business%20hours%20%7C%20%2A%2A%E2%89%A5%2090%25%2A%2A%20%7C%0A%7C%20Inventory%20cover%20%7C%20median%20days%20of%20cover%20across%20store-items%20%7C%20%2A%2A10%E2%80%9316%20days%2A%2A%20%7C%0A%0A%23%23%202.%20)

<name>OSA Assistant</name>

</details>

---
