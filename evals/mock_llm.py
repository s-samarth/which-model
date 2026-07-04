"""Keyword-heuristic LLM used by EVAL_MOCK=1 runs.

Lets the harness plumbing (driver, assertions, report) be exercised without a
live model. It is intentionally dumb; live runs are the real gate.
"""

import json
import re

KEYWORDS = [
    (r"summar|tldr|digest", "summarization"),
    (r"image|photo|receipt|screenshot|ocr", "image_understanding"),
    (r"translat", "translation"),
    (r"\brag\b|knowledge base|my (docs|documents|pdfs)|legal pdf", "rag_doc_qa"),
    (r"cod|program|debug|software|copilot", "coding"),
    (r"chatbot|assistant|customer|shop", "chat_assistant"),
    (r"agent|automat|workflow|tool", "agentic_tool_use"),
    (r"novel|story|writ|copy|marketing", "creative_writing"),
    (r"news|research|current|search", "web_search_heavy"),
]


class HeuristicLLM:
    """Rule-based stand-in for the serving model."""

    def complete(self, system: str, messages: list[dict], *, max_tokens: int = 700,
                 json_mode: bool = False) -> str:
        text = " ".join(m["content"].lower() for m in messages if m["role"] == "user")
        if "extract structured requirements" in system:
            return json.dumps(self._extract(text))
        if "not given you enough" in system:
            return json.dumps({"acknowledgement": "Got it.", "questions": [
                "Would you rather run it on your own computer, or use a cloud service?"]})
        if "FACTS" in system:
            return self._answer(system)
        return "Summary: user wants help choosing a model."

    def stream(self, system: str, messages: list[dict], *, max_tokens: int = 1200):
        yield self.complete(system, messages, max_tokens=max_tokens)

    def _answer(self, system: str) -> str:
        entries = re.findall(r"^\d+\. (.+?) \[([\w./:~-]+)\]", system, re.M)
        if not entries:
            return "I could not compose an answer from the facts."
        name, mid = entries[0]
        lines = [f"Based on your needs, I recommend **{name}** ({mid}); it leads the "
                 "candidates on the task-relevant benchmark shown in my catalog."]
        if len(entries) > 1:
            lines.append(f"A solid alternative is {entries[1][0]} ({entries[1][1]}).")
        lines.append("Next step: try it on a few of your real prompts.")
        return "\n\n".join(lines)

    def _extract(self, text: str) -> dict:
        patch: dict = {}
        for pattern, cat in KEYWORDS:
            if re.search(pattern, text):
                patch["task_category"] = cat
                break
        if re.search(r"offline|on my (mac|laptop|pc|machine)|locally|private|"
                     r"local llm|host(ed)? (it )?myself|self-?host", text):
            patch["deployment"] = "local"
        elif re.search(r"cloud|api|online|free tier", text):
            patch["deployment"] = "api"
        if m := re.search(r"\$(\d+)", text):
            patch["budget_amount"], patch["budget_currency"] = float(m.group(1)), "usd"
        elif m := re.search(r"(\d+)\s*(rupees|inr|rs)\b", text):
            patch["budget_amount"], patch["budget_currency"] = float(m.group(1)), "inr"
        elif re.search(r"free|can'?t pay|no money|nothing|refuse to pay|single dollar|won'?t pay",
                       text):
            patch["budget_amount"], patch["budget_currency"] = 0.0, "usd"
        if re.search(r"hour a day|daily|moderate", text):
            patch["usage_level"] = "moderate"
        elif re.search(r"few (chats|questions)|occasionally|light", text):
            patch["usage_level"] = "light"
        if m := re.search(r"(\d+)\s*gb", text):
            patch["hardware"] = {"ram_gb": float(m.group(1))}
        if re.search(r"hindi|tamil|multilingual", text):
            patch["language_needs"] = "Hindi"
        return patch

