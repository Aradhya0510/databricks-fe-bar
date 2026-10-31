# Knowledge Assistant evaluation — `ka-35e9950a-endpoint`

*2026-10-31 00:22 UTC. Questions and expected facts from `docs/eval_questions.json`; a question passes when ≥ 80% of the expected fact's key terms/numbers appear in the answer.*

**Score: 10/10 questions answered with the expected fact.**

## ✅ Within how many hours must a store manager act on a Critical stockout alert?

*Expected fact:* 4 business hours · *coverage* 100% · 5.9s

> A store manager must act on a Critical stockout alert within **4 business hours**
> . This requirement is documented in 
> SOP-REP-001, which specifies that for Critical alerts (risk score ≥ 0.60), the store manager must Approve, Override or Reject the recommended order within 4 business hours
> .

## ✅ What override size requires Regional Manager approval?

*Expected fact:* more than 50% increase or above $2,500 at cost · *coverage* 100% · 5.9s

> Overrides that increase the quantity by more than 50% of the recommendation, or any single order above $2,500 at cost, require Regional Manager approval.
> 
> 
> This requirement is documented in SOP-REP-001.

## ✅ What is the cost premium for an emergency DSD order?

*Expected fact:* 8% premium plus $45 delivery fee · *coverage* 100% · 5.5s

> Emergency DSD carries a cost premium of 8% over the contracted unit cost, plus a flat $45 delivery fee per store per day.
>  This information is found in document GUIDE-DSD-005.

## ✅ Which departments are eligible for emergency DSD?

*Expected fact:* FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1 · *coverage* 100% · 10.3s

> Emergency DSD is eligible for the following departments: FOODS_1, FOODS_2, FOODS_3, and HOUSEHOLD_1
> . 
> HOBBIES and HOUSEHOLD_2 items are not eligible for DSD; escalate to the category buyer instead
> .
> 
> This information is from document **GUIDE-DSD-005**.

## ✅ How quickly must a suspected phantom inventory item be cycle counted?

*Expected fact:* within 24 hours · *coverage* 100% · 4.0s

> A suspected phantom inventory item must be physically counted within **24 hours** of the flag, per SOP-INV-002
> .

## ✅ What is the on-time SLA for a C-tier supplier?

*Expected fact:* 92% · *coverage* 100% · 3.6s

> The on-time SLA for a C-tier supplier is 92%
> , as specified in 
> POL-SUP-003
> .

## ✅ What uplift applies to FOODS orders landing in a SNAP window?

*Expected fact:* 15% · *coverage* 100% · 3.7s

> Increase FOODS order quantities by 15% for orders landing in a SNAP window.
> 
> 
> This requirement is documented in 
> PLAY-PROMO-004 — Promotions, Events and SNAP Playbook
> .

## ✅ What is the FY2016 on-shelf availability target?

*Expected fact:* 96% · *coverage* 100% · 3.9s

> The FY2016 on-shelf availability (OSA) target is ≥ 96.0%
> , as documented in 
> RACI-006
> .

## ✅ What is the contract lead time for Golden Prairie Dairy Co?

*Expected fact:* 5 days · *coverage* 100% · 3.7s

> The contract lead time for Golden Prairie Dairy Co (SUP001) is 5 days from PO creation to expected receipt
> .

## ✅ How is a stockout day defined?

*Expected fact:* zero-sales streak with lambda*L >= 4.6 (probability < 1%), 2 to 28 days long · *coverage* 89% · 5.0s

> A stockout (out-of-stock, OOS) day is defined as a day inside a zero-sales streak of length L where e^(−λ·L) < 1% (i.e., λ·L ≥ 4.6), λ ≥ 0.3 units/day and 2 ≤ L ≤ 28.
>  
> The demand rate (λ) is an item-store's average daily unit sales over the previous 90 days.
> 
> 
> 
> For example, an item that normally sells 2 units/day is flagged after 3 consecutive zero-sales days; one that sells 0.5/day only after 10 days.
> 
> 
> This definition comes from **GLOSSARY-OSA-009**.
