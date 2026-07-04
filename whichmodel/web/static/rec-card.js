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
  if (pick.get_started) div.appendChild(el("p", "get-started", pick.get_started));
  if (pick.ollama_tag && pick.mode === "local") {
    const code = el("code", "pull", `ollama pull ${pick.ollama_tag}`);
    code.title = "click to copy";
    code.onclick = () => navigator.clipboard.writeText(`ollama pull ${pick.ollama_tag}`);
    div.appendChild(code);
  }
  return div;
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
    } else scoreTd.textContent = "–";
    tr.appendChild(scoreTd);
    tr.appendChild(el("td", null, money(row.est_monthly_usd)));
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
