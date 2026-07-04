"""Graph nodes for the recommending side: catalog query and final composition.

The LLM only chooses candidate ids and writes short "why" text. Prices, scores,
the comparison table and INR conversion are assembled deterministically from
catalog rows, so numbers cannot be hallucinated.
"""

import logging
import sqlite3

from whichmodel.agent import grounding, prompts
from whichmodel.agent.llm import LLMClient, StructuredOutputError, structured
from whichmodel.agent.state import AgentState, Phase, PickPlan
from whichmodel.schemas import ModelRow, Pick, Recommendation, Requirements, TaskCategory
from whichmodel.tools import catalog, costs

log = logging.getLogger(__name__)


def query_catalog(state: AgentState, conn: sqlite3.Connection) -> AgentState:
    """Deterministic candidate lookup, relaxing the budget once if it filters everything."""
    req = state.requirements
    state.candidates = catalog.find_candidates(conn, req)
    if not state.candidates and req.budget_monthly_usd is not None:
        relaxed = req.model_copy(update={"budget_monthly_usd": None})
        state.candidates = catalog.find_candidates(conn, relaxed)
        if state.candidates:
            state.notices.append("budget_relaxed")
    state.phase = Phase.recommending
    return state


def _candidate_lines(cands: list[ModelRow], benchmark: str) -> str:
    lines = []
    for m in cands:
        score = m.scores.get(benchmark)
        bits = [
            m.id,
            f"score={score:.0f}" if score is not None else "score=unmeasured",
            "free" if m.is_free else (
                (f"~${m.est_monthly_usd:.2f}/mo" if m.est_monthly_usd < 10
                 else f"~${m.est_monthly_usd:.0f}/mo")
                if m.est_monthly_usd is not None else "local-only"),
            f"ctx={m.context_length // 1000}k" if m.context_length else "ctx=?",
        ]
        if m.available_local:
            bits.append(f"runs locally ({m.est_memory_gb}GB)" if m.est_memory_gb else "local")
        lines.append(" | ".join(bits))
    return "\n".join(lines)


def _fallback_plan(cands: list[ModelRow]) -> PickPlan:
    """Deterministic plan when the LLM cannot produce a valid one."""
    top = cands[0]
    runner = cands[1] if len(cands) > 1 else None
    cheap = min(cands, key=lambda m: (m.est_monthly_usd if m.est_monthly_usd is not None else 0))
    budget = cheap if cheap.id not in {top.id, runner.id if runner else ""} else None
    mk = "highest task score among the candidates from our catalog"
    return PickPlan(
        top_pick_id=top.id, runner_up_id=runner.id if runner else None,
        budget_pick_id=budget.id if budget else None,
        why_top=f"{top.name} has the {mk}.",
        why_runner_up=f"{runner.name} is the strongest alternative." if runner else None,
        why_budget=f"{budget.name} is the cheapest solid option." if budget else None,
        assumptions=["Composed automatically from catalog rankings."], caveats=[])


def _valid_plan(plan: PickPlan, cands: list[ModelRow], db_path: str) -> bool:
    ids = {m.id for m in cands}
    named = [plan.top_pick_id, plan.runner_up_id, plan.budget_pick_id]
    if any(n is not None and n not in ids for n in named):
        return False
    prose = " ".join(filter(None, [plan.why_top, plan.why_runner_up, plan.why_budget,
                                   *plan.assumptions, *plan.caveats]))
    return not grounding.foreign_model_mentions(prose, db_path, ids)


def _auto_assumptions(req: Requirements, state: AgentState) -> list[str]:
    out = []
    if req.usage_level is None and req.deployment != "local":
        out.append("Assumed moderate usage (about an hour a day) for cost estimates.")
    if req.budget_monthly_usd is None and req.deployment != "local":
        out.append("No budget given, so options across price tiers are shown.")
    if "budget_relaxed" in state.notices:
        out.append("Nothing fit the stated budget at your usage level; "
                   "showing the cheapest capable options instead.")
    if req.task_category is None:
        out.append("Task was unclear, so rankings use overall quality scores.")
    return out


def _build_payload(plan: PickPlan, state: AgentState, conn: sqlite3.Connection,
                   benchmark: str, usd_to_inr: float) -> Recommendation:
    by_id = {m.id: m for m in state.candidates}
    picks = []
    for role, mid, why in (("top_pick", plan.top_pick_id, plan.why_top),
                           ("runner_up", plan.runner_up_id, plan.why_runner_up),
                           ("budget_pick", plan.budget_pick_id, plan.why_budget)):
        if mid is None:
            continue
        m = by_id[mid]
        picks.append(Pick(
            model_id=m.id, name=m.name, role=role, why=why or "",
            monthly_cost_usd=m.est_monthly_usd,
            monthly_cost_inr=costs.usd_to_inr(m.est_monthly_usd, usd_to_inr),
            ollama_tag=m.ollama_tag))
    pick_ids = {p.model_id for p in picks}
    comparison = [
        {
            "name": m.name, "model_id": m.id,
            "score": m.scores.get(benchmark),
            "benchmark": benchmark.replace("livebench_", "LiveBench "),
            "price_in": m.prompt_usd_per_m, "price_out": m.completion_usd_per_m,
            "est_monthly_usd": m.est_monthly_usd,
            "context_k": (m.context_length or 0) // 1000 or None,
            "local": m.available_local, "free": m.is_free, "ollama_tag": m.ollama_tag,
            "memory_gb": m.est_memory_gb, "picked": m.id in pick_ids,
        }
        for m in state.candidates[:6]
    ]
    return Recommendation(
        picks=picks, comparison=comparison,
        assumptions=[*plan.assumptions, *_auto_assumptions(state.requirements, state)],
        caveats=plan.caveats, data_age=catalog.data_age(conn))


def recommend(state: AgentState, llm: LLMClient, conn: sqlite3.Connection,
              db_path: str, usd_to_inr: float) -> AgentState:
    """Compose the final recommendation strictly from candidates + KB context."""
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
    benchmark = catalog.CATEGORY_BENCHMARKS[task][0]
    system = prompts.RECOMMEND_SYSTEM.format(
        requirements=req.model_dump_json(exclude_none=True, exclude={"open_questions"}),
        benchmark=benchmark.replace("livebench_", "LiveBench "),
        candidates=_candidate_lines(state.candidates, benchmark),
        kb="\n\n".join(state.kb_context)[:3500])
    plan: PickPlan | None = None
    messages = [{"role": "user", "content": "Choose the picks now."}]
    for attempt in range(2):
        try:
            cand_plan = structured(llm, system, messages, PickPlan, max_tokens=600)
        except StructuredOutputError:
            break
        if _valid_plan(cand_plan, state.candidates, db_path):
            plan = cand_plan
            break
        log.warning("recommendation grounding violation (attempt %d)", attempt + 1)
        messages = [{"role": "user", "content":
                     "Choose the picks now. Previous attempt named models outside the "
                     "candidate list. Use ONLY ids from the list."}]
    if plan is None:
        plan = _fallback_plan(state.candidates)
        state.notices.append("recommendation_fallback")

    state.recommendation = _build_payload(plan, state, conn, benchmark, usd_to_inr)
    top = state.recommendation.picks[0]
    state.reply = f"Here is my recommendation. Top pick: {top.name}. {top.why}"
    state.phase = Phase.done
    return state
