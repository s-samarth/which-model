"""A scripted LLM mock: returns queued responses, records every call."""

import json
from dataclasses import dataclass, field


@dataclass
class MockLLM:
    """Feed it a queue of responses (dicts are JSON-dumped). Repeats last if exhausted."""

    responses: list = field(default_factory=list)
    calls: list = field(default_factory=list)

    def complete(self, system: str, messages: list[dict], *, max_tokens: int = 700,
                 json_mode: bool = False) -> str:
        self.calls.append({"system": system, "messages": messages, "json_mode": json_mode})
        if not self.responses:
            return "{}"
        # Pop until one response is left, then repeat it (keeps loops stable).
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        return json.dumps(item) if isinstance(item, dict) else str(item)

    def stream(self, system: str, messages: list[dict], *, max_tokens: int = 1200):
        text = self.complete(system, messages, max_tokens=max_tokens)
        mid = max(1, len(text) // 2)
        yield text[:mid]
        yield text[mid:]


def queue(*items) -> MockLLM:
    return MockLLM(responses=list(items))
