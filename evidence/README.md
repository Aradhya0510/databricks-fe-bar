# Execution evidence (all plain text)

Everything below was produced by the deployed build on workspace `fevm-serverless-stable-4hkk7k` (profile `fevm-bar`)
on 2026-10-30/31 and exported **as text** — notebook cells with their real outputs, pipeline event-log metrics, SQL
results, HTTP responses of the live app, and agent outputs. Exporters live in `scripts/` and can be re-run.

## 1. Job runs (notebook code + real outputs, per task)

| Run | What it shows |
|---|---|
| [`runs/00_setup_land_and_simulate/`](runs/00_setup_land_and_simulate/README.md) | M5 download (sha256, file sizes) and landing; ERP/WMS simulation from real sales (8.3 M input rows → 5.6 M inventory snapshots, 1.4 M PO events; 180 daily partitions); first docs attempt that failed on a workspace-file read (fixed, see 00b) |
| [`runs/00b_setup_publish_docs/`](runs/00b_setup_publish_docs/README.md) | Internal document corpus + 21 supplier contract summaries published to the `docs` volume; KA evaluation questions |
| [`runs/01a_release_feed_2016-05-23/`](runs/01a_release_feed_2016-05-23/README.md) | "Tomorrow's" POS / inventory / PO files for 2016-05-23 released into landing, then the nightly job |
| [`runs/01_nightly_business_date_2016-05-23/`](runs/01_nightly_business_date_2016-05-23/README.md) | **Full nightly chain, 10 tasks:** governance → Lakeflow pipeline (incremental: only the new day's files ingested) → governance apply → model (champion reused) → Lakebase ingest → scoring + `ai_query` rationale → UC agent tools → agent briefings + MLflow evaluation → Lakebase synced-table refresh (Delta = Postgres row counts) → Postgres grants |
| [`runs/02_nightly_business_date_2016-05-24/`](runs/02_nightly_business_date_2016-05-24/README.md) | Second business day: the store decisions made in the app are read back from Lakebase and merged into Delta; new scores and briefings |
| [`runs/00c_rebuild_and_retrain_2016-05-22/`](runs/00c_rebuild_and_retrain_2016-05-22/README.md) | Full rebuild after tightening the stockout definition (runs > 28 days = delisted): pipeline recompute, **training of `osa_stockout_risk` v2 `@champion`** (split sizes, early stopping, test metrics vs. today's business rule, feature importance), scoring. Its `agent_tools` task failed on a SQL-UDF parameter scoping error that was fixed and re-run in 00d / 01 |
| [`runs/00d_briefing_agent_fix_2016-05-22/`](runs/00d_briefing_agent_fix_2016-05-22/README.md) | Briefing agent re-run after fixing reasoning-block parsing: 4 briefings, **all 7 evaluation scorers at 100 %** |

Key pipeline evidence: `runs/*/lakeflow_pipeline.md` — per-flow output rows and data-quality expectation results
(e.g. 483 inventory rows with null item, 155 with an unknown store, 725 PO events without quantity dropped on first load).

## 2. Stage-by-stage proof

| Stage | Evidence |
|---|---|
| Lakeflow ingest | `runs/*/lakeflow_pipeline.md`, [`data/table_inventory.md`](data/table_inventory.md) (every table, row counts, tags) |
| Unity Catalog governance | [`governance/persona_check.md`](governance/persona_check.md) — same queries as ADMIN vs. a real *South store manager* service principal: region row filter, masked commercial terms / cost / e-mails, denied bronze access; `runs/*/governance_apply.md` — policies, tags, grants, lineage from `system.access.table_lineage` |
| ML | `runs/00c_rebuild_and_retrain_2016-05-22/train_model.md`, [`ml/model_registry.md`](ml/model_registry.md), [`ml/forward_check.md`](ml/forward_check.md) (22-May predictions vs. real unseen 23/24-May Walmart sales) |
| GenAI | `runs/*/score_and_recommend.md` — `ai_query` rationales per alert, counts by source |
| Lakebase | [`lakebase/roundtrip.md`](lakebase/roundtrip.md) — synced-table row parity, app writes in Postgres read via UC catalog `osa_lakebase`, merged Delta rows; `runs/*/refresh_lakebase_serving.md` |
| Genie Agent | [`genie/benchmark.md`](genie/benchmark.md) — benchmark questions, Genie's generated SQL and results vs. reference SQL |
| Agents | [`agents/knowledge_assistant_eval.md`](agents/knowledge_assistant_eval.md), [`agents/supervisor_qa.md`](agents/supervisor_qa.md) (Supervisor routing Genie + Knowledge Assistant), [`agents/briefings.md`](agents/briefings.md) (agent-written reports), `runs/*/intelligence_briefings.md` (tool calls + `mlflow.genai.evaluate` scores) |
| Databricks App | [`app/api_responses.md`](app/api_responses.md) — live HTTP responses: Lakebase action queue and typeahead latency, approve/override/reject writes (incl. the SOP rule rejecting an override without reason code), briefings, Genie and Supervisor Q&A, governance view |
