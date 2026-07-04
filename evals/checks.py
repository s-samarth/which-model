"""Programmatic assertions applied to a finished eval scenario."""

import sqlite3
from pathlib import Path

from whichmodel.agent.grounding import foreign_model_mentions
from whichmodel.agent.state import AgentState, Phase
from whichmodel.schemas import Recommendation
from whichmodel.tools.hardware import load_snippets


def _final_reply(state: AgentState) -> str:
    """The final answer only: earlier turns were grounded against earlier
    candidate sets (a pivot legitimately changes them)."""
    replies = [m["content"] for m in state.messages if m["role"] == "assistant"]
    return replies[-1] if replies else ""


def check_grounding(state: AgentState, db_path: str, conn: sqlite3.Connection) -> str | None:
    """(a) Every model named in the final answer is a grounded candidate.

    A visible self-correction ("Correction: I mentioned X...") counts as
    handled: the mechanism worked and told the user.
    """
    if state.phase != Phase.done or not state.candidates:
        return None
    text = _final_reply(state)
    allowed = {m.id for m in state.candidates}
    violations = foreign_model_mentions(text, db_path, allowed)
    if violations and "Correction:" not in text:
        return f"foreign models mentioned uncorrected: {violations}"
    return None


def check_reached_recommendation(state: AgentState, max_turns: int,
                                 done_within: int | None) -> str | None:
    """(b) Recommendation phase reached within the turn budget."""
    if state.phase != Phase.done:
        return f"phase={state.phase} after {state.user_turns} turns"
    limit = done_within or max_turns
    if state.user_turns > limit:
        return f"took {state.user_turns} turns (limit {limit})"
    return None


def check_fields(state: AgentState, expect: dict) -> str | None:
    """(c) Required requirement fields were elicited (and match, when pinned)."""
    req = state.requirements
    for field in expect.get("fields", []):
        if getattr(req, field, None) is None:
            return f"field {field} never filled"
    for pin in ("task_category", "deployment", "language_needs"):
        if pin in expect:
            got = getattr(req, pin, None)
            want = expect[pin]
            if got is None or (pin == "language_needs" and want.lower() not in str(got).lower()):
                if pin == "language_needs":
                    return f"{pin}={got!r}, wanted ~{want!r}"
            if pin != "language_needs" and str(got) != str(want):
                return f"{pin}={got}, wanted {want}"
    return None


def check_shell_safety(state: AgentState, snippets_path: Path) -> str | None:
    """(d) Every shell command shown came verbatim from the snippet library."""
    allowed = {s.command.strip() for s in load_snippets(snippets_path).values()}
    for msg in state.messages:
        if msg["role"] != "assistant" or "```" not in msg["content"]:
            continue
        blocks = msg["content"].split("```")[1::2]
        for block in blocks:
            code = block.strip().removeprefix("bash\n").strip()
            if code and code not in allowed:
                return f"non-library command shown: {code[:60]!r}"
    return None


def check_schema(state: AgentState) -> str | None:
    """(e) The recommendation payload validates against the schema."""
    if state.recommendation is None:
        return None
    try:
        Recommendation.model_validate(state.recommendation.model_dump())
        return None
    except Exception as err:
        return f"schema invalid: {err}"


def check_expectations(state: AgentState, expect: dict) -> str | None:
    """Scenario-specific expectations on the composed answer.

    The answer is free-form Markdown, so expectations verify that the final
    reply names at least one suitable candidate; constraint filtering (budget,
    modality, memory) is enforced upstream by find_candidates and covered by
    unit tests.
    """
    if state.phase != Phase.done:
        return None  # reached-recommendation check reports this case
    if not state.candidates:
        return "no candidates behind the final answer"
    text = _final_reply(state).lower()
    def mentioned(m):
        return m.name.lower() in text or m.id.lower() in text \
            or m.id.split("/")[-1].lower() in text
    named = [m for m in state.candidates if mentioned(m)]
    if not named:
        return "final answer names no catalog candidate"
    if expect.get("picks_local") and not any(m.available_local for m in named):
        return "answer names no locally-runnable candidate"
    if expect.get("picks_support_image") and not any(
            "image" in m.input_modalities for m in named):
        return "answer names no image-capable candidate"
    return None
