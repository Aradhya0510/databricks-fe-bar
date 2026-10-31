# Task `generate_internal_docs` — FAILED

*Run 428630750781567 · started 2026-10-30 21:39:50 UTC · 7s*

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

src_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "docs_corpus"))
shutil.rmtree(DOCS + "/corpus", ignore_errors=True)
os.makedirs(DOCS + "/corpus/contracts", exist_ok=True)
for f in sorted(glob.glob(f"{src_dir}/*.md")):
    shutil.copy(f, f"{DOCS}/corpus/")
    print(f"published {os.path.basename(f)}")
```

**Output:**



```text
ERROR: ---------------------------------------------------------------------------
OSError                                   Traceback (most recent call last)
File <command-8599993747400923>, line 15
     13 os.makedirs(DOCS + "/corpus/contracts", exist_ok=True)
     14 for f in sorted(glob.glob(f"{src_dir}/*.md")):
---> 15     shutil.copy(f, f"{DOCS}/corpus/")
     16     print(f"published {os.path.basename(f)}")

File /usr/lib/python3.12/shutil.py:435, in copy(src, dst, follow_symlinks)
    433 if os.path.isdir(dst):
    434     dst = os.path.join(dst, os.path.basename(src))
--> 435 copyfile(src, dst, follow_symlinks=follow_symlinks)
    436 copymode(src, dst, follow_symlinks=follow_symlinks)
    437 return dst

File /usr/lib/python3.12/shutil.py:260, in copyfile(src, dst, follow_symlinks)
    258     os.symlink(os.readlink(src), dst)
    259 else:
--> 260     with open(src, 'rb') as fsrc:
    261         try:
    262             with open(dst, 'wb') as fdst:
    263                 # macOS

OSError: [Errno 5] Input/output error: '/Workspace/Users/aradhya.chouhan@databricks.com/.bundle/osa-retail/demo/files/src/docs_corpus/FAQ-010_osa_command_center.md'
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
    {"question": "How is a stockout day defined?", "expected_fact": "zero-sales streak with lambda*L >= 4.6 (probability < 1%)"},
]
with open(f"{DOCS}/eval_questions.json", "w") as fh:
    json.dump(eval_q, fh, indent=2)
display(spark.createDataFrame(pd.DataFrame(eval_q)))
```

```python
print("\n".join(sorted(os.path.relpath(p, DOCS) for p in glob.glob(f"{DOCS}/corpus/**/*.md", recursive=True))))
```
