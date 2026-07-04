"""Session storage behind an interface.

v1 ships an in-memory store with TTL. A persistent per-user store can be added
later by implementing SessionStore without touching the web layer.
"""

import time
from typing import Protocol

from whichmodel.agent.state import AgentState


class SessionStore(Protocol):
    """Server-side session state keyed by an opaque session id."""

    def get(self, session_id: str) -> AgentState | None: ...

    def put(self, session_id: str, state: AgentState) -> None: ...

    def delete(self, session_id: str) -> None: ...


class InMemorySessionStore:
    """Dict-backed store with TTL, pruned lazily on access."""

    def __init__(self, ttl_s: int = 3600):
        self._ttl = ttl_s
        self._data: dict[str, tuple[float, AgentState]] = {}

    def _prune(self) -> None:
        cutoff = time.monotonic() - self._ttl
        expired = [k for k, (ts, _) in self._data.items() if ts < cutoff]
        for k in expired:
            del self._data[k]

    def get(self, session_id: str) -> AgentState | None:
        self._prune()
        entry = self._data.get(session_id)
        return entry[1] if entry else None

    def put(self, session_id: str, state: AgentState) -> None:
        self._data[session_id] = (time.monotonic(), state)

    def delete(self, session_id: str) -> None:
        self._data.pop(session_id, None)
