"""Hybrid retrieval: BM25 + embeddings fused with reciprocal rank fusion.

RRF needs no score normalization: each retriever contributes 1/(60+rank) per
doc, which is robust when the two scoring scales are incomparable. If the
embedding backend is unavailable, the factory degrades to BM25 alone, so the
app never fails to boot because an embedding model is missing.
"""

import logging

from whichmodel.config import Settings
from whichmodel.retrieval.base import KBDoc, Retriever
from whichmodel.retrieval.bm25 import BM25Retriever
from whichmodel.retrieval.embedding import EmbeddingRetriever, OpenAICompatEmbedding

log = logging.getLogger(__name__)

RRF_K = 60


class HybridRetriever:
    """Retriever protocol over two ranked lists, fused by RRF."""

    def __init__(self, bm25: BM25Retriever, embedding: EmbeddingRetriever):
        self._bm25 = bm25
        self._embedding = embedding

    def search(self, query: str, k: int = 3, category: str | None = None) -> list[KBDoc]:
        pool = max(k * 2, 6)
        ranked_lists = [
            self._bm25.search(query, k=pool, category=category),
            self._embedding.search(query, k=pool, category=category),
        ]
        scores: dict[str, float] = {}
        docs: dict[str, KBDoc] = {}
        for ranking in ranked_lists:
            for rank, doc in enumerate(ranking):
                scores[doc.name] = scores.get(doc.name, 0.0) + 1.0 / (RRF_K + rank + 1)
                docs[doc.name] = doc
        best = sorted(scores.items(), key=lambda p: -p[1])[:k]
        return [docs[name] for name, _ in best]

    def get(self, name: str) -> KBDoc | None:
        return self._bm25.get(name)


def build_retriever(docs: list[KBDoc], settings: Settings) -> Retriever:
    """Factory honoring RETRIEVER_BACKEND with graceful degradation to BM25."""
    bm25 = BM25Retriever(docs)
    if settings.retriever_backend == "bm25":
        return bm25
    try:
        backend = OpenAICompatEmbedding(
            base_url=settings.openai_base_url, api_key=settings.openai_api_key,
            model=settings.embed_model_name)
        embedding = EmbeddingRetriever(docs, backend, settings.embed_cache_path)
    except Exception as err:
        log.warning("embedding retriever unavailable (%s); using BM25 only", err)
        return bm25
    if settings.retriever_backend == "embedding":
        return embedding
    return HybridRetriever(bm25, embedding)
