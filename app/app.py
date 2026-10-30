"""OSA Command Center — Databricks App (FastAPI).

Data paths:
  * Lakebase Postgres (operational, sub-second):  serving.* synced tables (action queue, risk scores, briefings)
                                                  + osa_app.replenishment_actions (store decisions, written here)
  * SQL warehouse (analytical):                    gold KPI tables for tiles and trends
  * Agents:                                        Supervisor Agent endpoint (Genie + Knowledge Assistant + UC tools)
                                                  and the Genie Conversation API for SQL-transparent answers
"""
import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Optional

import psycopg
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

log = logging.getLogger("osa")
logging.basicConfig(level=logging.INFO)

CATALOG = os.environ.get("OSA_CATALOG", "serverless_stable_4hkk7k_catalog")
SCHEMA = os.environ.get("OSA_SCHEMA", "osa_retail")
S = f"{CATALOG}.{SCHEMA}"
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")
SUPERVISOR_ENDPOINT = os.environ.get("SUPERVISOR_ENDPOINT")
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID")
APP_SCHEMA = "osa_app"
SERVING_SCHEMA = "serving"

w = WorkspaceClient()

# ---------------------------------------------------------------------------------------------------------------
# Lakebase connection pool with OAuth token rotation
# ---------------------------------------------------------------------------------------------------------------
_token = {"value": None, "at": 0.0}
_token_lock = threading.Lock()


def lakebase_token() -> str:
    with _token_lock:
        if not _token["value"] or time.time() - _token["at"] > 40 * 60:
            endpoint = os.environ.get("LAKEBASE_ENDPOINT")
            if endpoint:
                _token["value"] = w.postgres.generate_database_credential(endpoint=endpoint).token
            else:
                _token["value"] = w.config.oauth_token().access_token
            _token["at"] = time.time()
        return _token["value"]


class TokenConnection(psycopg.Connection):
    @classmethod
    def connect(cls, conninfo: str = "", **kwargs):
        kwargs["password"] = lakebase_token()
        return super().connect(conninfo, **kwargs)


pool: Optional[ConnectionPool] = None


def get_pool() -> ConnectionPool:
    global pool
    if pool is None:
        pool = ConnectionPool(
            conninfo="", connection_class=TokenConnection, min_size=1, max_size=6, max_lifetime=45 * 60,
            kwargs=dict(host=os.environ["PGHOST"], port=int(os.environ.get("PGPORT", "5432")),
                        dbname=os.environ.get("PGDATABASE", "databricks_postgres"), user=os.environ["PGUSER"],
                        sslmode=os.environ.get("PGSSLMODE", "require"), row_factory=dict_row, autocommit=True),
            open=True)
    return pool


@contextmanager
def pg():
    with get_pool().connection() as conn:
        yield conn


def pg_query(sql: str, params=None):
    with pg() as conn:
        return conn.execute(sql, params or ()).fetchall()


