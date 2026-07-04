/* Which Model? chat frontend: transport, composer, activity display.
   The recommendation card renderer lives in rec-card.js.
   Streaming: POST /chat/stream returns Server-Sent Events; we read the body
   with a ReadableStream and show "activity" events (what the agent is doing)
   live, then render the "final" event. Falls back to plain POST /chat. */

const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const send = document.getElementById("send");
const recommendBtn = document.getElementById("recommend-now");
const dataAge = document.getElementById("data-age");

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};

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

/* The live activity panel: one line per agent step, newest highlighted. */
function activityPanel() {
  const box = el("div", "activity");
  const list = el("ul");
  box.appendChild(list);
  chat.appendChild(box);
  return {
    add(text) {
      list.querySelectorAll("li").forEach((li) => li.classList.remove("now"));
      const li = el("li", "now", text);
      list.appendChild(li);
      box.scrollIntoView({ block: "end" });
    },
    remove() { box.remove(); },
    settle() { box.classList.add("settled"); },
  };
}

function handleFinal(body) {
  for (const n of body.notices || []) addMessage("notice", n);
  if (body.reply) addMessage("bot", body.reply);
  if (body.recommendation) renderRecommendation(body.recommendation);
  if (body.data_age) dataAge.textContent = `data refreshed ${body.data_age}`;
  recommendBtn.hidden = body.phase === "done";
}

async function streamChat(text, activity) {
  const resp = await fetch("/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text }),
  });
  if (!resp.ok || !resp.body) throw new Error(`stream failed: ${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (!chunk.startsWith("data: ")) continue;
      const event = JSON.parse(chunk.slice(6));
      if (event.type === "activity") activity.add(event.text);
      else if (event.type === "final") return event;
    }
  }
  throw new Error("stream ended without a final event");
}

async function sendMessage(text) {
  addMessage("user", text);
  send.disabled = true;
  recommendBtn.disabled = true;
  const activity = activityPanel();
  try {
    let body;
    try {
      body = await streamChat(text, activity);
    } catch {
      const resp = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      body = await resp.json();
    }
    activity.settle();
    handleFinal(body);
  } catch (err) {
    activity.remove();
    addMessage("bot", "Something went wrong reaching the server. Please try again.");
  } finally {
    send.disabled = false;
    recommendBtn.disabled = false;
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

/* "Recommend now": stop the questions, answer with what we have. The phrase
   matches the backend's impatience detection, so no special API is needed. */
recommendBtn.addEventListener("click", () => {
  sendMessage("just give me your best recommendation with what you know");
});

document.getElementById("reset").addEventListener("click", async () => {
  await fetch("/reset", { method: "POST" });
  chat.replaceChildren();
  recommendBtn.hidden = true;
  addMessage("bot", "Fresh start. What are you trying to do?");
});

fetch("/health").then((r) => r.json()).then((h) => {
  if (h.data_age) dataAge.textContent = `data refreshed ${h.data_age}`;
}).catch(() => {});

addMessage("bot", "Hi! Describe what you want an AI model for, in your own words. Budget, privacy, offline, anything that matters to you.");
recommendBtn.hidden = true;
