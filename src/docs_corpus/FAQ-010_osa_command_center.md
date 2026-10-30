# FAQ-010 — OSA Command Center for store managers

*Fictitious internal help article created for the OSA prototype.*

**What is the action queue?** Each morning it lists the store-items most likely to go out of stock in the next 3 days,
with a recommended order quantity and a one-line reason (e.g., "PO due 2 days ago not received; 1.4 days of cover").

**What does Approve do?** It places the recommended quantity as an expedited order and records your decision.

**When should I override?** When you know something the model does not: a local event, a shelf-capacity limit, a
quality issue. Always pick a reason code (SOP-REP-001 §4).

**Why does an item show "OOS now — system shows stock"?** It has stopped selling while the system still reports units
on hand — likely phantom inventory. Do a cycle count first (SOP-INV-002).

**Where do the numbers come from?** Sales come from point-of-sale, inventory and POs from the ERP; everything is
curated in the lakehouse and refreshed nightly. Ask the assistant "how is lost revenue calculated?" for definitions.

**Who sees my decisions?** Your Regional Manager and Supply Planning; decisions also feed back into next day's model
scoring (approved quantities count as on-order).
