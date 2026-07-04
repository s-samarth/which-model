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

    def stream(self, system: str, messages: list[dict], *, max_tokens: int = 1200):
        """Yield text chunks as they generate."""
        ...


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
        self._keep_alive = settings.llm_keep_alive or None

    def complete(self, system: str, messages: list[dict], *, max_tokens: int = 700,
                 json_mode: bool = False) -> str:
        kwargs: dict = {"response_format": {"type": "json_object"}} if json_mode else {}
        extra: dict = {}
        if self._reasoning_effort:
            extra["reasoning_effort"] = self._reasoning_effort
        if self._keep_alive:
            extra["keep_alive"] = self._keep_alive
        if extra:
            kwargs["extra_body"] = extra
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
            # Some backends reject the extra parameters; retry without them once.
            log.info("backend rejected extra body params; retrying without them")
            self._reasoning_effort = self._keep_alive = None
            kwargs.pop("extra_body")
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system}, *messages],
                temperature=self._temperature, max_tokens=max_tokens, **kwargs,
            )
        return resp.choices[0].message.content or ""

    def stream(self, system: str, messages: list[dict], *, max_tokens: int = 1200):
        """Yield content chunks from a streaming completion."""
        kwargs: dict = {}
        extra: dict = {}
        if self._reasoning_effort:
            extra["reasoning_effort"] = self._reasoning_effort
        if self._keep_alive:
            extra["keep_alive"] = self._keep_alive
        if extra:
            kwargs["extra_body"] = extra
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, *messages],
            temperature=self._temperature, max_tokens=max_tokens, stream=True, **kwargs,
        )
        for event in resp:
            if event.choices and event.choices[0].delta:
                yield event.choices[0].delta.content or ""


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        t = t.rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return t[start : end + 1] if start != -1 and end > start else t


def _skeleton(model_cls: type[BaseModel]) -> str:
    """Compact field guide, e.g. {"deployment": "local|api|either|null", ...}.

    A 4B model handed a full JSON schema tends to echo the schema back or pad
    every null field until it hits the token limit; a terse skeleton avoids both.
    """
    schema = model_cls.model_json_schema()
    defs = schema.get("$defs", {})

    def render(prop: dict) -> str:
        if "$ref" in prop:
            resolved = defs.get(prop["$ref"].split("/")[-1], {})
            return render(resolved) if "enum" in resolved else render_obj(resolved)
        if "anyOf" in prop:
            opts = [render(p) for p in prop["anyOf"] if p.get("type") != "null"]
            return (opts[0] if opts else '"?"') + "|null"
        if "enum" in prop:
            return '"' + "|".join(str(v) for v in prop["enum"]) + '"'
        t = prop.get("type", "string")
        if t == "array":
            return f"[{render(prop.get('items', {}))}]"
        if t == "object":
            return render_obj(prop)
        return {"number": "0", "integer": "0", "boolean": "true|false"}.get(t, '"text"')

    def render_obj(obj_schema: dict) -> str:
        props = obj_schema.get("properties", {})
        inner = ", ".join(f'"{k}": {render(v)}' for k, v in props.items())
        return "{" + inner + "}"

    return render_obj(schema)


def structured(llm: LLMClient, system: str, messages: list[dict], model_cls: type[T],
               *, max_tokens: int = 700) -> T:
    """Get a validated pydantic object out of the LLM, with one repair round."""
    sys_prompt = (
        f"{system}\n\nRespond with ONLY one JSON object, no prose, no markdown. "
        f"Omit fields you have nothing to say about. Output actual values, never "
        f"a schema. Fields:\n{_skeleton(model_cls)}"
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
