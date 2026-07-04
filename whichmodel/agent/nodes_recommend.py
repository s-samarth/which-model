"""Recommendation side of the graph: deterministic facts, LLM-composed answer.

There is deliberately no fixed answer template. The catalog produces a FACTS
block (scores by name, prices, computed local-setup numbers); the LLM writes
the whole Markdown answer, streamed token by token, shaped by what the user
asked. Grounding is enforced after the fact: models named outside FACTS get a
visible correction, and every number the model may use is in its prompt.
"""

import itertools
import logging
import sqlite3

from whichmodel.agent import grounding, prompts, streaming
from whichmodel.agent.state import AgentState, Phase
from whichmodel.schemas import ModelRow, Requirements, TaskCategory
from whichmodel.tools import catalog, costs, performance

log = logging.getLogger(__name__)

# What to ask the web for when the catalog has no score for a candidate.
SCORE_SEARCH_TERMS = {
    TaskCategory.coding: "SWE-bench aider coding benchmark score",
    TaskCategory.agentic_tool_use: "terminal-bench tau-bench agentic benchmark score",
    TaskCategory.image_understanding: "MMMU vision benchmark score",
}
DEFAULT_SCORE_TERMS = "LLM benchmark scores"


def query_catalog(state: AgentState, conn: sqlite3.Connection,
                  provider=None) -> AgentState:
    """Deterministic candidate lookup with two web supplements (context only,
    never picks): thin catalog coverage, and missing scores for top candidates."""
    req = state.requirements
    state.activity.append("Querying the model catalog")
    state.candidates = catalog.find_candidates(conn, req)
    if not state.candidates and req.budget_monthly_usd is not None:
        relaxed = req.model_copy(update={"budget_monthly_usd": None})
        state.candidates = catalog.find_candidates(conn, relaxed)
        if state.candidates:
            state.notices.append("budget_relaxed")
    state.activity.append(f"Ranking {len(state.candidates)} catalog candidates")
    if provider is None:
        state.phase = Phase.recommending
        return state

    task = req.task_category or TaskCategory.other
    if len(state.candidates) < 3:
        where = "run locally" if str(req.deployment) == "local" else "API"
        query = f"best {task.value.replace('_', ' ')} LLM {where} 2026"
        _search_into_context(state, provider, query, "web search")

    primary = catalog.CATEGORY_BENCHMARKS[task][0]
    unmeasured = [m for m in state.candidates[:3] if primary not in m.scores]
    terms = SCORE_SEARCH_TERMS.get(task, DEFAULT_SCORE_TERMS)
    for m in unmeasured[:2]:
        _search_into_context(state, provider, f"{m.name} {terms}", f"web scores: {m.name}")
    state.phase = Phase.recommending
    return state


def _search_into_context(state: AgentState, provider, query: str, label: str) -> None:
    state.activity.append(f'Searching the web: "{query}"')
    results = provider.search(query, k=3)
    state.activity.extend(f"Reading: {r.url}" for r in results)
    if results:
        joined = "\n".join(f"- {r.title}: {r.snippet} ({r.url})" for r in results)
        state.kb_context.append(f"[{label}: {query}]\n{joined}")


def _score_lines(m: ModelRow, task: TaskCategory) -> str:
    primary, secondary = catalog.CATEGORY_BENCHMARKS[task]
    keys = dict.fromkeys([primary, secondary, "livebench_global"])
    parts = []
    for key in keys:
        nice = key.replace("livebench_", "").replace("_", " ")
        if key in m.scores:
            parts.append(f"{nice} {m.scores[key]:.0f}/100 (LiveBench)")
    return "; ".join(parts) if parts else "no benchmark scores in catalog (unmeasured)"


