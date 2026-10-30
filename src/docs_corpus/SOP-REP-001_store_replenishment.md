# SOP-REP-001 — Store Replenishment Standard Operating Procedure

**Owner:** Director of Replenishment · **Applies to:** all 10 stores (CA_1–CA_4, TX_1–TX_3, WI_1–WI_3) · **Version:** 4.2 (effective 2016-01-04)
*Fictitious internal document created for the OSA prototype.*

## 1. Purpose
Keep every active item on the shelf (target on-shelf availability, OSA, of **96% or higher**) while holding no more than
**16 days of cover** for any store-item.

## 2. Review cycle
Each store runs a **weekly periodic review** on a fixed weekday:

| Store | Review day | Store | Review day |
|---|---|---|---|
| CA_1 | Monday | TX_1 | Monday |
| CA_2 | Tuesday | TX_2 | Tuesday |
| CA_3 | Wednesday | TX_3 | Wednesday |
| CA_4 | Thursday | WI_1 | Monday |
| | | WI_2 | Tuesday |
| | | WI_3 | Wednesday |

On the review day the system proposes an order that brings the inventory position (on-hand + on-order) up to the
**order-up-to level = forecast daily demand × (review period 7 days + supplier contract lead time + safety days)**.
Safety days are 3 for A-tier suppliers, 4 for B-tier and 5 for C-tier suppliers.

## 3. Stockout-risk alerts (OSA Command Center)
Every night the stockout-risk model scores every store-item for the probability of going out of stock in the next
3 days. Alerts are tiered:

| Tier | Risk score | Required action | Deadline |
|---|---|---|---|
| **Critical** | ≥ 0.60 | Store manager must Approve, Override or Reject the recommended order | within **4 business hours** |
| **High** | 0.35 – 0.59 | Review the recommendation; approve if cover < 3 days | same business day |
| **Watch** | 0.15 – 0.34 | No action required; monitor | — |

## 4. Approving and overriding recommendations
* **Approve** places the recommended quantity as an expedited order with the item's contracted supplier.
* **Override** lets the store manager change the quantity. An override **must carry a reason code**:
  `PROMO_UPLIFT`, `LOCAL_EVENT`, `SHELF_CAPACITY`, `QUALITY_ISSUE`, `OTHER`.
* Overrides that increase the quantity by **more than 50%** of the recommendation, or any single order above
  **$2,500 at cost**, require Regional Manager approval.
* **Reject** must state why (e.g., item being delisted). Rejections are reviewed weekly by the Regional Manager.

## 5. When a PO is overdue
If a supplier PO is past its expected date and the item has **less than 2 days of cover**, the store manager raises an
emergency Direct Store Delivery (DSD) request per GUIDE-DSD-005 and the category buyer is notified per POL-SUP-003.

## 6. Suspected phantom inventory
If an item shows units on hand in the system but has sold zero units for longer than expected (the app flags this as
"OOS now — system shows stock"), do **not** reorder blindly: trigger a cycle count per SOP-INV-002 first.

## 7. Records
All approvals/overrides/rejections are recorded in the OSA Command Center and flow nightly into the lakehouse table
`replenishment_actions` for audit and model feedback.
