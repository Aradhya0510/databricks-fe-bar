#!/usr/bin/env bash
# One-time: Agent Bricks Knowledge Assistant over the internal document corpus (docs volume).
set -euo pipefail
P=${PROFILE:-fevm-bar}
CATALOG=${CATALOG:-serverless_stable_4hkk7k_catalog}
SCHEMA=${SCHEMA:-osa_retail}

KA=$(databricks knowledge-assistants create-knowledge-assistant "OSA Policy & Procedures Assistant" \
  "Answers questions about the retailer's internal replenishment SOPs, inventory accuracy procedures, supplier SLAs and escalation policy, promotions playbook, DSD rules, KPI targets, memos and post-mortems." \
  --instructions "Answer only from the internal documents. Always cite the document id (e.g. SOP-REP-001, POL-SUP-003, CONTRACT-SUP007) and quote exact thresholds, deadlines and percentages. If the documents do not cover the question, say so." \
  -p "$P" -o json | jq -r '.name')
echo "created $KA"

databricks knowledge-assistants create-knowledge-source "$KA" -p "$P" --json "{
  \"display_name\": \"Internal SOPs, policies and contracts\",
  \"description\": \"Replenishment SOPs, supplier policy and contract summaries, playbooks, memos, post-mortems, metric glossary\",
  \"source_type\": \"files\",
  \"files\": {\"path\": \"/Volumes/${CATALOG}/${SCHEMA}/docs/corpus/\"}
}" -o json | jq '{name, state}'

databricks knowledge-assistants sync-knowledge-sources "$KA" -p "$P"
databricks knowledge-assistants get-knowledge-assistant "$KA" -p "$P" -o json | jq '{name, display_name, state, endpoint_name}'
