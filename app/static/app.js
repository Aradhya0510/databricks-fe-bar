const $ = (s) => document.querySelector(s);
const fmt$ = (v) => v == null ? "–" : "$" + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.text()).slice(0, 300));
  return r.json();
}
const region = () => $("#region").value;
let chart, queueRows = [], current, genieConv = null;

document.querySelectorAll(".tab").forEach((b) => b.onclick = () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
  document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
  b.classList.add("active"); $("#" + b.dataset.tab).classList.add("active");
  if (b.dataset.tab === "briefings") loadBriefings();
  if (b.dataset.tab === "governance") loadGov();
});
$("#region").onchange = () => { loadKpis(); loadQueue(); };
$("#store").onchange = loadQueue; $("#tier").onchange = loadQueue;

async function loadContext() {
  try {
    const c = await api("/api/context");
    $("#ctx").innerHTML = `Business date <b>${c.score_date}</b> · model v${c.model_version}<br>${c.open_recommendations} open recommendations · ${c.critical} critical`;
  } catch (e) { $("#ctx").textContent = "context unavailable"; }
  ["CA_1","CA_2","CA_3","CA_4","TX_1","TX_2","TX_3","WI_1","WI_2","WI_3"].forEach((s) => $("#store").insertAdjacentHTML("beforeend", `<option>${s}</option>`));
}

async function loadKpis() {
  const k = await api("/api/kpis?region=" + region());
  const last = k.summary.find((x) => x.period === "last_7d") || {}, prior = k.summary.find((x) => x.period === "prior_7d") || {};
  const atRisk = k.at_risk.reduce((a, x) => a + Number(x.revenue_at_risk_3d || 0), 0);
  const crit = (k.at_risk.find((x) => x.risk_tier === "CRITICAL") || {}).items || 0;
  const d = (a, b, inv) => { const v = Number(a) - Number(b); const good = inv ? v < 0 : v > 0;
    return `<span class="${good ? "up" : "down"}">${v > 0 ? "▲" : "▼"} ${Math.abs(v).toFixed(2)}</span> vs prior 7d`; };
  $("#tiles").innerHTML = `
    <div class="tile"><div class="k">On-shelf availability (7d)</div><div class="v">${last.osa_pct ?? "–"}%</div><div class="d">${d(last.osa_pct, prior.osa_pct)} pts · target 96%</div></div>
    <div class="tile"><div class="k">Lost revenue to stockouts (7d)</div><div class="v">${fmt$(last.lost_revenue)}</div><div class="d">${d(last.lost_revenue / 1000, prior.lost_revenue / 1000, true)}k</div></div>
    <div class="tile"><div class="k">Lost-sales rate (7d)</div><div class="v">${last.lost_sales_rate_pct ?? "–"}%</div><div class="d">target &lt; 1.5%</div></div>
    <div class="tile"><div class="k">Revenue at risk, next 3 days</div><div class="v">${fmt$(atRisk)}</div><div class="d">across open alerts</div></div>
    <div class="tile"><div class="k">Critical alerts tonight</div><div class="v">${crit}</div><div class="d">act within 4h (SOP-REP-001)</div></div>`;
  const regions = [...new Set(k.trend.map((r) => r.region))];
  const dates = [...new Set(k.trend.map((r) => r.date))];
  const colors = { West: "#2856c6", South: "#ff3621", Midwest: "#1a7f4b" };
  const ds = regions.map((rg) => ({ label: rg, borderColor: colors[rg], backgroundColor: colors[rg], tension: .25, pointRadius: 0,
    data: dates.map((dt) => { const x = k.trend.find((r) => r.date === dt && r.region === rg); return x ? Number(x.osa_pct) : null; }) }));
  ds.push({ label: "Target 96%", data: dates.map(() => 96), borderDash: [4, 4], borderColor: "#999", pointRadius: 0 });
  if (chart) chart.destroy();
  chart = new Chart($("#trend"), { type: "line", data: { labels: dates, datasets: ds },
    options: { plugins: { legend: { position: "bottom" } }, scales: { y: { title: { display: true, text: "OSA %" } } } } });
}

async function loadQueue() {
  const store = $("#store").value, tier = $("#tier").value;
  queueRows = await api(`/api/queue?store=${store}&tier=${tier}&limit=150`);
  const rows = queueRows.filter((r) => region() === "ALL" || r.region === region());
  $("#queue tbody").innerHTML = rows.map((r, i) => `<tr>
    <td>${r.priority_rank}</td><td>${r.store_id}</td><td><b>${esc(r.item_name)}</b><br><small>${r.item_id} · ${esc(r.supplier_name || "")}</small></td>
    <td><span class="tier ${r.risk_tier}">${r.risk_tier}</span></td><td>${r.risk_score}</td><td>${r.days_of_cover ?? "–"}</td>
    <td>${r.recommended_action.replaceAll("_", " ")}</td><td>${r.recommended_qty}</td><td>${fmt$(r.revenue_at_risk_3d)}</td>
    <td class="why">${esc(r.rationale)}</td>
    <td>${r.decision ? `<span class="done">${r.decision}${r.decision_qty != null ? " · " + r.decision_qty : ""}</span><br><small>${esc(r.decided_by || "")}</small>`
        : `<button class="act" data-i="${queueRows.indexOf(r)}">Decide</button>`}</td></tr>`).join("");
  document.querySelectorAll("button.act").forEach((b) => b.onclick = () => openDecision(queueRows[b.dataset.i]));
}