def _fact_entry(i: int, m: ModelRow, req: Requirements, conn: sqlite3.Connection,
                task: TaskCategory) -> str:
    lines = [f"{i}. {m.name} [{m.id}]", f"   scores: {_score_lines(m, task)}"]
    if m.available_api and m.prompt_usd_per_m is not None:
        est = f" -> est ${m.est_monthly_usd:.2f}/mo at their usage" \
            if m.est_monthly_usd is not None else ""
        price = "free tier" if m.is_free else (
            f"${m.prompt_usd_per_m:.2f}/M in, ${m.completion_usd_per_m:.2f}/M out{est}")
        lines.append(f"   API: {price} | context {(m.context_length or 0) // 1000}k")
    elif not m.available_api:
        lines.append("   API: not offered (run it yourself)")
    if m.available_local and m.param_b:
        setup = performance.local_setup(
            conn, m, req.hardware, req.usage_level,
            str(req.task_category) if req.task_category else None)
        quants = ", ".join(
            f"{q['quant']} ~{q['memory_gb']}GB"
            + ("" if q["fits"] is None else (" (fits)" if q["fits"] else " (too big)"))
            for q in setup["quants"] if q["quant"] in ("q4_K_M", "q8_0"))
        moe = f" | {setup['moe_note']}" if setup["moe_note"] else ""
        tag = f" | install: ollama pull {m.ollama_tag}" if m.ollama_tag else ""
        lines.append(f"   local: {m.param_b:g}B params; {quants}; "
                     f"~{setup['est_speed']} on their hardware{tag}{moe}")
    elif not m.available_local:
        lines.append("   local: not available (closed weights)")
    return "\n".join(lines)


def _facts(state: AgentState, conn: sqlite3.Connection, task: TaskCategory) -> str:
    req = state.requirements
    return "\n".join(_fact_entry(i + 1, m, req, conn, task)
                     for i, m in enumerate(state.candidates[:6]))


def recommend(state: AgentState, llm, conn: sqlite3.Connection,
              db_path: str, usd_to_inr: float) -> AgentState:
    """Stream the LLM's own Markdown answer over the FACTS block."""
    req = state.requirements
    if not state.candidates:
        state.reply = (
            "I could not find a model in my catalog that fits those constraints, "
            "usually this means very tight hardware for local use. If you can use "
            f"a cloud API or free tier, say so and I will re-check. (Catalog data: "
            f"refreshed {catalog.data_age(conn)}.)")
        state.phase = Phase.done
        return state

    task = req.task_category or TaskCategory.other
    primary = catalog.CATEGORY_BENCHMARKS[task][0]
    system = prompts.RECOMMEND_SYSTEM.format(
        requirements=req.model_dump_json(exclude_none=True, exclude={"open_questions"}),
        benchmark_blurb=catalog.BENCHMARK_BLURBS.get(primary, ""),
        cost_basis=costs.basis_text(req.usage_level),
        data_age=catalog.data_age(conn),
        facts=_facts(state, conn, task),
        kb="\n\n".join(state.kb_context)[:4000])
    state.activity.append("Composing the answer")
    user_msg = state.messages[-1]["content"][:600] if state.messages else "Recommend now."
    messages = [{"role": "user", "content": user_msg}]
    prefix = state.reply_prefix or ""
    try:
        text = streaming.emit_tokens(
            itertools.chain([prefix], llm.stream(system, messages, max_tokens=1200)))
    except Exception as err:
        log.warning("streaming failed (%s); falling back to non-streaming", err)
        try:
            text = prefix + llm.complete(system, messages, max_tokens=1200)
        except Exception:
            log.exception("recommendation generation failed entirely")
            top = state.candidates[0]
            text = (f"{prefix}Based on my catalog, {top.name} is the strongest fit for "
                    f"your needs (see the facts I have on it), but I hit a problem "
                    f"writing a fuller answer. Ask again for details.")

    allowed = {m.id for m in state.candidates}
    violations = grounding.foreign_model_mentions(text, db_path, allowed)
    if violations:
        log.warning("grounding violations in composed answer: %s", violations)
        names = ", ".join(v.split("/")[-1] for v in violations)
        correction = (f"\n\n*Correction: I mentioned {names} above, but I do not have "
                      f"catalog data for {'it' if len(violations) == 1 else 'them'} "
                      "this turn, so please disregard those specifics.*")
        text += correction
        emit = streaming.token_emitter.get()
        if emit:
            emit(correction)

    state.reply = text.strip()
    state.phase = Phase.done
    return state
