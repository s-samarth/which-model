/* Minimal safe Markdown renderer for streamed answers.
   Everything lands via textContent (no innerHTML with model output), so the
   LLM cannot inject markup. Supports: paragraphs, ### headings, **bold**,
   `inline code`, ``` code blocks, - lists, and | tables |. */

function mdInline(target, text) {
  // Order matters: code spans first so ** inside code stays literal.
  const parts = text.split(/(`[^`]*`)/);
  for (const part of parts) {
    if (part.startsWith("`") && part.endsWith("`") && part.length > 1) {
      target.appendChild(el("code", "md-code", part.slice(1, -1)));
    } else {
      const boldParts = part.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/);
      for (const b of boldParts) {
        if (b && b.startsWith("**") && b.endsWith("**") && b.length > 4) {
          target.appendChild(el("strong", null, b.slice(2, -2)));
        } else if (b && b.startsWith("*") && b.endsWith("*") && b.length > 2) {
          target.appendChild(el("em", null, b.slice(1, -1)));
        } else if (b) {
          target.appendChild(document.createTextNode(b));
        }
      }
    }
  }
}

function mdTable(lines) {
  const table = el("table", "md-table");
  lines.forEach((line, i) => {
    const cells = line.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    if (cells.every((c) => /^:?-{2,}:?$/.test(c))) return; // separator row
    const tr = el("tr");
    for (const cell of cells) {
      const td = el(i === 0 ? "th" : "td");
      mdInline(td, cell);
      tr.appendChild(td);
    }
    table.appendChild(tr);
  });
  return table;
}

function renderMarkdown(text) {
  const frag = document.createDocumentFragment();
  const blocks = text.split(/```(?:\w*\n)?/);
  blocks.forEach((block, bi) => {
    if (bi % 2 === 1) {
      // fenced code block, with the copy button chat users already know
      const pre = el("pre");
      pre.appendChild(el("code", null, block.trim()));
      const btn = el("button", "copy-btn", "copy");
      btn.onclick = () => {
        navigator.clipboard.writeText(block.trim());
        btn.textContent = "copied";
        setTimeout(() => (btn.textContent = "copy"), 1200);
      };
      pre.appendChild(btn);
      frag.appendChild(pre);
      return;
    }
    const lines = block.split("\n");
    let i = 0;
    while (i < lines.length) {
      const line = lines[i].trim();
      if (!line) { i += 1; continue; }
      if (line.startsWith("|")) {
        const tbl = [];
        while (i < lines.length && lines[i].trim().startsWith("|")) tbl.push(lines[i++].trim());
        frag.appendChild(mdTable(tbl));
      } else if (/^#{1,4} /.test(line)) {
        const h = el("h4", "md-h");
        mdInline(h, line.replace(/^#+ /, ""));
        frag.appendChild(h);
        i += 1;
      } else if (/^[-*] /.test(line)) {
        const ul = el("ul", "md-list");
        while (i < lines.length && /^[-*] /.test(lines[i].trim())) {
          const li = el("li");
          mdInline(li, lines[i].trim().slice(2));
          ul.appendChild(li);
          i += 1;
        }
        frag.appendChild(ul);
      } else {
        const para = [line];
        i += 1;
        while (i < lines.length && lines[i].trim() &&
               !/^([-*] |#{1,4} |\|)/.test(lines[i].trim())) {
          para.push(lines[i].trim());
          i += 1;
        }
        const p = el("p", "md-p");
        mdInline(p, para.join(" "));
        frag.appendChild(p);
      }
    }
  });
  return frag;
}
