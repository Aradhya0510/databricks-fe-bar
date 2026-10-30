#!/usr/bin/env python3
"""Record Q&A evidence for the Knowledge Assistant and the Supervisor Agent (OSA Assistant).

  evidence/agents/knowledge_assistant_eval.md  - 10 policy questions with expected facts, pass/fail per fact
  evidence/agents/supervisor_qa.md            - mixed data + policy questions, answer text and tool/agent steps

Usage: scripts/agent_qa_evidence.py KA_ENDPOINT SUPERVISOR_ENDPOINT [--profile fevm-bar]
"""
import json, os, re, subprocess, sys, time

KA, SUP = sys.argv[1], sys.argv[2]
PROFILE = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "fevm-bar"
ROOT = os.path.join(os.path.dirname(__file__), "..", "evidence", "agents")
DOCS_EVAL = "/Volumes/serverless_stable_4hkk7k_catalog/osa_retail/docs/eval_questions.json"


def cli(*args, raw=False):
    r = subprocess.run(["databricks", *args, "-p", PROFILE] + ([] if raw else ["-o", "json"]), capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:500])
    return r.stdout if raw else (json.loads(r.stdout) if r.stdout.strip() else {})


def invoke(endpoint, question):
    t0 = time.time()
    body = json.dumps({"input": [{"role": "user", "content": question}]})
    for attempt in range(3):
        try:
            r = cli("api", "post", f"/serving-endpoints/{endpoint}/invocations", "--json", body)
            break
        except RuntimeError as e:
            if attempt == 2:
                return {"answer": f"ERROR: {e}", "steps": [], "secs": round(time.time() - t0, 1)}
            time.sleep(10)
    text, steps = [], []
    for item in r.get("output", []):
        t = item.get("type")
        if t == "message":
            text += [c.get("text", "") for c in item.get("content", []) if c.get("text")]
        elif t == "function_call":
            steps.append(f"{item.get('name')}({item.get('arguments', '')[:160]})")
    return {"answer": "\n".join(text).strip(), "steps": steps, "secs": round(time.time() - t0, 1)}


def norm(s):
    return re.sub(r"[^a-z0-9%$.]+", " ", s.lower())


def fact_hits(answer, fact):
    keys = [k for k in re.findall(r"\$?\d[\d,.]*%?|[A-Z]{3,}_\d|[a-z]{4,}", fact.replace(",", "")) if k.lower() not in
            {"within", "more", "than", "above", "plus", "with", "days", "long"}]
    a = norm(answer.replace(",", ""))
    found = [k for k in keys if norm(k).strip() in a]
    return len(found) / max(len(keys), 1), keys


os.makedirs(ROOT, exist_ok=True)
evalq = json.loads(cli("fs", "cat", f"dbfs:{DOCS_EVAL}", raw=True))
out = [f"# Knowledge Assistant evaluation — `{KA}`\n",
       f"*{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}. Questions and expected facts from `docs/eval_questions.json`; "
       "a question passes when ≥ 80% of the expected fact's key terms/numbers appear in the answer.*\n"]
passed = 0
for q in evalq:
    r = invoke(KA, q["question"])
    cov, keys = fact_hits(r["answer"], q["expected_fact"])
    ok = cov >= 0.8
    passed += ok
    out += [f"## {'✅' if ok else '❌'} {q['question']}\n", f"*Expected fact:* {q['expected_fact']} · *coverage* {cov:.0%} · {r['secs']}s\n",
            "> " + r["answer"].replace("\n", "\n> ") + "\n"]
out.insert(2, f"**Score: {passed}/{len(evalq)} questions answered with the expected fact.**\n")
open(os.path.join(ROOT, "knowledge_assistant_eval.md"), "w").write("\n".join(out))
print(f"KA: {passed}/{len(evalq)}")

QUESTIONS = [
    "What was on-shelf availability by region over the last 7 days compared with the prior 7 days?",
    "Which 5 store-items have the highest revenue at risk tonight, and what should each store do?",
    "Which suppliers caused the most stockouts in the last 4 weeks, and what does our escalation policy require us to do about them?",
    "Store TX_2 has a household cleaning item out of stock and the supplier PO is overdue. Can they place an emergency DSD order, by when, and what will it cost?",
    "What share of stockouts since November 2015 came from phantom inventory, and what is the procedure when we suspect it?",
    "How is lost revenue calculated, and what is our FY2016 target for the lost-sales rate?",
]
out = [f"# Supervisor Agent (OSA Assistant) Q&A — `{SUP}`\n",
       f"*{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}. Each answer is produced by the Agent Bricks Supervisor "
       "routing between the Genie Agent (governed SQL), the Knowledge Assistant (internal documents) and UC function tools.*\n"]
for q in QUESTIONS:
    r = invoke(SUP, q)
    out += [f"## Q: {q}\n", f"*{r['secs']}s · steps: {' → '.join(r['steps']) if r['steps'] else '(routing not exposed in response)'}*\n",
            r["answer"] + "\n", "---\n"]
    print(f"SUP: {q[:60]}… {r['secs']}s steps={len(r['steps'])}")
open(os.path.join(ROOT, "supervisor_qa.md"), "w").write("\n".join(out))