def init_app_schema():
    """The app's service principal creates and owns its own schema (see Lakebase permission model)."""
    with pg() as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA}")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.replenishment_actions (
              action_id       UUID PRIMARY KEY,
              rec_id          TEXT NOT NULL,
              store_id        TEXT NOT NULL,
              item_id         TEXT NOT NULL,
              action          TEXT NOT NULL CHECK (action IN ('APPROVE', 'OVERRIDE', 'REJECT', 'CYCLE_COUNT_DONE')),
              final_qty       INTEGER,
              reason_code     TEXT,
              note            TEXT,
              decided_by      TEXT,
              decided_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
              recommended_qty INTEGER,
              risk_tier       TEXT)""")
        conn.execute(f"CREATE INDEX IF NOT EXISTS ix_actions_rec ON {APP_SCHEMA}.replenishment_actions (rec_id, decided_at DESC)")
        conn.execute(f"ALTER TABLE {APP_SCHEMA}.replenishment_actions REPLICA IDENTITY FULL")


# ---------------------------------------------------------------------------------------------------------------
# SQL warehouse helper (analytics)
# ---------------------------------------------------------------------------------------------------------------
def sql(statement: str, params: Optional[dict] = None):
    from databricks.sdk.service.sql import StatementParameterListItem
    p = [StatementParameterListItem(name=k, value=str(v)) for k, v in (params or {}).items()]
    r = w.statement_execution.execute_statement(statement=statement, warehouse_id=WAREHOUSE_ID, parameters=p or None,
                                                wait_timeout="30s")
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(1)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        raise HTTPException(500, f"SQL failed: {r.status.error.message if r.status.error else r.status.state}")
    cols = [c.name for c in r.manifest.schema.columns]
    return [dict(zip(cols, row)) for row in (r.result.data_array or [])] if r.result else []


# ---------------------------------------------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------------------------------------------
app = FastAPI(title="OSA Command Center")


@app.on_event("startup")
def startup():
    try:
        init_app_schema()
        log.info("Lakebase app schema ready")
    except Exception as e:  # app still serves analytics if Lakebase is unavailable
        log.exception("Lakebase init failed: %s", e)


@app.get("/api/health")
def health():
    status = {"app": "ok"}
    try:
        status["lakebase"] = pg_query("SELECT current_user AS role, now() AS ts")[0]
    except Exception as e:
        status["lakebase"] = f"error: {e}"
    status["warehouse_id"] = WAREHOUSE_ID
    status["supervisor_endpoint"] = SUPERVISOR_ENDPOINT
    status["genie_space_id"] = GENIE_SPACE_ID
    return status


@app.get("/api/context")
def context():
    rows = pg_query(f"""SELECT max(score_date) AS score_date, count(*) AS open_recommendations,
                               max(model_version) AS model_version,
                               sum(CASE WHEN risk_tier = 'CRITICAL' THEN 1 ELSE 0 END) AS critical
                        FROM {SERVING_SCHEMA}.replenishment_recommendations""")
    return rows[0]


@app.get("/api/kpis")
def kpis(region: str = "ALL"):
    summary = sql(f"SELECT * FROM {S}.osa_kpi_summary(:region)", {"region": region})
    trend = sql(f"""SELECT date, region, round(100 * (1 - sum(oos_store_items) / sum(active_store_items)), 2) AS osa_pct,
                           round(sum(lost_revenue), 0) AS lost_revenue
                    FROM {S}.gold_osa_kpi_daily
                    WHERE date > (SELECT max(date) FROM {S}.gold_osa_kpi_daily) - INTERVAL 56 DAYS
                      AND (:region = 'ALL' OR region = :region)
                    GROUP BY date, region ORDER BY date""", {"region": region})
    at_risk = pg_query(f"""SELECT risk_tier, count(*) AS items, round(sum(revenue_at_risk_3d)::numeric, 0) AS revenue_at_risk_3d
                           FROM {SERVING_SCHEMA}.replenishment_recommendations
                           WHERE %s = 'ALL' OR region = %s GROUP BY risk_tier""", (region, region))
    return {"summary": summary, "trend": trend, "at_risk": at_risk}


@app.get("/api/queue")
def queue(store: str = "ALL", tier: str = "ALL", limit: int = 100):
    return pg_query(f"""
        SELECT r.rec_id, r.priority_rank, r.score_date, r.store_id, r.region, r.item_id, r.item_name, r.dept_id,
               r.supplier_name, r.risk_tier, round(r.risk_score::numeric, 3) AS risk_score, r.recommended_action,
               r.recommended_qty, r.on_hand_units, r.on_order_units, r.days_of_cover, r.overdue_po_count,
               r.max_days_overdue, r.revenue_at_risk_3d, r.rationale, r.rationale_source,
               a.action AS decision, a.final_qty AS decision_qty, a.decided_by, a.decided_at
        FROM {SERVING_SCHEMA}.replenishment_recommendations r
        LEFT JOIN LATERAL (
            SELECT action, final_qty, decided_by, decided_at FROM {APP_SCHEMA}.replenishment_actions x
            WHERE x.rec_id = r.rec_id ORDER BY decided_at DESC LIMIT 1) a ON TRUE
        WHERE (%(store)s = 'ALL' OR r.store_id = %(store)s) AND (%(tier)s = 'ALL' OR r.risk_tier = %(tier)s)
        ORDER BY r.revenue_at_risk_3d DESC LIMIT %(limit)s""", {"store": store, "tier": tier, "limit": min(limit, 500)})


class Decision(BaseModel):
    rec_id: str
    action: str = Field(pattern="^(APPROVE|OVERRIDE|REJECT|CYCLE_COUNT_DONE)$")
    final_qty: Optional[int] = None
    reason_code: Optional[str] = None
    note: Optional[str] = None


@app.post("/api/decision")
def decide(d: Decision, request: Request):
    rec = pg_query(f"SELECT rec_id, store_id, item_id, recommended_qty, risk_tier FROM {SERVING_SCHEMA}.replenishment_recommendations WHERE rec_id = %s", (d.rec_id,))
    if not rec:
        raise HTTPException(404, "unknown recommendation")
    rec = rec[0]
    if d.action == "OVERRIDE" and not d.reason_code:
        raise HTTPException(400, "overrides require a reason code (SOP-REP-001 §4)")
    qty = d.final_qty if d.action == "OVERRIDE" else (rec["recommended_qty"] if d.action == "APPROVE" else 0)
    user = request.headers.get("x-forwarded-email") or request.headers.get("x-forwarded-preferred-username") or "unknown"
    row = pg_query(f"""INSERT INTO {APP_SCHEMA}.replenishment_actions
                       (action_id, rec_id, store_id, item_id, action, final_qty, reason_code, note, decided_by, recommended_qty, risk_tier)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
                   (str(uuid.uuid4()), rec["rec_id"], rec["store_id"], rec["item_id"], d.action, qty, d.reason_code,
                    d.note, user, rec["recommended_qty"], rec["risk_tier"]))
    needs_rm = d.action == "OVERRIDE" and rec["recommended_qty"] and qty > 1.5 * rec["recommended_qty"]
    return {"saved": row[0], "requires_regional_manager_approval": bool(needs_rm)}


