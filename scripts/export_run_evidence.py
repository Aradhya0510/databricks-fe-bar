#!/usr/bin/env python3
"""Export a Databricks job run as plain-text execution evidence (Markdown).

For every task in the run:
  * notebook tasks  -> code cells + their real outputs (stdout, tables, errors) decoded from `jobs export-run`
  * pipeline tasks  -> update status, per-flow row counts and expectation (data quality) metrics from the event log
A run summary (task, state, duration, run URL) is written to <out>/README.md.

Usage: scripts/export_run_evidence.py <job_run_id> <out_dir> [--profile fevm-bar]
Only uses the Python standard library and the `databricks` CLI.
"""
import argparse, base64, json, os, re, subprocess, sys, urllib.parse
from datetime import datetime, timezone

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
MAX_ROWS = 40


def cli(*args, profile):
    out = subprocess.run(["databricks", *args, "-p", profile, "-o", "json"], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout) if out.stdout.strip() else {}


def ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if ms else ""


def md_table(schema, rows):
    cols = [c["name"] for c in schema]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows[:MAX_ROWS]:
        lines.append("| " + " | ".join("" if v is None else str(v).replace("|", "\\|").replace("\n", " ") for v in r) + " |")
    if len(rows) > MAX_ROWS:
        lines.append(f"\n*… {len(rows) - MAX_ROWS} more rows*")
    return "\n".join(lines)


def render_result(res):
    if not res:
        return ""
    t, data = res.get("type"), res.get("data")
    if t == "listResults":
        return "\n\n".join(filter(None, (render_result(r) for r in data)))
    if t in ("ansi", "text"):
        txt = ANSI.sub("", data if isinstance(data, str) else str(data)).rstrip()
        return f"```text\n{txt}\n```" if txt else ""
    if t == "table":
        return md_table(res.get("schema", []), data)
    if t == "mimeBundle":
        txt = (data or {}).get("text/plain", "")
        return "" if txt.startswith("DataFrame[") or not txt else f"```text\n{txt}\n```"
    if t == "error":
        return f"```text\nERROR: {ANSI.sub('', str(res.get('summary') or data))[:3000]}\n```"
    if t == "html":
        return ""
    return f"```text\n{str(data)[:2000]}\n```"


def notebook_md(task_run, profile):
    exp = cli("jobs", "export-run", str(task_run["run_id"]), "--views-to-export", "CODE", profile=profile)
    html = exp["views"][0]["content"]
    model = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']*)'", html).group(1)
    nb = json.loads(urllib.parse.unquote(base64.b64decode(model).decode()))
    out = []
    for c in nb["commands"]:
        code = c.get("command", "")
        if code.lstrip().startswith("%md"):
            out.append(re.sub(r"^%md\s?", "", code.lstrip()).replace("\n%md", "\n"))
            continue
        out.append(f"```python\n{code.strip()}\n```")
        rendered = render_result(c.get("results"))
        if c.get("error"):
            rendered += f"\n\n```text\nERROR: {ANSI.sub('', c['error'])[:3000]}\n```"
        if rendered.strip():
            out.append("**Output:**\n\n" + rendered)
    return "\n\n".join(out)


