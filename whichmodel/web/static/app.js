/* Which Model? chat frontend.
   Vanilla JS patterns used here:
   - fetch() + async/await for the JSON API (no framework needed)
   - <template> cloning for the recommendation card (HTML lives in index.html,
     JS only fills data in, keeping markup and logic separate)
   - textContent everywhere user/LLM text lands, so nothing is injected as HTML */

const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const send = document.getElementById("send");
const dataAge = document.getElementById("data-age");

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

/* Assistant text may contain ```code blocks``` (hardware probe commands).
   Split on the fences and render code separately with a copy button. */
function renderBotText(container, text) {
  text.split(/```(?:\w*\n)?/).forEach((part, i) => {
    if (!part.trim()) return;
    if (i % 2 === 0) {
      container.appendChild(el("span", null, part.trim()));
    } else {
      const pre = el("pre");
      pre.appendChild(el("code", null, part.trim()));
      const btn = el("button", "copy-btn", "copy");
      btn.onclick = () => {
        navigator.clipboard.writeText(part.trim());
        btn.textContent = "copied";
        setTimeout(() => (btn.textContent = "copy"), 1200);
      };
      pre.appendChild(btn);
      container.appendChild(pre);
    }
  });
}

function addMessage(role, text) {
  const msg = el("div", `msg ${role}`);
  if (role === "bot") renderBotText(msg, text);
  else msg.textContent = text;
  chat.appendChild(msg);
  msg.scrollIntoView({ behavior: "smooth", block: "end" });
  return msg;
}

const money = (usd, inr) =>
  usd === null || usd === undefined
    ? "runs on your machine"
    : usd === 0
      ? "free"
      : `$${usd < 10 ? usd.toFixed(2) : Math.round(usd)}/mo`;

const ROLE_LABELS = { top_pick: "Top pick", runner_up: "Runner-up", budget_pick: "Budget pick" };

function renderRecommendation(rec) {
  const card = document.getElementById("tpl-recommendation").content.cloneNode(true);
  const picksBox = card.querySelector(".rec-picks");

  for (const pick of rec.picks) {
    const div = el("div", `pick ${pick.role}`);
    div.appendChild(el("span", "role", ROLE_LABELS[pick.role] || pick.role));
    div.appendChild(el("h3", null, pick.name));
    const cost = el("p", "cost", money(pick.monthly_cost_usd));
    if (pick.monthly_cost_inr) {
      const inr = el("small", null, ` (~₹${pick.monthly_cost_inr.toLocaleString("en-IN")})`);
      cost.appendChild(inr);
    }
    div.appendChild(cost);
    div.appendChild(el("p", "why", pick.why));
    if (pick.ollama_tag) {
      const code = el("code", "pull", `ollama pull ${pick.ollama_tag}`);
      code.title = "click to copy";
      code.onclick = () => navigator.clipboard.writeText(`ollama pull ${pick.ollama_tag}`);
      div.appendChild(code);
    }
    picksBox.appendChild(div);
  }

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
    tr.appendChild(el("td", null, row.local ? (row.free ? "local · free" : "local") : "cloud"));
    tbody.appendChild(tr);
  }

  const notes = card.querySelector(".rec-notes");
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

function showTyping() {
  const t = el("div", "typing");
  t.append(el("i"), el("i"), el("i"));
  chat.appendChild(t);
  t.scrollIntoView({ block: "end" });
  return t;
}

async function sendMessage(text) {
  addMessage("user", text);
  send.disabled = true;
  const typing = showTyping();
  try {
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const body = await resp.json();
    typing.remove();
    for (const n of body.notices || []) addMessage("notice", n);
    if (body.reply) addMessage("bot", body.reply);
    if (body.recommendation) renderRecommendation(body.recommendation);
    if (body.data_age) dataAge.textContent = `data refreshed ${body.data_age}`;
  } catch (err) {
    typing.remove();
    addMessage("bot", "Something went wrong reaching the server. Please try again.");
  } finally {
    send.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  input.style.height = "auto";
  sendMessage(text);
});

/* Enter sends, Shift+Enter makes a newline; the textarea grows as you type. */
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
});

document.getElementById("reset").addEventListener("click", async () => {
  await fetch("/reset", { method: "POST" });
  chat.replaceChildren();
  addMessage("bot", "Fresh start. What are you trying to do?");
});

/* Load the data-age footer on first paint. */
fetch("/health").then((r) => r.json()).then((h) => {
  if (h.data_age) dataAge.textContent = `data refreshed ${h.data_age}`;
}).catch(() => {});

addMessage("bot", "Hi! Describe what you want an AI model for, in your own words. Budget, privacy, offline, anything that matters to you.");
