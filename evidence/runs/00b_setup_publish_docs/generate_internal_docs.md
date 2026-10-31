# Task `generate_internal_docs` — SUCCESS

*Run 895834552222777 · started 2026-10-30 23:22:56 UTC · 29s*

# 03 · Publish the internal document corpus to the `docs` volume

The Q&A assistant answers questions on the company's **internal** knowledge: SOPs, supplier policy, playbooks,
post-mortems, memos. All documents are fictitious and authored for this prototype (`src/docs_corpus/`).
In addition, one contract summary per supplier is rendered from the supplier master so that contract
terms in documents and in the data agree.

```python
dbutils.widgets.text("catalog", "serverless_stable_4hkk7k_catalog")
dbutils.widgets.text("schema", "osa_retail")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
DOCS = f"/Volumes/{catalog}/{schema}/docs"
RAW = f"/Volumes/{catalog}/{schema}/raw"

import os, glob, shutil, json
import pandas as pd
from databricks.sdk import WorkspaceClient

# Bundle files live in the workspace file tree; read them through the Workspace API.
w = WorkspaceClient()
nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
src_dir = "/".join(nb_path.split("/")[:-2]) + "/docs_corpus"
shutil.rmtree(DOCS + "/corpus", ignore_errors=True)
os.makedirs(DOCS + "/corpus/contracts", exist_ok=True)
for obj in sorted(w.workspace.list(src_dir), key=lambda o: o.path):
    if not obj.path.endswith(".md"):
        continue
    with w.workspace.download(obj.path) as fh, open(f"{DOCS}/corpus/{os.path.basename(obj.path)}", "wb") as out:
        out.write(fh.read())
    print(f"published {os.path.basename(obj.path)}")
```

**Output:**

```text
published FAQ-010_osa_command_center.md
published GLOSSARY-OSA-009_metric_definitions.md
published GUIDE-DSD-005_direct_store_delivery_emergency_orders.md
published MEMO-2016-05-16_weekly_ops_memo.md
published PLAY-PROMO-004_promotions_events_playbook.md
published PM-2016-04_south_pantry_stockout_postmortem.md
published POL-SUP-003_supplier_performance_escalation.md
published RACI-006_osa_roles_and_kpi_targets.md
published SOP-INV-002_inventory_accuracy_cycle_counts.md
published SOP-REP-001_store_replenishment.md
```

```python
suppliers = pd.read_csv(f"{RAW}/erp/suppliers/suppliers.csv")

tmpl = """# CONTRACT-{supplier_id} — Supply agreement summary: {supplier_name}

*Fictitious contract summary generated for the OSA prototype from the supplier master.*

| Term | Value |
|---|---|
| Supplier | {supplier_name} ({supplier_id}) |
| Primary department | {primary_dept_id} |
| Reliability tier | {reliability_tier} |
| Contract lead time | {contract_lead_time_days} days from PO creation to expected receipt |
| On-time SLA | {contract_on_time_sla_pct:.0f}% of POs received on or before the expected date |
| Fill-rate SLA | {contract_fill_rate_sla_pct:.0f}% of ordered units |
| Late-delivery penalty | {late_penalty_pct_of_po:.1f}% of PO value per late PO |
| Payment terms | {payment_terms} |
| Account manager | {account_manager_email} |

## Escalation
Late POs are escalated per POL-SUP-003: automatic notice at 1 day late, category-buyer call at 2 days late or when
store cover drops below 2 days, sourcing review at 3+ days late or 2+ attributed stockouts in a week.

## Emergency supply
If a {supplier_name} PO is overdue for a DSD-eligible department, stores may raise an emergency DSD order
(GUIDE-DSD-005); the 8% DSD premium is charged back to {supplier_name} when the root cause is a late PO.
"""
for row in suppliers.to_dict("records"):
    with open(f"{DOCS}/corpus/contracts/CONTRACT-{row['supplier_id']}.md", "w") as fh:
        fh.write(tmpl.format(**row))
print(f"rendered {len(suppliers)} contract summaries")
```

**Output:**

```text
rendered 21 contract summaries
```

