"""Embedding retrieval over the knowledge base.

Embeddings come from the same OpenAI-compatible endpoint as the chat model
(Ollama serves nomic-embed-text locally). Document vectors are cached on disk
keyed by content hash, so the corpus is embedded once, not on every boot.
"""

import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Protocol

from whichmodel.retrieval.base import KBDoc

log = logging.getLogger(__name__)


class EmbeddingBackend(Protocol):
    """Anything that turns texts into vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAICompatEmbedding:
    """Embeddings via any OpenAI-compatible /v1/embeddings endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float = 30.0):
        from openai import OpenAI

        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_s,
                              max_retries=1)
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _doc_key(doc: KBDoc) -> str:
    return hashlib.sha256((doc.name + doc.text).encode()).hexdigest()[:16]


class EmbeddingRetriever:
    """Retriever protocol implementation over cached document vectors.

    Raises at construction if the backend is unreachable, so callers (the
    hybrid factory) can fall back to BM25 cleanly.
    """

    def __init__(self, docs: list[KBDoc], backend: EmbeddingBackend, cache_path: Path):
        self._docs = docs
        self._by_name = {d.name: d for d in docs}
        self._backend = backend
        self._vectors = self._load_or_embed(docs, cache_path)

    def _load_or_embed(self, docs: list[KBDoc], cache_path: Path) -> dict[str, list[float]]:
        cache: dict[str, dict] = {}
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text())
            except json.JSONDecodeError:
                cache = {}
        vectors: dict[str, list[float]] = {}
        missing: list[KBDoc] = []
        for d in docs:
            entry = cache.get(d.name)
            if entry and entry.get("key") == _doc_key(d):
                vectors[d.name] = entry["vector"]
            else:
                missing.append(d)
        if missing:
            log.info("embedding %d KB docs (cache had %d)", len(missing), len(vectors))
            texts = [f"{' '.join(d.tags)}\n{d.title}\n{d.text[:2000]}" for d in missing]
            for doc, vec in zip(missing, self._backend.embed(texts), strict=True):
                vectors[doc.name] = vec
                cache[doc.name] = {"key": _doc_key(doc), "vector": vec}
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache))
        return vectors

    def search(self, query: str, k: int = 3, category: str | None = None) -> list[KBDoc]:
        try:
            qvec = self._backend.embed([query])[0]
        except Exception as err:
            log.warning("query embedding failed (%s); returning nothing", err)
            return []
        scored = sorted(
            ((_cosine(qvec, self._vectors[d.name]), d) for d in self._docs
             if category is None or d.category == category),
            key=lambda p: -p[0])
        return [d for score, d in scored[:k] if score > 0]

    def get(self, name: str) -> KBDoc | None:
        return self._by_name.get(name)
