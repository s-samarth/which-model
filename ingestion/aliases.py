"""Model-name matching between benchmark sources and catalog ids.

Benchmark sources use their own naming (e.g. LiveBench's
`claude-opus-4-8-high-effort`). We normalize away variant suffixes, then try
mechanical candidates against catalog slugs, then an explicit alias seed for
irregular names. Unmatched names are logged, never guessed.
"""

import logging
import re
import sqlite3

log = logging.getLogger(__name__)

# Variant suffixes that describe a run configuration, not a different model.
_VARIANT_RE = re.compile(
    r"(-(base|nothinking|highthinking|thinking-auto|thinking(-\d+k)?|reasoning|non-reasoning|"
    r"(low|medium|high|xhigh|minimal)(-effort)?))+$"
)
_DATE_RE = re.compile(r"-(\d{8}|\d{4}-\d{2}-\d{2}|\d{2}-\d{4}|\d{2}-\d{2}|\d{4})$")

# Explicit seed for names the mechanical rules cannot bridge.
# Keys must be in normalized form (see normalize()). Only map when the target
# is genuinely the same base model; version mismatches stay unmatched.
ALIAS_SEED = {
    "claude-4-1-opus": "anthropic/claude-opus-4.1",
    "claude-4-sonnet": "anthropic/claude-sonnet-4",
    "devstral": "mistralai/devstral-2512",
    "gemini-2.5-flash-lite-preview": "google/gemini-2.5-flash-lite-preview-09-2025",
    "grok-4.20-beta": "x-ai/grok-4.20",
    "kimi-k2-instruct": "moonshotai/kimi-k2",
    "qwen3-235b-a22b-instruct": "qwen/qwen3-235b-a22b-2507",
    "qwen3-next-80b-a3b": "qwen/qwen3-next-80b-a3b-instruct",
}


def normalize(name: str) -> str:
    """Strip run-variant suffixes and trailing date stamps from a source model name."""
    n = name.strip().lower()
    prev = None
    while prev != n:
        prev = n
        n = _VARIANT_RE.sub("", n)
        n = _DATE_RE.sub("", n)
    return n


def _candidates(base: str) -> list[str]:
    """Mechanical slug candidates for a normalized name (dash-to-dot on versions)."""
    cands = [base]
    dotted = re.sub(r"(\d)-(\d)", r"\1.\2", base)
    if dotted != base:
        cands.append(dotted)
    return cands


def build_slug_index(conn: sqlite3.Connection) -> dict[str, str]:
    """Map catalog slug tails (after the org prefix) to canonical model ids."""
    index: dict[str, str] = {}
    for row in conn.execute("SELECT id FROM models"):
        mid = row["id"]
        tail = mid.split("/", 1)[-1].lower()
        index.setdefault(tail, mid)
    return index


def resolve(conn: sqlite3.Connection, source_name: str, slug_index: dict[str, str]) -> str | None:
    """Resolve a benchmark-source model name to a catalog id, or None (logged)."""
    # Exact raw-name match first, so date-stamped catalog ids are not degraded
    # by normalization (e.g. qwen3-235b-a22b-thinking-2507).
    raw = source_name.strip().lower()
    if raw in slug_index:
        return slug_index[raw]
    base = normalize(source_name)
    row = conn.execute("SELECT model_id FROM aliases WHERE alias=?", (base,)).fetchone()
    if row:
        return row["model_id"]
    if base in ALIAS_SEED:
        target = ALIAS_SEED[base]
        if conn.execute("SELECT 1 FROM models WHERE id=?", (target,)).fetchone():
            return target
        log.warning("alias seed target %s not in catalog (for %s)", target, source_name)
        return None
    for cand in _candidates(base):
        if cand in slug_index:
            return slug_index[cand]
    return None


def remember(conn: sqlite3.Connection, source_name: str, model_id: str) -> None:
    """Persist a resolved alias so future refreshes match instantly."""
    conn.execute(
        "INSERT INTO aliases(alias, model_id) VALUES(?,?) "
        "ON CONFLICT(alias) DO UPDATE SET model_id=excluded.model_id",
        (normalize(source_name), model_id),
    )
