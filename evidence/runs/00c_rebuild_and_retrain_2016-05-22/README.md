# Job run evidence: osa_01_nightly_osa_intelligence

* Run ID: `706109977409027` · Job ID: `497823472235375`
* Started: 2026-10-30 23:23:48 UTC · Ended: 2026-10-30 23:39:36 UTC
* Result: **FAILED**
* Run page: https://fevm-serverless-stable-4hkk7k.cloud.databricks.com/?o=7474659940257593#job/497823472235375/run/706109977409027

| task | type | result | duration (s) | evidence |
|---|---|---|---|---|
| governance_setup | notebook | SUCCESS | 32 | [governance_setup.md](governance_setup.md) |
| lakeflow_pipeline | pipeline | SUCCESS | 193 | [lakeflow_pipeline.md](lakeflow_pipeline.md) |
| governance_apply | notebook | SUCCESS | 72 | [governance_apply.md](governance_apply.md) |
| ingest_app_actions | notebook | SUCCESS | 44 | [ingest_app_actions.md](ingest_app_actions.md) |
| train_model | notebook | SUCCESS | 284 | [train_model.md](train_model.md) |
| score_and_recommend | notebook | SUCCESS | 405 | [score_and_recommend.md](score_and_recommend.md) |
| agent_tools | notebook | FAILED | 16 | [agent_tools.md](agent_tools.md) |
| intelligence_briefings | notebook | UPSTREAM_FAILED | 0 |  |
| refresh_lakebase_serving | notebook | DISABLED | 0 |  |
