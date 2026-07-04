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
