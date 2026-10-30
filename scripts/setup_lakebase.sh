#!/usr/bin/env bash
# One-time Lakebase setup for the OSA prototype (Lakebase Autoscaling project my-fe-bar-project / production).
#  1. register the Postgres database in Unity Catalog as catalog osa_lakebase  (lets jobs read app writes via SQL)
#  2. create synced tables gold Delta -> Lakebase Postgres schema "serving"      (sub-second reads for the app)
# Synced tables are snapshot-refreshed by the nightly job (src/lakebase/02_refresh_synced_tables.py).
set -euo pipefail
P=${PROFILE:-fevm-bar}
PROJECT=${PROJECT:-my-fe-bar-project}
BRANCH=projects/$PROJECT/branches/production
LB=${LB:-osa_lakebase}
C=${CATALOG:-serverless_stable_4hkk7k_catalog}
S=${SCHEMA:-osa_retail}

databricks postgres get-catalog "catalogs/$LB" -p "$P" -o json >/dev/null 2>&1 || \
  databricks postgres create-catalog "$LB" -p "$P" -o json \
    --json "{\"spec\": {\"postgres_database\": \"databricks_postgres\", \"branch\": \"$BRANCH\"}}" | jq '{name, status}'

sync () {  # target source pk
  if databricks postgres get-synced-table "synced_tables/$LB.serving.$1" -p "$P" -o json >/dev/null 2>&1; then
    echo "exists: $LB.serving.$1"; return
  fi
  databricks postgres create-synced-table "$LB.serving.$1" -p "$P" -o json --no-wait --json "{
    \"spec\": {
      \"source_table_full_name\": \"$C.$S.$2\",
      \"primary_key_columns\": [$3],
      \"scheduling_policy\": \"SNAPSHOT\",
      \"branch\": \"$BRANCH\",
      \"postgres_database\": \"databricks_postgres\",
      \"create_database_objects_if_missing\": true,
      \"new_pipeline_spec\": {\"storage_catalog\": \"$C\", \"storage_schema\": \"$S\"}
    }}" | jq -c '{name: (.name // .metadata), done}'
}
sync replenishment_recommendations gold_replenishment_recommendations '"rec_id"'
sync stockout_risk_scores          gold_stockout_risk_scores          '"store_id", "item_id"'
if [ "${WITH_REPORTS:-0}" = "1" ]; then
  sync intelligence_reports        gold_intelligence_reports          '"report_id"'
fi
