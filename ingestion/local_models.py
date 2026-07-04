"""Curated local-model metadata (param counts, Ollama tags, quant availability).

The curated list is the source of truth for which models we recommend for local
use. Param counts are verified against the Hugging Face API when online; the
hardcoded fallbacks keep offline seed builds working. Entries whose id matches
an OpenRouter id enrich that row; others are inserted as local/<slug>.
"""

import logging
import sqlite3

from ingestion.http import get_with_backoff
from ingestion.schema import utcnow

log = logging.getLogger(__name__)

HF_API = "https://huggingface.co/api/models/"

# (catalog_id, name, hf_id, ollama_tag, param_b, active_param_b, context_length)
LOCAL_MODELS = [
    ("local/qwen3.5-2b", "Qwen3.5 2B", "Qwen/Qwen3.5-2B", "qwen3.5:2b", 2.0, None, 262144),
    ("local/qwen3.5-4b", "Qwen3.5 4B", "Qwen/Qwen3.5-4B", "qwen3.5:4b", 4.0, None, 262144),
    ("qwen/qwen3.5-9b", "Qwen3.5 9B", "Qwen/Qwen3.5-9B", "qwen3.5:9b", 9.0, None, None),
    ("qwen/qwen3.5-27b", "Qwen3.5 27B", "Qwen/Qwen3.5-27B", "qwen3.5:27b", 27.0, None, None),
    ("qwen/qwen3.5-35b-a3b", "Qwen3.5 35B A3B", "Qwen/Qwen3.5-35B-A3B",
     "qwen3.5:35b", 35.0, 3.0, None),
    ("qwen/qwen3.5-122b-a10b", "Qwen3.5 122B A10B", "Qwen/Qwen3.5-122B-A10B",
     "qwen3.5:122b", 122.0, 10.0, None),
    ("google/gemma-3-4b-it", "Gemma 3 4B", "google/gemma-3-4b-it", "gemma3:4b",
     4.3, None, None),
    ("google/gemma-3-12b-it", "Gemma 3 12B", "google/gemma-3-12b-it", "gemma3:12b",
     12.2, None, None),
    ("google/gemma-3-27b-it", "Gemma 3 27B", "google/gemma-3-27b-it", "gemma3:27b",
     27.4, None, None),
    ("meta-llama/llama-3.1-8b-instruct", "Llama 3.1 8B", "meta-llama/Llama-3.1-8B-Instruct",
     "llama3.1:8b", 8.0, None, None),
    ("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B", "meta-llama/Llama-3.3-70B-Instruct",
     "llama3.3:70b", 70.6, None, None),
    ("mistralai/mistral-small-3.2-24b-instruct", "Mistral Small 3.2 24B",
     "mistralai/Mistral-Small-3.2-24B-Instruct-2506", "mistral-small3.2:24b", 24.0, None, None),
    ("mistralai/ministral-8b-2512", "Ministral 8B (2512)", "mistralai/Ministral-8B-Instruct-2512",
     None, 8.0, None, None),
    ("qwen/qwen3-coder-30b-a3b-instruct", "Qwen3 Coder 30B A3B",
     "Qwen/Qwen3-Coder-30B-A3B-Instruct", "qwen3-coder:30b", 30.5, 3.3, None),
    ("qwen/qwen3-32b", "Qwen3 32B", "Qwen/Qwen3-32B", "qwen3:32b", 32.8, None, None),
    ("openai/gpt-oss-20b", "GPT-OSS 20B", "openai/gpt-oss-20b", "gpt-oss:20b",
     21.0, 3.6, None),
    ("openai/gpt-oss-120b", "GPT-OSS 120B", "openai/gpt-oss-120b", "gpt-oss:120b",
     117.0, 5.1, None),
    ("microsoft/phi-4", "Phi-4 14B", "microsoft/phi-4", "phi4:14b", 14.7, None, None),
    ("nvidia/nemotron-3-nano-30b-a3b", "Nemotron 3 Nano 30B A3B",
     "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", None, 30.0, 3.0, None),
]


def _hf_param_b(hf_id: str) -> float | None:
    """Look up total parameter count (billions) from the HF API; None on any failure."""
    try:
        data = get_with_backoff(HF_API + hf_id).json()
        total = (data.get("safetensors") or {}).get("total")
        return round(total / 1e9, 1) if total else None
    except Exception as err:
        log.warning("hf lookup failed for %s: %s", hf_id, err)
        return None


def upsert(conn: sqlite3.Connection, offline: bool = False) -> int:
    """Mark curated models as locally runnable, verifying param counts online."""
    now = utcnow()
    written = 0
    for mid, name, hf_id, tag, param_b, active_b, ctx in LOCAL_MODELS:
        if not offline:
            param_b = _hf_param_b(hf_id) or param_b
        exists = conn.execute("SELECT 1 FROM models WHERE id=?", (mid,)).fetchone()
        if exists:
            conn.execute(
                "UPDATE models SET available_local=1, open_weights=1, param_b=?, "
                "active_param_b=?, ollama_tag=?, hf_id=COALESCE(hf_id, ?), as_of=? WHERE id=?",
                (param_b, active_b, tag, hf_id, now, mid),
            )
        else:
            conn.execute(
                "INSERT INTO models (id, name, provider, context_length, input_modalities, "
                "available_api, available_local, open_weights, param_b, active_param_b, "
                "ollama_tag, hf_id, as_of) VALUES (?,?,?,?, 'text', 0, 1, 1, ?,?,?,?,?)",
                (mid, name, hf_id.split("/")[0].lower(), ctx, param_b, active_b, tag, hf_id, now),
            )
        written += 1
    conn.commit()
    log.info("local_models: upserted %d curated local models", written)
    return written
