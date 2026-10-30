#!/usr/bin/env python3
"""Ask the Genie Agent its benchmark questions and compare against the reference SQL results.

Writes evidence/genie/benchmark.md (question, Genie's generated SQL, Genie result, reference result, match).
Usage: scripts/genie_benchmark.py SPACE_ID [--profile fevm-bar]
"""
import json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from genie_space import benchmarks, examples  # noqa: E402

SPACE = sys.argv[1]
PROFILE = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "fevm-bar"
WAREHOUSE = "e0a8cc3b322c1f1d"
OUT = os.path.join(os.path.dirname(__file__), "..", "evidence", "genie", "benchmark.md")
EXTRA = [("Which South region stores have the lowest availability last week, and how much revenue did they lose?", None),
         ("What share of stockouts since November 2015 were caused by phantom inventory vs supplier delays?", None)]


def cli(*args):
    r = subprocess.run(["databricks", *args, "-p", PROFILE, "-o", "json"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:400])
    return json.loads(r.stdout) if r.stdout.strip() else {}


def run_sql(q):
    r = cli("api", "post", "/api/2.0/sql/statements", "--json", json.dumps({"statement": q, "warehouse_id": WAREHOUSE, "wait_timeout": "50s"}))
    if r["status"]["state"] != "SUCCEEDED":
        return None
    return [[c["name"] for c in r["manifest"]["schema"]["columns"]]] + (r.get("result", {}).get("data_array") or [])


def ask(q):
    t0 = time.time()
    m = cli("genie", "start-conversation", SPACE, q)
    conv, msg = m["conversation_id"], m["message_id"]
    while True:
        g = cli("genie", "get-message", SPACE, conv, msg)
        if g.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(3)
    out = {"status": g.get("status"), "sql": None, "text": "", "result": None, "secs": round(time.time() - t0, 1)}
    for a in g.get("attachments", []) or []:
        if a.get("text"):
            out["text"] += a["text"].get("content", "")
        if a.get("query"):
            out["sql"] = a["query"].get("query")
            out["text"] += a["query"].get("description", "") or ""
            res = cli("genie", "get-message-attachment-query-result", SPACE, conv, msg, a["attachment_id"])
            sr = res.get("statement_response", {})
            cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
            out["result"] = [cols] + (sr.get("result", {}).get("data_array") or [])
    return out


def md(rows, limit=12):
    if not rows:
        return "*(no result)*"
    head, body = rows[0], rows[1:limit + 1]
    s = "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] +
                  ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in body])
    return s + (f"\n\n*… {len(rows) - 1 - limit} more rows*" if len(rows) - 1 > limit else "")


def values(rows):
    def norm(v):
        try:
            return round(float(v), 1)
        except (TypeError, ValueError):
            return v
    return sorted(tuple(norm(v) for v in r) for r in (rows or [[]])[1:])


lines, score = [], []
for q, ref in benchmarks + EXTRA:
    g = ask(q)
    expected = run_sql(ref) if ref else None
    match = None if expected is None else (values(g["result"]) == values(expected))
    score.append(match)
    lines += [f"## {q}\n", f"*Genie status: {g['status']} · {g['secs']}s · "
              f"{'match: ✅' if match else 'match: ❌' if match is False else 'open question (no reference SQL)'}*\n"]
    if g["text"]:
        lines.append("**Genie answer:** " + g["text"].strip().replace("\n", " ") + "\n")
    lines.append(f"**Genie SQL:**\n\n```sql\n{g['sql'] or '(none)'}\n```\n\n**Genie result:**\n\n{md(g['result'])}\n")
    if ref:
        lines.append(f"<details><summary>Reference SQL and result</summary>\n\n```sql\n{ref}\n```\n\n{md(expected)}\n\n</details>\n")
graded = [s for s in score if s is not None]
header = [f"# Genie Agent benchmark — space `{SPACE}`\n",
          f"*Run {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} via the Genie Conversation API.*\n",
          f"**Result-set match vs reference SQL: {sum(graded)}/{len(graded)}** "
          f"(numeric values compared at 0.1 precision, row order ignored). "
          f"{len(score) - len(graded)} additional open-ended questions shown for answer quality.\n"]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(header + lines))
print("\n".join(header))
