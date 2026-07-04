"""Web search tool, used when the catalog cannot answer.

Triggered only for model-ish names that are not in the DB (e.g. a user asking
about "SuperGPT-9000") or explicit search requests. Results feed the LLM as
clearly-labeled web context; picks still come exclusively from the catalog.
"""

import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider(Protocol):
    def search(self, query: str, k: int = 3) -> list[SearchResult]: ...


class DdgsSearch:
    """DuckDuckGo search via the ddgs package. No API key. Failures return []."""

    def search(self, query: str, k: int = 3) -> list[SearchResult]:
        try:
            from ddgs import DDGS

            rows = list(DDGS().text(query, max_results=k))
            return [SearchResult(title=r.get("title", ""), url=r.get("href", ""),
                                 snippet=r.get("body", "")[:400]) for r in rows]
        except Exception as err:
            log.warning("web search failed for %r: %s", query, err)
            return []


def make_provider(kind: str) -> SearchProvider | None:
    return DdgsSearch() if kind == "ddgs" else None


# Model-ish tokens: letters + digits joined by dashes/dots ("gpt-9000",
# "claude-sonnet-5"). The whole hyphenated chain is captured so catalog
# lookups see the full name, not a suffix.
_MODELISH_RE = re.compile(
    r"\b((?:[A-Za-z][A-Za-z0-9]*[-.])*[A-Za-z][A-Za-z]+[-.]?[0-9][0-9A-Za-z.-]*)\b")
_NOISE = re.compile(r"^(gb|tb|k|b|m|x|v)?\d|^\d|^(rtx|gtx|m1|m2|m3|m4|a100|h100)", re.I)
_EXPLICIT_SEARCH_RE = re.compile(r"search (the )?(web|internet)|look (it |this )?up|"
                                 r"latest news|what'?s new", re.I)


def unknown_model_mentions(text: str, conn: sqlite3.Connection) -> list[str]:
    """Model-looking names in the text that resolve to nothing in the catalog."""
    from whichmodel.tools.catalog import lookup_model

    seen: set[str] = set()
    out: list[str] = []
    for m in _MODELISH_RE.finditer(text):
        token = m.group(1).strip().rstrip(".")
        low = token.lower()
        if low in seen or len(token) < 5 or _NOISE.match(token):
            continue
        seen.add(low)
        if lookup_model(conn, token) is None:
            out.append(token)
    return out[:2]


def wants_web_search(text: str) -> bool:
    return bool(_EXPLICIT_SEARCH_RE.search(text))