```python
# Evaluation questions with expected facts, used to verify the Knowledge Assistant / Supervisor Agent answers
eval_q = [
    {"question": "Within how many hours must a store manager act on a Critical stockout alert?", "expected_fact": "4 business hours"},
    {"question": "What override size requires Regional Manager approval?", "expected_fact": "more than 50% increase or above $2,500 at cost"},
    {"question": "What is the cost premium for an emergency DSD order?", "expected_fact": "8% premium plus $45 delivery fee"},
    {"question": "Which departments are eligible for emergency DSD?", "expected_fact": "FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1"},
    {"question": "How quickly must a suspected phantom inventory item be cycle counted?", "expected_fact": "within 24 hours"},
    {"question": "What is the on-time SLA for a C-tier supplier?", "expected_fact": "92%"},
    {"question": "What uplift applies to FOODS orders landing in a SNAP window?", "expected_fact": "15%"},
    {"question": "What is the FY2016 on-shelf availability target?", "expected_fact": "96%"},
    {"question": f"What is the contract lead time for {suppliers.supplier_name[0]}?", "expected_fact": f"{suppliers.contract_lead_time_days[0]} days"},
    {"question": "How is a stockout day defined?", "expected_fact": "zero-sales streak with lambda*L >= 4.6 (probability < 1%), 2 to 28 days long"},
]
with open(f"{DOCS}/eval_questions.json", "w") as fh:
    json.dump(eval_q, fh, indent=2)
display(spark.createDataFrame(pd.DataFrame(eval_q)))
```

**Output:**

| question | expected_fact |
|---|---|
| Within how many hours must a store manager act on a Critical stockout alert? | 4 business hours |
| What override size requires Regional Manager approval? | more than 50% increase or above $2,500 at cost |
| What is the cost premium for an emergency DSD order? | 8% premium plus $45 delivery fee |
| Which departments are eligible for emergency DSD? | FOODS_1, FOODS_2, FOODS_3, HOUSEHOLD_1 |
| How quickly must a suspected phantom inventory item be cycle counted? | within 24 hours |
| What is the on-time SLA for a C-tier supplier? | 92% |
| What uplift applies to FOODS orders landing in a SNAP window? | 15% |
| What is the FY2016 on-shelf availability target? | 96% |
| What is the contract lead time for Golden Prairie Dairy Co? | 5 days |
| How is a stockout day defined? | zero-sales streak with lambda*L >= 4.6 (probability < 1%), 2 to 28 days long |

```python
print("\n".join(sorted(os.path.relpath(p, DOCS) for p in glob.glob(f"{DOCS}/corpus/**/*.md", recursive=True))))
```

**Output:**

```text
corpus/FAQ-010_osa_command_center.md
corpus/GLOSSARY-OSA-009_metric_definitions.md
corpus/GUIDE-DSD-005_direct_store_delivery_emergency_orders.md
corpus/MEMO-2016-05-16_weekly_ops_memo.md
corpus/PLAY-PROMO-004_promotions_events_playbook.md
corpus/PM-2016-04_south_pantry_stockout_postmortem.md
corpus/POL-SUP-003_supplier_performance_escalation.md
corpus/RACI-006_osa_roles_and_kpi_targets.md
corpus/SOP-INV-002_inventory_accuracy_cycle_counts.md
corpus/SOP-REP-001_store_replenishment.md
corpus/contracts/CONTRACT-SUP001.md
corpus/contracts/CONTRACT-SUP002.md
corpus/contracts/CONTRACT-SUP003.md
corpus/contracts/CONTRACT-SUP004.md
corpus/contracts/CONTRACT-SUP005.md
corpus/contracts/CONTRACT-SUP006.md
corpus/contracts/CONTRACT-SUP007.md
corpus/contracts/CONTRACT-SUP008.md
corpus/contracts/CONTRACT-SUP009.md
corpus/contracts/CONTRACT-SUP010.md
corpus/contracts/CONTRACT-SUP011.md
corpus/contracts/CONTRACT-SUP012.md
corpus/contracts/CONTRACT-SUP013.md
corpus/contracts/CONTRACT-SUP014.md
corpus/contracts/CONTRACT-SUP015.md
corpus/contracts/CONTRACT-SUP016.md
corpus/contracts/CONTRACT-SUP017.md
corpus/contracts/CONTRACT-SUP018.md
corpus/contracts/CONTRACT-SUP019.md
corpus/contracts/CONTRACT-SUP020.md
corpus/contracts/CONTRACT-SUP021.md
```
