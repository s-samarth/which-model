"""SQLite schema and connection helpers for the model catalog.

Ingestion writes this DB; the app only reads it through whichmodel.tools.catalog.
Every row carries an `as_of` timestamp so the UI can surface data age.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS models (
    id TEXT PRIMARY KEY,              -- canonical id: OpenRouter slug, or local/<slug>
    name TEXT NOT NULL,
    provider TEXT,                    -- organization: openai, anthropic, meta-llama, ...
    description TEXT,
    context_length INTEGER,
    input_modalities TEXT,            -- comma separated: text,image
    prompt_usd_per_m REAL,            -- API price per 1M input tokens (NULL if local-only)
    completion_usd_per_m REAL,
    is_free INTEGER NOT NULL DEFAULT 0,
    available_api INTEGER NOT NULL DEFAULT 0,
    available_local INTEGER NOT NULL DEFAULT 0,
    open_weights INTEGER NOT NULL DEFAULT 0,
    param_b REAL,                     -- total parameters in billions (local models)
    active_param_b REAL,              -- active parameters for MoE (speed proxy)
    ollama_tag TEXT,                  -- e.g. qwen3.5:4b (local models)
    hf_id TEXT,
    as_of TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmarks (
    model_id TEXT NOT NULL REFERENCES models(id),
    benchmark TEXT NOT NULL,          -- e.g. livebench_global, livebench_coding
    score REAL NOT NULL,
    source TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    PRIMARY KEY (model_id, benchmark)
);

CREATE TABLE IF NOT EXISTS aliases (
    alias TEXT PRIMARY KEY,           -- normalized foreign name, e.g. livebench model id
    model_id TEXT NOT NULL REFERENCES models(id)
);

CREATE TABLE IF NOT EXISTS quant_factors (
    quant TEXT PRIMARY KEY,           -- q4_K_M, q8_0, fp16, ...
    bytes_per_param REAL NOT NULL,
    quality_note TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Memory-fit heuristics used by the catalog tools: file size ~= param_b * bytes_per_param,
# runtime needs ~1.2x for KV cache and overhead. Stored in the DB per the spec.
QUANT_FACTORS = [
    ("q4_K_M", 0.60, "4-bit, the default sweet spot: small quality loss, half the memory of 8-bit"),
    ("q5_K_M", 0.72, "5-bit, slightly better quality than q4 for ~20% more memory"),
    ("q8_0", 1.07, "8-bit, near-lossless, needs roughly the param count in GB"),
    ("fp16", 2.0, "full half precision, reference quality, rarely needed for chat use"),
]


def utcnow() -> str:
    """UTC timestamp string used for as_of columns."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (and initialize if needed) the catalog database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)
    for quant, bpp, note in QUANT_FACTORS:
        conn.execute(
            "INSERT INTO quant_factors(quant, bytes_per_param, quality_note) VALUES(?,?,?) "
            "ON CONFLICT(quant) DO UPDATE SET bytes_per_param=excluded.bytes_per_param, "
            "quality_note=excluded.quality_note",
            (quant, bpp, note),
        )
    conn.commit()
    return conn


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Upsert a meta key (e.g. per-source refresh timestamps)."""
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