@app.get("/api/decisions")
def decisions(limit: int = 50):
    return pg_query(f"SELECT * FROM {APP_SCHEMA}.replenishment_actions ORDER BY decided_at DESC LIMIT %s", (min(limit, 500),))


@app.get("/api/items")
def items(q: str, store: str = "ALL"):
    t0 = time.time()
    rows = pg_query(f"""SELECT store_id, item_id, item_name, dept_id, risk_tier, round(risk_score::numeric, 3) AS risk_score,
                               driver_1, driver_2, driver_3, on_hand_units, on_order_units, days_of_cover,
                               round(lambda_90d::numeric, 2) AS demand_per_day, overdue_po_count, revenue_at_risk_3d
                        FROM {SERVING_SCHEMA}.stockout_risk_scores
                        WHERE (item_id ILIKE %(q)s OR item_name ILIKE %(q)s) AND (%(store)s = 'ALL' OR store_id = %(store)s)
                        ORDER BY risk_score DESC LIMIT 25""", {"q": f"%{q}%", "store": store})
    return {"latency_ms": round(1000 * (time.time() - t0), 1), "rows": rows}


@app.get("/api/briefings")
def briefings():
    return pg_query(f"""SELECT report_id, report_date, audience, region, title, markdown, model, generated_at
                        FROM {SERVING_SCHEMA}.intelligence_reports ORDER BY report_date DESC,
                        CASE audience WHEN 'executive' THEN 0 ELSE 1 END, region""")


class Ask(BaseModel):
    question: str
    mode: str = "assistant"
    conversation_id: Optional[str] = None


def ask_supervisor(question: str):
    client = w.serving_endpoints.get_open_ai_client()
    t0 = time.time()
    resp = client.responses.create(model=SUPERVISOR_ENDPOINT, input=[{"role": "user", "content": question}])
    steps = []
    for item in resp.output or []:
        kind = getattr(item, "type", "")
        if kind == "function_call":
            steps.append({"tool": getattr(item, "name", ""), "arguments": getattr(item, "arguments", "")[:300]})
    text = resp.output_text if hasattr(resp, "output_text") else str(resp)
    return {"mode": "assistant", "answer": text, "steps": steps, "latency_s": round(time.time() - t0, 1)}


def ask_genie(question: str, conversation_id: Optional[str]):
    t0 = time.time()
    if conversation_id:
        msg = w.genie.create_message_and_wait(GENIE_SPACE_ID, conversation_id, question)
    else:
        msg = w.genie.start_conversation_and_wait(GENIE_SPACE_ID, question)
    out = {"mode": "genie", "conversation_id": msg.conversation_id, "answer": "", "sql": None, "columns": [], "rows": []}
    parts = []
    for att in msg.attachments or []:
        if att.text and att.text.content:
            parts.append(att.text.content)
        if att.query:
            out["sql"] = att.query.query
            if att.query.description:
                parts.append(att.query.description)
            res = w.genie.get_message_attachment_query_result(GENIE_SPACE_ID, msg.conversation_id, msg.id, att.attachment_id)
            sr = res.statement_response
            if sr and sr.manifest:
                out["columns"] = [c.name for c in sr.manifest.schema.columns]
                out["rows"] = (sr.result.data_array or [])[:50] if sr.result else []
    out["answer"] = "\n\n".join(parts)
    out["latency_s"] = round(time.time() - t0, 1)
    return out


@app.post("/api/ask")
def ask(a: Ask):
    try:
        if a.mode == "genie":
            return ask_genie(a.question, a.conversation_id)
        return ask_supervisor(a.question)
    except Exception as e:
        log.exception("ask failed")
        raise HTTPException(502, f"agent call failed: {e}")


@app.get("/api/governance")
def governance():
    """What this app's identity is allowed to see — UC row filters and column masks enforced for the app too."""
    ident = sql("SELECT current_user() AS identity")
    masked = sql(f"""SELECT supplier_id, supplier_name, late_penalty_pct_of_po, payment_terms, account_manager_email
                     FROM {S}.dim_supplier ORDER BY supplier_id LIMIT 3""")
    regions = sql(f"SELECT region, count(*) AS rows FROM {S}.gold_osa_kpi_daily GROUP BY region ORDER BY region")
    return {"identity": ident, "dim_supplier_sample": masked, "kpi_rows_by_region": regions}


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("DATABRICKS_APP_PORT", 8000)))