def pipeline_md(task_run, profile):
    pt = task_run.get("pipeline_task", {})
    pid = pt.get("pipeline_id")
    start = task_run.get("start_time", 0)
    updates = cli("pipelines", "list-updates", pid, profile=profile).get("updates", [])
    after = [u for u in updates if u.get("creation_time", 0) >= start - 60000]
    update_id = min(after, key=lambda u: u["creation_time"])["update_id"] if after else None
    lines = [f"Pipeline `{pid}` · update `{update_id}` · state **{next((u['state'] for u in updates if u['update_id'] == update_id), '?')}**\n",
             "Metrics read from the pipeline event log (`event_log()` table-valued function).\n"]
    base = f"FROM event_log('{pid}') WHERE origin.update_id = '{update_id}' AND event_type = 'flow_progress'"
    flows = sql_rows(f"""SELECT element_at(split(origin.flow_name, '\\\\.'), -1) AS flow,
               sum(coalesce(details:flow_progress.metrics.num_output_rows::bigint, 0)) AS output_rows,
               sum(coalesce(details:flow_progress.data_quality.dropped_records::bigint, 0)) AS dropped_by_expectations,
               round(timestampdiff(MILLISECOND, min(timestamp), max(timestamp)) / 1000, 1) AS seconds
        {base} AND origin.flow_name IS NOT NULL GROUP BY 1 ORDER BY min(timestamp)""", profile)
    lines.append(md_rows(flows))
    exp = sql_rows(f"""SELECT element_at(split(x.dataset, '\\\\.'), -1) AS dataset, x.name AS expectation,
               sum(x.passed_records) AS passed, sum(x.failed_records) AS failed
        FROM (SELECT explode(from_json(details:flow_progress.data_quality.expectations::string,
              'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS x {base})
        GROUP BY 1, 2 ORDER BY 1, 2""", profile)
    if exp:
        lines.append("\n**Data-quality expectations** (warn / drop / fail rules declared in the pipeline)\n")
        lines.append(md_rows(exp))
    errs = sql_rows(f"SELECT timestamp, message FROM event_log('{pid}') WHERE origin.update_id = '{update_id}' AND level = 'ERROR' LIMIT 5", profile)
    if errs:
        lines.append("\n**Errors**\n\n" + md_rows(errs))
    return "\n".join(lines)


WAREHOUSE = os.environ.get("OSA_WAREHOUSE_ID", "e0a8cc3b322c1f1d")


def sql_rows(statement, profile):
    body = json.dumps({"statement": statement, "warehouse_id": WAREHOUSE, "wait_timeout": "50s"})
    r = cli("api", "post", "/api/2.0/sql/statements", "--json", body, profile=profile)
    while r.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        import time; time.sleep(2)
        r = cli("api", "get", f"/api/2.0/sql/statements/{r['statement_id']}", profile=profile)
    if r.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(json.dumps(r.get("status"))[:300])
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return [dict(zip(cols, row)) for row in r.get("result", {}).get("data_array", []) or []]


def md_rows(rows):
    if not rows:
        return "*(no rows)*"
    return md_table([{"name": c} for c in rows[0].keys()], [list(r.values()) for r in rows])


def _ms(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("out_dir")
    ap.add_argument("--profile", default="fevm-bar")
    a = ap.parse_args()
    run = cli("jobs", "get-run", a.run_id, profile=a.profile)
    os.makedirs(a.out_dir, exist_ok=True)
    summary = [f"# Job run evidence: {run.get('run_name')}\n",
               f"* Run ID: `{run['run_id']}` · Job ID: `{run.get('job_id')}`",
               f"* Started: {ts(run.get('start_time'))} · Ended: {ts(run.get('end_time'))}",
               f"* Result: **{run.get('state', {}).get('result_state', run.get('state', {}).get('life_cycle_state'))}**",
               f"* Run page: {run.get('run_page_url')}\n",
               "| task | type | result | duration (s) | evidence |", "|---|---|---|---|---|"]
    for t in sorted(run.get("tasks", []), key=lambda t: t.get("start_time") or 0):
        res = t.get("state", {}).get("result_state") or t.get("state", {}).get("life_cycle_state")
        kind = "pipeline" if "pipeline_task" in t else "notebook" if "notebook_task" in t else "other"
        dur = round((t.get("execution_duration") or t.get("run_duration") or 0) / 1000)
        fname = f"{t['task_key']}.md"
        if res in ("SUCCESS", "FAILED") or kind == "pipeline":
            try:
                body = notebook_md(t, a.profile) if kind == "notebook" else pipeline_md(t, a.profile)
                with open(os.path.join(a.out_dir, fname), "w") as fh:
                    fh.write(f"# Task `{t['task_key']}` — {res}\n\n*Run {t['run_id']} · started {ts(t.get('start_time'))} · "
                             f"{dur}s*\n\n{body}\n")
            except Exception as e:  # keep exporting other tasks
                fname = f"(export failed: {str(e)[:80]})"
        else:
            fname = ""
        summary.append(f"| {t['task_key']} | {kind} | {res} | {dur} | {f'[{fname}]({fname})' if fname.endswith('.md') else fname} |")
    with open(os.path.join(a.out_dir, "README.md"), "w") as fh:
        fh.write("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    sys.exit(main())
