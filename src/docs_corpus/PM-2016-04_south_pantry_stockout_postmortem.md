# PM-2016-04 — Post-mortem: Pantry stockouts in the South region (April 2016)

**Owner:** Sourcing · **Status:** Closed · **Severity:** Sev-2
*Fictitious example post-mortem created for the OSA prototype; figures are illustrative.*

## Summary
During the second and third weeks of April 2016, several FOODS_2 (pantry) items went out of stock in TX_1–TX_3.
The common factor was replenishment POs from a C-tier pantry supplier arriving 2–4 days after their expected date
while stores held less than one review cycle of cover.

## Timeline
* Day 0 – PO due; not received. Automatic late notification sent (POL-SUP-003 step 1).
* Day 2 – Cover below 2 days in 3 stores; buyer escalation did **not** happen because the alert was e-mail only.
* Day 3 – Shelves empty; emergency DSD requested after the 2 pm cut-off, delivered on Day 5.
* Day 5 – PO received; shelves restored.

## Root causes
1. Supplier carrier capacity shortfall (external).
2. No proactive signal: the overdue PO and low cover were visible in data two days before the shelf went empty, but
   nobody was alerted with a recommended action.
3. DSD request submitted after cut-off.

## Corrective actions
* Introduce a predictive stockout-risk alert with a recommended order and owner (→ OSA Command Center).
* Escalate automatically to the category buyer at 2 days late **or** cover < 2 days.
* Store managers to submit DSD requests before 2 pm when a Critical alert is open.
