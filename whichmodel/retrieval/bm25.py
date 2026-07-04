"""BM25 retrieval over the knowledge base.

Tags and titles are weighted by repetition in the indexed text so that a query
like "coding" reliably surfaces the coding taxonomy doc.
"""

import re

from rank_bm25 import BM25Okapi

from whichmodel.retrieval.base import KBDoc

_TOKEN_RE = re.compile(r"[a-z0-9]+")
TAG_WEIGHT = 3  # tags/title repeated this many times in the index text


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Retriever:
    """Retriever protocol implementation backed by rank_bm25."""

    def __init__(self, docs: list[KBDoc]):
        self._docs = docs
        self._by_name = {d.name: d for d in docs}
        corpus = []
        for d in docs:
            boosted = " ".join([" ".join(d.tags), d.title, d.name.replace("/", " ")] * TAG_WEIGHT)
            corpus.append(_tokenize(boosted + " " + d.text))
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, k: int = 3, category: str | None = None) -> list[KBDoc]:
        """Top-k docs by BM25 score, optionally filtered to one category."""
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(scores, self._docs, strict=True), key=lambda p: -p[0])
        out = []
        for score, doc in ranked:
            if score <= 0:
                break
            if category is not None and doc.category != category:
                continue
            out.append(doc)
            if len(out) >= k:
                break
        return out

    def get(self, name: str) -> KBDoc | None:
        return self._by_name.get(name)
