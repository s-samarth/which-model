"""Deterministic catalog queries over the SQLite model database.

The task category selects which benchmark columns rank the candidates; budget,
deployment, hardware, context and modality act as filters. If a model is not
in the DB, it does not exist for this app.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from whichmodel.schemas import ContextNeed, Deployment, ModelRow, Requirements, TaskCategory
from whichmodel.tools import costs

# Primary + secondary benchmark keys per task; primary weighs double when ranking.
CATEGORY_BENCHMARKS: dict[TaskCategory, tuple[str, str]] = {
    TaskCategory.coding: ("livebench_agentic_coding", "livebench_coding"),
    TaskCategory.chat_assistant: ("livebench_global", "livebench_if"),
    TaskCategory.rag_doc_qa: ("livebench_language", "livebench_data_analysis"),
    TaskCategory.summarization: ("livebench_if", "livebench_language"),
    TaskCategory.agentic_tool_use: ("livebench_agentic_coding", "livebench_if"),
    TaskCategory.image_understanding: ("livebench_global", "livebench_if"),
    TaskCategory.creative_writing: ("livebench_language", "livebench_if"),
    TaskCategory.web_search_heavy: ("livebench_global", "livebench_data_analysis"),
    TaskCategory.translation: ("livebench_language", "livebench_global"),
    TaskCategory.other: ("livebench_global", "livebench_if"),
}

MIN_CONTEXT = {ContextNeed.short: 0, ContextNeed.medium: 32_000, ContextNeed.long: 131_000}
Q4_BYTES_PER_PARAM = 0.60
MEMORY_OVERHEAD = 1.2


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def data_age(conn: sqlite3.Connection) -> str:
    """Human-readable age of the last data refresh, e.g. '6h ago'."""
    row = conn.execute("SELECT value FROM meta WHERE key='last_refresh'").fetchone()
    if not row:
        return "unknown"
    then = datetime.strptime(row["value"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    hours = (datetime.now(UTC) - then).total_seconds() / 3600
    if hours < 1:
        return "under an hour ago"
    if hours < 48:
        return f"{hours:.0f}h ago"
    return f"{hours / 24:.0f} days ago"


def est_memory_gb(param_b: float) -> float:
    """Runtime memory footprint of a q4-quantized model, in GB."""
    return round(param_b * Q4_BYTES_PER_PARAM * MEMORY_OVERHEAD, 1)


def _load_row(conn: sqlite3.Connection, row: sqlite3.Row) -> ModelRow:
    scores = {
        r["benchmark"]: r["score"]
        for r in conn.execute("SELECT benchmark, score FROM benchmarks WHERE model_id=?",
                              (row["id"],))
    }
    return ModelRow(
        id=row["id"], name=row["name"], provider=row["provider"] or "",
        context_length=row["context_length"],
        input_modalities=row["input_modalities"] or "text",
        prompt_usd_per_m=row["prompt_usd_per_m"],
        completion_usd_per_m=row["completion_usd_per_m"],
        is_free=bool(row["is_free"]), available_api=bool(row["available_api"]),
        available_local=bool(row["available_local"]), open_weights=bool(row["open_weights"]),
        param_b=row["param_b"], active_param_b=row["active_param_b"],
        ollama_tag=row["ollama_tag"], scores=scores,
        est_memory_gb=est_memory_gb(row["param_b"]) if row["param_b"] else None,
    )


def lookup_model(conn: sqlite3.Connection, name: str) -> ModelRow | None:
    """Find one model by id, name, or alias. Returns None if truly absent."""
    needle = name.strip().lower()
    row = conn.execute(
        "SELECT * FROM models WHERE lower(id)=? OR lower(name)=? "
        "OR lower(id) LIKE '%/' || ? OR lower(ollama_tag)=?",
        (needle, needle, needle, needle),
    ).fetchone()
    if row is None:
        alias = conn.execute(
            "SELECT model_id FROM aliases WHERE alias=?", (needle,)
        ).fetchone()
        if alias:
            row = conn.execute("SELECT * FROM models WHERE id=?", (alias["model_id"],)).fetchone()
    return _load_row(conn, row) if row else None


def _rank_score(m: ModelRow, primary: str, secondary: str) -> float:
    """Weighted mean of available benchmark scores; 0 if unmeasured."""
    parts = []
    if primary in m.scores:
        parts += [m.scores[primary]] * 2
    if secondary in m.scores:
        parts.append(m.scores[secondary])
    return round(sum(parts) / len(parts), 2) if parts else 0.0


def find_candidates(
    conn: sqlite3.Connection, req: Requirements, limit: int = 8
) -> list[ModelRow]:
    """Filter and rank catalog models against the requirements. Deterministic."""
    task = req.task_category or TaskCategory.other
    primary, secondary = CATEGORY_BENCHMARKS[task]
    deployment = req.deployment or Deployment.either
    mem = req.hardware.usable_memory_gb if req.hardware else None

    rows = [_load_row(conn, r) for r in conn.execute("SELECT * FROM models")]
    out: list[ModelRow] = []
    for m in rows:
        if deployment == Deployment.local and not m.available_local:
            continue
        if deployment == Deployment.api and not m.available_api:
            continue
        if req.context_need and (m.context_length or 0) < MIN_CONTEXT[req.context_need]:
            if not (deployment == Deployment.local and m.context_length is None):
                continue
        if task == TaskCategory.image_understanding and "image" not in m.input_modalities:
            continue
        if deployment == Deployment.local and mem and m.est_memory_gb:
            if m.est_memory_gb > mem:
                continue
        m.rank_score = _rank_score(m, primary, secondary)
        if m.available_api and deployment != Deployment.local:
            m.est_monthly_usd = costs.estimate_monthly_usd(m, req.usage_level)
            if (
                req.budget_monthly_usd is not None
                and m.est_monthly_usd is not None
                and m.est_monthly_usd > req.budget_monthly_usd
            ):
                continue
        out.append(m)

    # Measured models first by score; unmeasured local models by size as a weak proxy.
    out.sort(key=lambda m: (m.rank_score, m.param_b or 0), reverse=True)
    top = out[:limit]
    # Guarantee a budget option: cheapest paid or free/local candidate.
    cheap = [m for m in out if (m.est_monthly_usd or 0) == 0 or m.available_local]
    if cheap:
        cheapest = min(cheap, key=lambda m: (m.est_monthly_usd or 0, -(m.rank_score)))
        if cheapest.id not in {m.id for m in top}:
            top.append(cheapest)
    return top
