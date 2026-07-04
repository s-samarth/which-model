"""Ingest models, pricing, context windows and modality flags from OpenRouter.

Public API, no key required: https://openrouter.ai/api/v1/models
"""

import json
import logging
import sqlite3
from pathlib import Path

from ingestion.http import SourceSchemaError, get_with_backoff
from ingestion.schema import utcnow

log = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/models"
SNAPSHOT = Path(__file__).parent / "snapshots" / "openrouter.json"

# Router/meta entries that are not real models a user would pick.
SKIP_PREFIXES = ("openrouter/", "~", "switchpoint/", "morph/", "relace/")


def fetch(offline: bool = False) -> list[dict]:
    """Fetch the OpenRouter model list (or load the bundled snapshot)."""
    if offline:
        return json.loads(SNAPSHOT.read_text())["data"]
    resp = get_with_backoff(OPENROUTER_URL)
    payload = resp.json()
    if "data" not in payload or not isinstance(payload["data"], list):
        raise SourceSchemaError("OpenRouter response missing 'data' list")
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(payload, indent=1))
    return payload["data"]


def _price_per_m(pricing: dict, key: str) -> float | None:
    """OpenRouter prices are USD per token as strings; convert to USD per 1M tokens."""
    raw = pricing.get(key)
    if raw is None:
        return None
    try:
        return float(raw) * 1_000_000
    except (TypeError, ValueError):
        return None


def upsert(conn: sqlite3.Connection, models: list[dict]) -> int:
    """Idempotent upsert of OpenRouter models into the catalog. Returns rows written."""
    now = utcnow()
    written = 0
    for m in models:
        mid = m.get("id", "")
        if not mid or mid.startswith(SKIP_PREFIXES) or mid.endswith(":free"):
            continue  # ':free' variants are duplicates; is_free is derived from price
        arch = m.get("architecture") or {}
        pricing = m.get("pricing") or {}
        prompt_usd = _price_per_m(pricing, "prompt")
        completion_usd = _price_per_m(pricing, "completion")
        is_free = int(prompt_usd == 0 and completion_usd == 0)
        conn.execute(
            """
            INSERT INTO models (id, name, provider, description, context_length,
                input_modalities, prompt_usd_per_m, completion_usd_per_m, is_free,
                available_api, open_weights, hf_id, as_of)
            VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, provider=excluded.provider,
                description=excluded.description, context_length=excluded.context_length,
                input_modalities=excluded.input_modalities,
                prompt_usd_per_m=excluded.prompt_usd_per_m,
                completion_usd_per_m=excluded.completion_usd_per_m,
                is_free=excluded.is_free, available_api=1,
                open_weights=excluded.open_weights, hf_id=excluded.hf_id,
                as_of=excluded.as_of
            """,
            (
                mid,
                m.get("name") or mid,
                mid.split("/")[0],
                (m.get("description") or "")[:300],
                m.get("context_length"),
                ",".join(arch.get("input_modalities") or ["text"]),
                prompt_usd,
                completion_usd,
                is_free,
                int(bool(m.get("hugging_face_id"))),
                m.get("hugging_face_id"),
                now,
            ),
        )
        written += 1
    conn.commit()
    log.info("openrouter: upserted %d models", written)
    return written
