# SOP-INV-002 — Inventory Accuracy and Cycle Counts

**Owner:** Store Operations · **Version:** 2.0 (effective 2015-09-01)
*Fictitious internal document created for the OSA prototype.*

## 1. Why it matters
Industry studies attribute 20–30% of retail out-of-stocks to **inventory record inaccuracy** ("phantom inventory"):
the system shows units on hand, so no replenishment is triggered, while the shelf is actually empty.

## 2. Phantom-inventory trigger
A store-item is flagged as **suspected phantom inventory** when **both** hold:
1. it has sold zero units for a streak whose probability under its normal demand rate is below 1%
   (the same statistical rule used for stockout inference, see GLOSSARY-OSA-009), **and**
2. the system on-hand is greater than zero.

## 3. Required response
| Step | Who | SLA |
|---|---|---|
| Physical count of shelf + backroom | Store associate | within **24 hours** of the flag |
| Inventory adjustment in ERP | Store manager | same day as the count |
| Emergency order if count = 0 | Store manager | immediately after adjustment (GUIDE-DSD-005) |

## 4. Adjustment approvals
* Adjustments below **$500 at cost** are approved by the store manager.
* Adjustments of **$500 or more** require Regional Manager sign-off within 2 business days.
* Repeated adjustments (3+ in 30 days) on the same item trigger a shrink investigation by Loss Prevention.

## 5. Scheduled cycle counts
* A-velocity items (top 20% by units): counted every **2 weeks**.
* B-velocity items: every **6 weeks**.
* C-velocity items: every **quarter**.
