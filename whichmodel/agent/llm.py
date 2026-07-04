"""LLM client protocol, OpenAI-compatible implementation, structured-output wrapper.

The app talks to any OpenAI-compatible endpoint (Ollama, LM Studio, vLLM,
cloud) configured via OPENAI_BASE_URL and MODEL_NAME. A 4B model will
occasionally emit malformed JSON, so structured() validates, re-prompts once
with the error, and raises StructuredOutputError on the second failure so
callers can fall back gracefully.
"""

import json
import logging
from typing import Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from whichmodel.config import Settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """The model could not produce valid JSON after one repair attempt."""


class LLMClient(Protocol):
    """Minimal completion interface the graph nodes depend on."""

    def complete(self, system: str, messages: list[dict], *, max_tokens: int = 700,
                 json_mode: bool = False) -> str: ...


class OpenAICompatClient:
    """LLMClient against any OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, settings: Settings):
        self._client = OpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            timeout=settings.llm_timeout_s,
            max_retries=1,
        )
        self._model = settings.model_name
        self._temperature = settings.llm_temperature
        self._reasoning_effort = settings.llm_reasoning_effort or None

    def complete(self, system: str, messages: list[dict], *, max_tokens: int = 700,
                 json_mode: bool = False) -> str:
        kwargs: dict = {"response_format": {"type": "json_object"}} if json_mode else {}
        if self._reasoning_effort:
            kwargs["extra_body"] = {"reasoning_effort": self._reasoning_effort}
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system}, *messages],
                temperature=self._temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except Exception:
            if "extra_body" not in kwargs:
                raise
            # Some backends reject reasoning_effort; retry without it once.
            log.info("backend rejected reasoning_effort; retrying without it")
            self._reasoning_effort = None
            kwargs.pop("extra_body")
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system}, *messages],
                temperature=self._temperature, max_tokens=max_tokens, **kwargs,
            )
        return resp.choices[0].message.content or ""


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        t = t.rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return t[start : end + 1] if start != -1 and end > start else t


def structured(llm: LLMClient, system: str, messages: list[dict], model_cls: type[T],
               *, max_tokens: int = 700) -> T:
    """Get a validated pydantic object out of the LLM, with one repair round."""
    schema_hint = json.dumps(model_cls.model_json_schema(), separators=(",", ":"))
    sys_prompt = (
        f"{system}\n\nRespond with ONLY a JSON object matching this schema "
        f"(no prose, no markdown):\n{schema_hint}"
    )
    convo = list(messages)
    last_err: Exception | None = None
    for attempt in range(2):
        raw = llm.complete(sys_prompt, convo, max_tokens=max_tokens, json_mode=True)
        try:
            return model_cls.model_validate(json.loads(_strip_fences(raw)))
        except (json.JSONDecodeError, ValidationError) as err:
            last_err = err
            log.warning("structured output invalid (attempt %d): %s", attempt + 1, err)
            convo = convo + [
                {"role": "assistant", "content": raw[:1000]},
                {"role": "user", "content":
                    f"That JSON was invalid: {str(err)[:300]}. "
                    "Reply again with ONLY the corrected JSON object."},
            ]
    raise StructuredOutputError(str(last_err))
