"""Per-request token streaming channel.

The web layer sets a token emitter in the worker thread's context before
running the graph; the recommend node streams LLM tokens through it. A
contextvar keeps concurrent sessions isolated without threading emitters
through every node signature.
"""

import contextvars
from collections.abc import Callable

token_emitter: contextvars.ContextVar[Callable[[str], None] | None] = contextvars.ContextVar(
    "token_emitter", default=None
)


def emit_tokens(text_iter) -> str:
    """Drain a token iterator, forwarding to the active emitter. Returns full text."""
    emit = token_emitter.get()
    parts: list[str] = []
    for chunk in text_iter:
        if chunk:
            parts.append(chunk)
            if emit:
                emit(chunk)
    return "".join(parts)