function openDecision(r) {
  current = r;
  $("#dtitle").textContent = `${r.store_id} · ${r.item_name}`;
  $("#drat").textContent = r.rationale;
  $("#dqty").value = r.recommended_qty; $("#dmsg").textContent = ""; $("#dreason").value = ""; $("#dnote").value = "";
  $("#daction").value = r.recommended_action === "CYCLE_COUNT" ? "CYCLE_COUNT_DONE" : "APPROVE";
  $("#dlg").showModal();
}
$("#dsave").onclick = async (ev) => {
  ev.preventDefault();
  try {
    const res = await api("/api/decision", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rec_id: current.rec_id, action: $("#daction").value, final_qty: Number($("#dqty").value),
        reason_code: $("#dreason").value || null, note: $("#dnote").value || null }) });
    $("#dmsg").textContent = res.requires_regional_manager_approval ? "Saved — override > 50%: Regional Manager approval required." : "Saved.";
    setTimeout(() => { $("#dlg").close(); loadQueue(); }, 700);
  } catch (e) { $("#dmsg").textContent = "Error: " + e.message; }
};

let t;
$("#itemq").oninput = () => { clearTimeout(t); t = setTimeout(async () => {
  const q = $("#itemq").value.trim(); if (q.length < 2) { $("#itemres").innerHTML = ""; return; }
  const r = await api(`/api/items?q=${encodeURIComponent(q)}&store=${$("#store").value}`);
  $("#lat").textContent = `${r.rows.length} rows · ${r.latency_ms} ms from Lakebase`;
  $("#itemres").innerHTML = `<table><tr><th>Store</th><th>Item</th><th>Tier</th><th>Risk</th><th>On hand</th><th>Cover</th><th>Top driver</th></tr>` +
    r.rows.map((x) => `<tr><td>${x.store_id}</td><td>${esc(x.item_name)}<br><small>${x.item_id}</small></td><td><span class="tier ${x.risk_tier}">${x.risk_tier}</span></td>
    <td>${x.risk_score}</td><td>${x.on_hand_units}</td><td>${x.days_of_cover}</td><td>${x.driver_1}</td></tr>`).join("") + "</table>";
}, 250); };

async function loadBriefings() {
  const b = await api("/api/briefings");
  $("#brieflist").innerHTML = b.map((x, i) => `<div class="b" data-i="${i}"><b>${esc(x.title)}</b><small>${x.audience} · ${x.model}</small></div>`).join("") || "No briefings yet.";
  document.querySelectorAll(".list .b").forEach((el) => el.onclick = () => {
    document.querySelectorAll(".list .b").forEach((y) => y.classList.remove("sel")); el.classList.add("sel");
    const x = b[el.dataset.i]; $("#briefbody").innerHTML = marked.parse(x.markdown) + `<p class="note">Generated ${x.generated_at} by the OSA intelligence agent (${x.model}); every figure comes from governed UC tools.</p>`;
  });
  const first = document.querySelector(".list .b"); if (first) first.click();
}

const SUGGEST = ["Which 5 store-items have the highest revenue at risk tonight and why?",
  "What was on-shelf availability by region last week vs the week before?",
  "Which suppliers caused the most stockouts in the last 4 weeks, and what does our escalation policy require?",
  "Can store TX_2 use an emergency DSD order for a household item, and what does it cost?",
  "How is lost revenue calculated?"];
$("#suggest").innerHTML = SUGGEST.map((s) => `<button>${s}</button>`).join("");
document.querySelectorAll("#suggest button").forEach((b) => b.onclick = () => { $("#q").value = b.textContent; $("#askform").requestSubmit(); });
$("#askform").onsubmit = async (ev) => {
  ev.preventDefault();
  const q = $("#q").value.trim(); if (!q) return;
  const mode = document.querySelector("input[name=mode]:checked").value;
  $("#chat").insertAdjacentHTML("beforeend", `<div class="msg u">${esc(q)}</div>`);
  const id = "m" + Date.now(); $("#chat").insertAdjacentHTML("beforeend", `<div class="msg a" id="${id}">Thinking…</div>`);
  $("#q").value = "";
  try {
    const r = await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, mode, conversation_id: mode === "genie" ? genieConv : null }) });
    let html = marked.parse(r.answer || "(no text answer)");
    if (r.sql) html += `<details open><summary>Generated SQL (Genie)</summary><pre>${esc(r.sql)}</pre></details>`;
    if (r.columns && r.columns.length) html += `<table><tr>${r.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr>` +
      r.rows.slice(0, 20).map((row) => `<tr>${row.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("") + "</table>";
    if (r.steps && r.steps.length) html += `<div class="steps">Agents/tools used: ${r.steps.map((s) => esc(s.tool)).join(" → ")}</div>`;
    html += `<div class="steps">${mode === "genie" ? "Genie Agent" : "Supervisor Agent"} · ${r.latency_s}s</div>`;
    if (mode === "genie") genieConv = r.conversation_id;
    $("#" + id).innerHTML = html;
  } catch (e) { $("#" + id).textContent = "Error: " + e.message; }
  $("#chat").scrollTop = 1e9;
};

async function loadGov() {
  const g = await api("/api/governance");
  const tbl = (rows) => rows.length ? `<table><tr>${Object.keys(rows[0]).map((k) => `<th>${k}</th>`).join("")}</tr>${rows.map((r) => `<tr>${Object.values(r).map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</table>` : "<i>no rows visible</i>";
  $("#gov").innerHTML = `<h3>What this app's identity can see</h3><p>Identity: <code>${esc(g.identity[0].identity)}</code></p>
    <h3>dim_supplier (column masks on commercial terms & e-mail)</h3>${tbl(g.dim_supplier_sample)}
    <h3>gold_osa_kpi_daily rows by region (row filter)</h3>${tbl(g.kpi_rows_by_region)}
    <p class="note">Policies are Unity Catalog functions attached to the tables; they are enforced for SQL, Genie, agents and this app alike.</p>`;
}

loadContext(); loadKpis(); loadQueue();
