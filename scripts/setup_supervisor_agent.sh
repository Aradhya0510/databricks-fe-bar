#!/usr/bin/env bash
# One-time: Agent Bricks Supervisor Agent = the app's Q&A bot over company data + documents.
#   tools: Genie Agent (analytics SQL over governed gold tables) + Knowledge Assistant (SOPs/policies/contracts).
#   The governed UC function tools (src/agents/01_agent_tools.py) are used by the briefing agent; attaching them as
#   Supervisor uc_function tools failed on this workspace ("Failed to register UC function tool"), so set
#   WITH_UC_TOOLS=1 to try them on another workspace.
set -euo pipefail
P=${PROFILE:-fevm-bar}
S=${S:-serverless_stable_4hkk7k_catalog.osa_retail}
GENIE_SPACE_ID=${GENIE_SPACE_ID:?set GENIE_SPACE_ID}
KA_ID=${KA_ID:-}

SA=$(databricks supervisor-agents list-supervisor-agents -p "$P" -o json | jq -r '.[] | select(.display_name=="OSA Assistant") | .name' | head -1)
if [ -z "$SA" ]; then
  SA=$(databricks supervisor-agents create-supervisor-agent "OSA Assistant" \
    --description "Q&A assistant for store, regional and supply-chain leaders on on-shelf availability: KPIs, stockouts, tonight's alerts, suppliers, and internal policy." \
    --instructions "You help retail operations leaders. Route numeric/analytical questions (OSA %, lost revenue, stockouts, supplier performance, trends, rankings, tonight's alerts and recommended orders for a store or item) to osa_analyst. Route questions about procedures, policies, SLAs, contracts, deadlines, costs of DSD, escalation rules and KPI targets to osa_policies. When a question mixes data and policy, call both and combine. Always quote figures exactly, name the store/item/supplier, cite document ids (e.g. POL-SUP-003) for policy, and end with a concrete recommended next step. The business date is the latest date in the data (2016), not today." \
    -p "$P" -o json | jq -r '.name')
  echo "created $SA"
fi

add_tool () {  # name json
  databricks supervisor-agents create-tool "$SA" "$1" --json "$2" -p "$P" -o json | jq -c '{name, tool_type}' || true
}
add_tool osa_analyst "{\"tool_type\":\"genie_space\",\"description\":\"Genie Agent over governed OSA gold tables: availability, lost sales, stockout events and root causes, supplier scorecards, tonight's alerts, sales history 2011-2016.\",\"genie_space\":{\"id\":\"$GENIE_SPACE_ID\"}}"
if [ -n "$KA_ID" ]; then
  add_tool osa_policies "{\"tool_type\":\"knowledge_assistant\",\"description\":\"Internal SOPs, supplier policy and contract summaries, promotions playbook, DSD rules, KPI targets, memos and post-mortems.\",\"knowledge_assistant\":{\"knowledge_assistant_id\":\"$KA_ID\"}}"
fi
[ "${WITH_UC_TOOLS:-0}" = "1" ] && for f in osa_item_risk osa_store_action_queue osa_open_purchase_orders osa_kpi_summary osa_supplier_watchlist; do
  add_tool "$f" "{\"tool_type\":\"uc_function\",\"description\":\"$(databricks functions get $S.$f -p "$P" -o json | jq -r '.comment' | sed 's/"/\\"/g')\",\"uc_function\":{\"name\":\"$S.$f\"}}"
done

databricks supervisor-agents create-example "$SA" -p "$P" --json '{"question":"Which suppliers caused the most stockouts recently and what does our policy say we must do?","guidelines":["Use osa_supplier_watchlist or osa_analyst for the ranking","Use osa_policies for POL-SUP-003 escalation ladder","Combine both into one answer with next steps"]}' >/dev/null || true
databricks supervisor-agents create-example "$SA" -p "$P" --json '{"question":"Can TX_2 raise an emergency DSD for a household cleaning item that is out of stock?","guidelines":["Use osa_policies (GUIDE-DSD-005): HOUSEHOLD_1 is eligible, 2pm cut-off, 8% premium + $45 fee","Optionally check osa_store_action_queue for TX_2"]}' >/dev/null || true

databricks supervisor-agents list-tools "$SA" -p "$P" -o json | jq -r '.[] | [.name, .tool_type] | @tsv'
databricks supervisor-agents get-supervisor-agent "$SA" -p "$P" -o json | jq '{name, display_name, endpoint_name}'
