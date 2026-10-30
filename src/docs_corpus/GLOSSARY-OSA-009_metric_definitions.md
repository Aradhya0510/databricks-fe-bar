# GLOSSARY-OSA-009 — OSA metric and model definitions

*Internal reference for analysts, created for the OSA prototype.*

* **Demand rate (λ):** an item-store's average daily unit sales over the previous 90 days.
* **Stockout (out-of-stock, OOS) day:** a day inside a zero-sales streak of length L where e^(−λ·L) < 1%
  (i.e., λ·L ≥ 4.6), λ ≥ 0.3 units/day and 2 ≤ L ≤ 28. Example: an item that normally sells 2 units/day is flagged
  after 3 consecutive zero-sales days; one that sells 0.5/day only after 10 days.
* **Inactive / delisted:** an implausible zero-sales streak longer than 28 days is treated as an assortment change
  (seasonal or discontinued item), not a shelf stockout, and is excluded from OSA % and lost sales.
* **Stockout event:** a maximal run of consecutive OOS days for a store-item.
* **On-shelf availability (OSA %):** 1 − (OOS store-item-days ÷ active store-item-days). Active = λ ≥ 0.3.
* **Lost units / lost revenue:** λ × OOS days, valued at the item's shelf price that week.
* **Days of cover:** on-hand units ÷ λ.
* **Root cause (stockout event):**
  * `SUPPLIER_DELAY` — a PO for the store-item was overdue when the run started.
  * `PHANTOM_INVENTORY` — system on-hand > 0 during the run.
  * `DEMAND_SPIKE` — 7-day sales before the run exceeded 1.5 × λ × 7, with no overdue PO.
  * `UNEXPLAINED` — none of the above.
* **Stockout-risk score:** model probability that a store-item that is in stock today will be out of stock on at least
  one of the next 3 days.
* **Precision@K:** share of the top-K alerts per day that actually went out of stock within 3 days.
* **Lost revenue captured:** share of next-3-day lost revenue that falls on items inside the daily alert list.
