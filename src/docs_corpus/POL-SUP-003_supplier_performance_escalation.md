# POL-SUP-003 — Supplier Performance and Escalation Policy

**Owner:** VP Sourcing · **Version:** 3.1 (effective 2016-02-01)
*Fictitious internal document created for the OSA prototype.*

## 1. Definitions
* **On-time:** the PO is received on or before its expected date.
* **Days late:** received date minus expected date (0 if on time).
* **Fill rate:** units received ÷ units ordered.
* **Attributed stockout:** an out-of-stock run that starts while a PO for the same store-item is overdue.

## 2. Supplier tiers
| Tier | On-time SLA | Fill-rate SLA | Late penalty (chargeback) | Safety days in order-up-to |
|---|---|---|---|---|
| A | 97% | 98% | 1.0% of PO value | 3 |
| B | 95% | 96% | 1.5% of PO value | 4 |
| C | 92% | 94% | 2.0% of PO value | 5 |

Individual contract terms are listed in the supplier contract summaries (CONTRACT-SUPxxx documents).

## 3. Escalation ladder
| Trigger | Action | Owner |
|---|---|---|
| PO 1 day late | Automatic notification to supplier account manager | System |
| PO 2 days late **or** item cover < 2 days | Category buyer calls the supplier account manager; store may raise emergency DSD | Category buyer |
| PO 3+ days late, **or** 2+ attributed stockouts for the same supplier in one week | Sourcing review; corrective action plan due in 5 business days | Sourcing manager |
| Supplier below on-time SLA for 4 consecutive weeks | Tier downgrade review; volume reallocation to alternate supplier | VP Sourcing |

## 4. Chargebacks
Late penalties are applied per PO at the contract rate. Chargebacks are waived for force-majeure events declared by
Sourcing. Penalty revenue is **not** a substitute for availability — the KPI that matters is lost sales.

## 5. Quarterly business review
Every supplier with more than **$250k** quarterly spend has a QBR covering on-time %, fill rate, attributed stockouts
and lost sales attributable to the supplier.
