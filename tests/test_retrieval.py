"""Retrieval tests: the right KB docs surface for realistic queries."""

from pathlib import Path

import pytest

from whichmodel.retrieval import BM25Retriever, load_kb

KB_DIR = Path(__file__).parent.parent / "kb"


@pytest.fixture(scope="module")
def retriever() -> BM25Retriever:
    docs = load_kb(KB_DIR)
    assert len(docs) >= 20, "expected the full KB corpus"
    return BM25Retriever(docs)


class TestLoader:
    def test_frontmatter_parsed(self, retriever):
        doc = retriever.get("taxonomy/coding")
        assert doc is not None
        assert doc.category == "taxonomy"
        assert "coding" in doc.tags
        assert doc.updated
        assert "Example user phrasings" in doc.text


class TestSearch:
    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("I want something that codes for me", "taxonomy/coding"),
            ("chatbot for my shop customers", "taxonomy/chat-assistant"),
            ("summarize legal PDFs and contracts", "taxonomy/summarization"),
            ("ask questions about my company documents", "taxonomy/rag-doc-qa"),
            ("automate workflows with tool calling agents", "taxonomy/agentic-tool-use"),
            ("translate product pages to Hindi", "taxonomy/translation"),
            ("what does the SWE-bench score mean", "benchmarks/swe-bench"),
            ("how much RAM do I need for local models vram", "guides/local-inference"),
            ("how many tokens fit in a context window", "guides/context-length"),
            ("monthly cost estimate for API usage", "guides/pricing-mental-models"),
            ("INR pricing and Indian languages", "regional/india-notes"),
            ("what GPU setup do I need to self-host", "guides/gpu-hosting"),
            ("user says I don't know and is not sure", "guides/reading-user-language"),
        ],
    )
    def test_query_surfaces_right_doc(self, retriever, query, expected):
        names = [d.name for d in retriever.search(query, k=3)]
        assert expected in names, f"{query!r} returned {names}"

    def test_category_filter(self, retriever):
        docs = retriever.search("coding", k=3, category="benchmark")
        assert docs, "benchmark-filtered search returned nothing"
        assert all(d.category == "benchmark" for d in docs)

    def test_get_unknown_returns_none(self, retriever):
        assert retriever.get("taxonomy/does-not-exist") is None

    def test_nonsense_query_returns_gracefully(self, retriever):
        docs = retriever.search("qwzyx blorptangle", k=3)
        assert docs == []


class FakeEmbedding:
    """Deterministic vectors: count occurrences of theme words."""

    THEMES = ["coding", "local", "cost", "image", "hindi", "summar"]

    def embed(self, texts):
        return [[float(t.lower().count(w)) + 0.01 for w in self.THEMES] for t in texts]


class TestEmbeddingRetriever:
    def _make(self, tmp_path):
        from whichmodel.retrieval.embedding import EmbeddingRetriever
        docs = load_kb(KB_DIR)
        return EmbeddingRetriever(docs, FakeEmbedding(), tmp_path / "cache.json"), docs

    def test_search_surfaces_theme_match(self, tmp_path):
        r, _ = self._make(tmp_path)
        docs = r.search("coding coding coding", k=3, category="taxonomy")
        assert docs, "no results"
        assert docs[0].name == "taxonomy/coding"
        assert all(d.category == "taxonomy" for d in docs)

    def test_cache_written_and_reused(self, tmp_path):
        import json as j
        r1, docs = self._make(tmp_path)
        cache = j.loads((tmp_path / "cache.json").read_text())
        assert len(cache) == len(docs)

        class ExplodingBackend:
            def embed(self, texts):
                raise AssertionError("must not re-embed cached docs")

        from whichmodel.retrieval.embedding import EmbeddingRetriever
        EmbeddingRetriever(docs, ExplodingBackend(), tmp_path / "cache.json")

    def test_query_failure_returns_empty(self, tmp_path):
        r, docs = self._make(tmp_path)
        r._backend = type("B", (), {"embed": lambda self, t: 1 / 0})()
        assert r.search("anything") == []


class TestHybridRetriever:
    def test_rrf_fuses_both_rankings(self, tmp_path):
        from whichmodel.retrieval.embedding import EmbeddingRetriever
        from whichmodel.retrieval.hybrid import HybridRetriever
        docs = load_kb(KB_DIR)
        hybrid = HybridRetriever(
            BM25Retriever(docs),
            EmbeddingRetriever(docs, FakeEmbedding(), tmp_path / "c.json"))
        names = [d.name for d in hybrid.search("how much RAM for local coding models", k=3)]
        assert "guides/local-inference" in names
        assert hybrid.get("taxonomy/coding") is not None

    def test_factory_degrades_to_bm25_without_endpoint(self, monkeypatch, tmp_path):
        from whichmodel.config import Settings
        from whichmodel.retrieval.hybrid import build_retriever
        docs = load_kb(KB_DIR)
        settings = Settings(openai_base_url="http://localhost:1", # nothing listens
                            embed_cache_path=tmp_path / "c.json",
                            retriever_backend="hybrid")
        r = build_retriever(docs, settings)
        assert isinstance(r, BM25Retriever)
