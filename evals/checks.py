"""Programmatic assertions applied to a finished eval scenario."""

import sqlite3
from pathlib import Path

from whichmodel.agent.grounding import foreign_model_mentions
from whichmodel.agent.state import AgentState, Phase
from whichmodel.schemas import Recommendation
from whichmodel.tools.hardware import load_snippets


def _rec_prose(state: AgentState) -> str:
    parts = [m["content"] for m in state.messages if m["role"] == "assistant"]
    rec = state.recommendation
    if rec:
        parts += [p.why for p in rec.picks] + rec.assumptions + rec.caveats
    return "\n".join(parts)


def check_grounding(state: AgentState, db_path: str, conn: sqlite3.Connection) -> str | None:
    """(a) Every model named in the final answer exists in candidates/DB picks."""
    rec = state.recommendation
    if rec is None:
        return None
    for pick in rec.picks:
        if not conn.execute("SELECT 1 FROM models WHERE id=?", (pick.model_id,)).fetchone():
            return f"pick {pick.model_id} not in DB"
    allowed = {m.id for m in state.candidates}
    violations = foreign_model_mentions(_rec_prose(state), db_path, allowed)
    return f"foreign models mentioned: {violations}" if violations else None


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
    """Scenario-specific expectations on the picks."""
    rec = state.recommendation
    if rec is None or not rec.picks:
        return "no recommendation payload"
    by_id = {m.id: m for m in state.candidates}
    for pick in rec.picks:
        m = by_id.get(pick.model_id)
        if m is None:
            return f"pick {pick.model_id} not among candidates"
        if expect.get("picks_local") and not m.available_local:
            return f"{m.id} is not locally runnable"
        if expect.get("picks_support_image") and "image" not in m.input_modalities:
            return f"{m.id} does not accept images"
        cap = expect.get("max_pick_monthly_usd")
        if cap is not None and (pick.monthly_cost_usd or 0) > cap:
            return f"{m.id} costs ${pick.monthly_cost_usd}/mo over cap {cap}"
        budget = expect.get("picks_within_budget")
        if budget is not None and (pick.monthly_cost_usd or 0) > budget:
            return f"{m.id} exceeds budget {budget}"
    return None
