# GUIDE-DSD-005 — Direct Store Delivery (DSD) and Emergency Orders

**Owner:** Supply Planning · **Version:** 1.4
*Fictitious internal document created for the OSA prototype.*

## 1. When to use an emergency DSD order
Use emergency DSD only when **all** apply:
* the item has a Critical stockout-risk alert or is already out of stock,
* the regular supplier PO is overdue or will not land before cover runs out,
* the item is in an eligible department: **FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1**.
HOBBIES and HOUSEHOLD_2 items are not eligible for DSD; escalate to the category buyer instead.

## 2. Cut-off and lead time
* Requests submitted by **2:00 pm local time** are delivered next morning.
* Requests after the cut-off are delivered in two days.

## 3. Cost
Emergency DSD carries a **cost premium of 8%** over the contracted unit cost, plus a flat **$45 delivery fee** per
store per day. The premium is charged back to the supplier when the root cause is a late PO (POL-SUP-003).

## 4. Quantity
Order enough to cover **demand until the regular PO lands plus 3 days**, rounded up to the case pack. The OSA Command
Center's suggested quantity already follows this rule.
