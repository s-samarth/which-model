/* Recommendation card rendering, split from app.js.
   Uses the shared `el` helper defined in app.js (loaded first). */

const money = (usd) =>
  usd === null || usd === undefined
    ? "runs on your machine"
    : usd === 0
      ? "free"
      : `$${usd < 10 ? usd.toFixed(2) : Math.round(usd)}/mo`;

const ROLE_LABELS = { top_pick: "Top pick", runner_up: "Runner-up", budget_pick: "Budget pick" };

function renderPick(pick) {
  const div = el("div", `pick ${pick.role}`);
  div.appendChild(el("span", "role", ROLE_LABELS[pick.role] || pick.role));
  div.appendChild(el("h3", null, pick.name));

  const mode = el("span", "mode-tag", pick.mode === "local" ? "run locally" : "via cloud API");
  div.appendChild(mode);

  const cost = el("p", "cost", money(pick.monthly_cost_usd));
  if (pick.monthly_cost_inr) {
    cost.appendChild(el("small", null, ` (~₹${pick.monthly_cost_inr.toLocaleString("en-IN")})`));
  }
  div.appendChild(cost);
  div.appendChild(el("p", "why", pick.why));
  if (pick.local_setup) div.appendChild(renderLocalSetup(pick.local_setup));
  if (pick.get_started) div.appendChild(el("p", "get-started", pick.get_started));
  if (pick.ollama_tag && pick.mode === "local") {
    const code = el("code", "pull", `ollama pull ${pick.ollama_tag}`);
    code.title = "click to copy";
    code.onclick = () => navigator.clipboard.writeText(`ollama pull ${pick.ollama_tag}`);
    div.appendChild(code);
  }
  return div;
}

/* Local setup block: quantization options with memory, speed, serving stack.
   Quantization = compressing the model to fewer bits; q4 is the usual choice. */
function renderLocalSetup(setup) {
  const box = el("div", "local-setup");
  const quants = (setup.quants || [])
    .filter((q) => ["q4_K_M", "q8_0"].includes(q.quant))
    .map((q) => {
      const fit = q.fits === null ? "" : q.fits ? " ✓ fits" : " ✗ too big";
      return `${q.quant.replace("_K_M", "")} ≈ ${q.memory_gb}GB${fit}`;
    })
    .join(" · ");
  if (quants) {
    const q = el("p", null, `Quantized sizes: ${quants}`);
    q.title = "Quantization compresses the model to fewer bits per weight. " +
      "q4 is the standard choice: half the memory, small quality loss. " +
      "q8 is near-lossless but twice the size.";
    box.appendChild(q);
  }
  if (setup.est_speed) box.appendChild(el("p", null, `Expected speed: ~${setup.est_speed} on your hardware (readable is ~10)`));
  if (setup.moe_note) box.appendChild(el("p", null, setup.moe_note));
  if (setup.serving) box.appendChild(el("p", null, setup.serving));
  return box;
}

function runsLabel(row) {
  if (row.local && row.api) return "cloud · local";
  if (row.local) return row.free ? "local · free" : "local";
  return "cloud";
}

function renderRecommendation(rec) {
  const card = document.getElementById("tpl-recommendation").content.cloneNode(true);
  const picksBox = card.querySelector(".rec-picks");
  rec.picks.forEach((p) => picksBox.appendChild(renderPick(p)));

  const tbody = card.querySelector("tbody");
  const maxScore = Math.max(...rec.comparison.map((r) => r.score || 0), 1);
  for (const row of rec.comparison) {
    const tr = el("tr", row.picked ? "picked" : "");
    tr.appendChild(el("td", null, row.name));
    const scoreTd = el("td");
    if (row.score !== null && row.score !== undefined) {
      const bar = el("span", "bar");
      bar.style.width = `${Math.round((row.score / maxScore) * 46)}px`;
      scoreTd.appendChild(bar);
      scoreTd.appendChild(el("span", null, row.score.toFixed(0)));
      scoreTd.title = row.benchmark;
    } else if (row.param_b) {
      scoreTd.textContent = `${row.param_b}B params`;
      scoreTd.title = "Not benchmarked; parameter count shown as a rough size proxy";
    } else scoreTd.textContent = "–";
    tr.appendChild(scoreTd);
    const costTd = el("td");
    if (row.est_monthly_usd === null && row.local && row.memory_gb) {
      costTd.textContent = `~${row.memory_gb}GB @ q4`;
      costTd.title = "Runs on your machine; memory needed at 4-bit quantization";
    } else costTd.textContent = money(row.est_monthly_usd);
    tr.appendChild(costTd);
    tr.appendChild(el("td", null, row.context_k ? `${row.context_k}k` : "–"));
    tr.appendChild(el("td", null, runsLabel(row)));
    tbody.appendChild(tr);
  }

  const notes = card.querySelector(".rec-notes");
  const legends = el("div", "legend");
  if (rec.score_legend) legends.appendChild(el("p", null, rec.score_legend));
  if (rec.cost_basis) legends.appendChild(el("p", null, rec.cost_basis));
  if (legends.childNodes.length) notes.appendChild(legends);

  for (const [title, items] of [["Assumptions", rec.assumptions], ["Caveats", rec.caveats]]) {
    if (!items || !items.length) continue;
    const box = el("div");
    box.appendChild(el("h4", null, title));
    const ul = el("ul");
    items.forEach((t) => ul.appendChild(el("li", null, t)));
    box.appendChild(ul);
    notes.appendChild(box);
  }
  if (rec.data_age) notes.appendChild(el("div", null, `Catalog data refreshed ${rec.data_age}.`));

  chat.appendChild(card);
  chat.lastElementChild.scrollIntoView({ behavior: "smooth", block: "end" });
}
