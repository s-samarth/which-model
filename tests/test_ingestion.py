"""Unit tests for ingestion: alias matching, LiveBench aggregation, pricing."""

import sqlite3

import pytest

from ingestion import aliases, livebench, openrouter
from ingestion.schema import connect


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    yield c
    c.close()


def _add_model(conn: sqlite3.Connection, mid: str):
    conn.execute(
        "INSERT INTO models(id, name, provider, as_of) VALUES(?,?,?, '2026-01-01T00:00:00Z')",
        (mid, mid, mid.split("/")[0]),
    )


class TestNormalize:
    def test_strips_effort_and_thinking_suffixes(self):
        assert aliases.normalize("claude-opus-4-8-high-effort") == "claude-opus-4-8"
        assert aliases.normalize("claude-haiku-4-5-20251001-thinking-64k") == "claude-haiku-4-5"
        assert aliases.normalize("gpt-5.1-2025-11-13-nothinking") == "gpt-5.1"
        assert aliases.normalize("claude-opus-4-6-thinking-auto-high-effort") == "claude-opus-4-6"

    def test_keeps_meaningful_names(self):
        assert aliases.normalize("gpt-oss-120b") == "gpt-oss-120b"
        assert aliases.normalize("kimi-k2.7-code") == "kimi-k2.7-code"


class TestResolve:
    def test_direct_and_dotted_match(self, conn):
        _add_model(conn, "anthropic/claude-opus-4.8")
        idx = aliases.build_slug_index(conn)
        assert aliases.resolve(conn, "claude-opus-4-8-xhigh-effort", idx) == \
            "anthropic/claude-opus-4.8"

    def test_raw_exact_match_beats_normalization(self, conn):
        _add_model(conn, "qwen/qwen3-235b-a22b-thinking-2507")
        _add_model(conn, "qwen/qwen3-235b-a22b")
        idx = aliases.build_slug_index(conn)
        assert aliases.resolve(conn, "qwen3-235b-a22b-thinking-2507", idx) == \
            "qwen/qwen3-235b-a22b-thinking-2507"

    def test_unmatched_returns_none(self, conn):
        idx = aliases.build_slug_index(conn)
        assert aliases.resolve(conn, "elephant-alpha", idx) is None

    def test_seed_requires_target_in_catalog(self, conn):
        idx = aliases.build_slug_index(conn)
        # Seed target not in catalog: must return None, never invent a model.
        assert aliases.resolve(conn, "claude-4-1-opus-20250805-base", idx) is None


class TestLiveBenchAggregation:
    CATS = {"Coding": ["code_generation", "code_completion"], "Reasoning": ["zebra_puzzle"]}

    def test_category_means_and_global(self):
        row = {"model": "m", "code_generation": "80", "code_completion": "60",
               "zebra_puzzle": "40"}
        scores = livebench._category_scores(row, self.CATS)
        assert scores["livebench_coding"] == 70.0
        assert scores["livebench_reasoning"] == 40.0
        assert scores["livebench_global"] == 55.0

    def test_missing_tasks_skipped(self):
        scores = livebench._category_scores({"model": "m", "zebra_puzzle": "50"}, self.CATS)
        assert "livebench_coding" not in scores
        assert scores["livebench_global"] == 50.0

    def test_variant_collapse_keeps_best(self, conn):
        _add_model(conn, "anthropic/claude-opus-4.8")
        table = [
            {"model": "claude-opus-4-8-low-effort", "code_generation": "50",
             "code_completion": "50", "zebra_puzzle": "10"},
            {"model": "claude-opus-4-8-high-effort", "code_generation": "90",
             "code_completion": "90", "zebra_puzzle": "80"},
        ]
        livebench.upsert(conn, "2026-01-08", table, self.CATS)
        score = conn.execute(
            "SELECT score FROM benchmarks WHERE model_id='anthropic/claude-opus-4.8' "
            "AND benchmark='livebench_coding'"
        ).fetchone()["score"]
        assert score == 90.0


class TestOpenRouterUpsert:
    def _model(self, mid="openai/gpt-5.4", prompt="0.00000125", completion="0.00001"):
        return {
            "id": mid, "name": mid, "description": "d", "context_length": 400000,
            "architecture": {"input_modalities": ["text", "image"]},
            "pricing": {"prompt": prompt, "completion": completion},
        }

    def test_price_converted_to_per_million(self, conn):
        openrouter.upsert(conn, [self._model()])
        row = conn.execute("SELECT * FROM models WHERE id='openai/gpt-5.4'").fetchone()
        assert row["prompt_usd_per_m"] == 1.25
        assert row["completion_usd_per_m"] == 10.0
        assert row["is_free"] == 0
        assert row["input_modalities"] == "text,image"

    def test_free_and_router_entries(self, conn):
        openrouter.upsert(conn, [
            self._model("meta-llama/llama-3.3-70b-instruct", "0", "0"),
            self._model("openrouter/auto"),
            self._model("qwen/qwen3-coder:free"),
        ])
        rows = {r["id"] for r in conn.execute("SELECT id FROM models")}
        assert rows == {"meta-llama/llama-3.3-70b-instruct"}
        free = conn.execute("SELECT is_free FROM models").fetchone()["is_free"]
        assert free == 1

    def test_upsert_is_idempotent(self, conn):
        openrouter.upsert(conn, [self._model()])
        openrouter.upsert(conn, [self._model(prompt="0.000002")])
        rows = conn.execute("SELECT count(*) c, max(prompt_usd_per_m) p FROM models").fetchone()
        assert rows["c"] == 1
        assert rows["p"] == 2.0
