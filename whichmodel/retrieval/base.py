"""Retrieval interfaces.

The graph depends only on this protocol. Swapping BM25 for an embedding
backend later means adding a new implementation, not touching the agent.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class KBDoc:
    """One knowledge-base document with its frontmatter metadata."""

    name: str  # unique slug, e.g. "taxonomy/coding"
    category: str  # taxonomy | benchmark | guide | regional
    tags: tuple[str, ...] = ()
    updated: str = ""
    text: str = ""

    @property
    def title(self) -> str:
        for line in self.text.splitlines():
            if line.startswith("#"):
                return line.lstrip("# ").strip()
        return self.name


@runtime_checkable
class Retriever(Protocol):
    """Query interface the agent graph uses to pull KB context."""

    def search(self, query: str, k: int = 3, category: str | None = None) -> list[KBDoc]:
        """Top-k docs for a free-text query, optionally restricted to a category."""
        ...

    def get(self, name: str) -> KBDoc | None:
        """Deterministic lookup by doc slug (e.g. the taxonomy doc for a known task)."""
        ...


@dataclass
class StaticRetriever:
    """In-memory retriever over a fixed doc list; useful in tests."""

    docs: list[KBDoc] = field(default_factory=list)

    def search(self, query: str, k: int = 3, category: str | None = None) -> list[KBDoc]:
        pool = [d for d in self.docs if category is None or d.category == category]
        return pool[:k]

    def get(self, name: str) -> KBDoc | None:
        return next((d for d in self.docs if d.name == name), None)
