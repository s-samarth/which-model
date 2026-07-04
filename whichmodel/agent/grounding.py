"""Post-generation grounding validation.

Scans generated text for names of catalog models that are NOT in the current
candidate list. Used to reject recommendation text that drifts off the
grounded candidates before it ever reaches the user.
"""

import re
import sqlite3
from functools import lru_cache


def _variants(model_id: str, name: str) -> set[str]:
    """Recognizable surface forms of one model's name."""
    out = {name.lower(), model_id.lower(), model_id.split("/")[-1].lower()}
    if ":" in name:  # "OpenAI: GPT-5.4" -> "gpt-5.4"
        out.add(name.split(":", 1)[1].strip().lower())
    return {v for v in out if len(v) >= 5}


@lru_cache(maxsize=4)
def _name_table(db_key: str) -> list[tuple[str, str, frozenset[str]]]:
    conn = sqlite3.connect(db_key)
    rows = conn.execute("SELECT id, name FROM models").fetchall()
    conn.close()
    return [(mid, nm, frozenset(_variants(mid, nm))) for mid, nm in rows]


def _spans(variant: str, text: str) -> list[tuple[int, int]]:
    pat = re.compile(rf"(?<![\w.]){re.escape(variant)}(?![\w.])")
    return [m.span() for m in pat.finditer(text)]


def foreign_model_mentions(text: str, db_path: str, allowed_ids: set[str]) -> list[str]:
    """Catalog models named in text that are not in allowed_ids.

    A mention is only a violation if its text span is not covered by a longer
    allowed-model mention (so "gpt-5.4" inside "gpt-5.4-mini" does not fire).
    """
    lowered = text.lower()
    allowed_spans: list[tuple[int, int]] = []
    foreign: dict[str, list[tuple[int, int]]] = {}
    for mid, _name, variants in _name_table(db_path):
        for v in variants:
            spans = _spans(v, lowered)
            if not spans:
                continue
            if mid in allowed_ids:
                allowed_spans.extend(spans)
            else:
                foreign.setdefault(mid, []).extend(spans)
    violations = []
    for mid, spans in foreign.items():
        uncovered = [s for s in spans
                     if not any(a[0] <= s[0] and s[1] <= a[1] for a in allowed_spans)]
        if uncovered:
            violations.append(mid)
    return sorted(violations)
