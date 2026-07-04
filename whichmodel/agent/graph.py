"""Graph assembly: explicit LangGraph StateGraph with injected dependencies.

One invocation processes one user turn and ends. The web layer persists the
returned state in the session store and re-invokes on the next message.
"""

import sqlite3
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from whichmodel.agent import nodes_elicit as ne
from whichmodel.agent import nodes_recommend as nr
from whichmodel.agent import prompts
from whichmodel.agent.llm import LLMClient
from whichmodel.agent.state import AgentState
from whichmodel.retrieval.base import Retriever

KEEP_MESSAGES = 6  # verbatim window; older turns live in the summary string


@dataclass
class AgentDeps:
    """Everything the graph needs, injected so tests can mock each piece."""

    llm: LLMClient
    retriever: Retriever
    conn: sqlite3.Connection
    db_path: str
    snippets_path: Path
    usd_to_inr: float = 84.0
    search_provider: object | None = None  # tools.websearch.SearchProvider


def maybe_summarize(state: AgentState, llm: LLMClient) -> AgentState:
    """Fold messages beyond the window into a compact summary string."""
    if len(state.messages) <= KEEP_MESSAGES + 4:
        return state
    old, state.messages = state.messages[:-KEEP_MESSAGES], state.messages[-KEEP_MESSAGES:]
    excerpt = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in old)
    if state.summary:
        excerpt = f"Previous summary: {state.summary}\n{excerpt}"
    try:
        state.summary = llm.complete(
            prompts.SUMMARIZE_SYSTEM, [{"role": "user", "content": excerpt[:4000]}],
            max_tokens=150).strip()
    except Exception:  # summarization is best-effort; requirements hold the facts
        state.summary = state.summary or ""
    return state


def build_graph(deps: AgentDeps):
    """Wire nodes and edges; returns a compiled LangGraph app."""
    g = StateGraph(AgentState)

    g.add_node("router", ne.router)
    g.add_node("extract", partial(ne.extract, llm=deps.llm, usd_to_inr=deps.usd_to_inr))
    g.add_node("probe_parse", ne.probe_parse)
    g.add_node("hardware_probe", partial(ne.hardware_probe, snippets_path=deps.snippets_path))
    g.add_node("retrieve_clarify",
               partial(ne.retrieve_kb, retriever=deps.retriever, purpose="clarify"))
    g.add_node("ask_clarifying", partial(ne.ask_clarifying, llm=deps.llm))
    g.add_node("retrieve_recommend",
               partial(ne.retrieve_kb, retriever=deps.retriever, purpose="recommend"))
    g.add_node("query_catalog", partial(nr.query_catalog, conn=deps.conn))
    g.add_node("recommend", partial(nr.recommend, llm=deps.llm, conn=deps.conn,
                                    db_path=deps.db_path, usd_to_inr=deps.usd_to_inr))

    g.add_node("web_lookup", partial(ne.web_lookup, provider=deps.search_provider,
                                     conn=deps.conn))

    g.add_edge(START, "router")
    g.add_conditional_edges("router", ne.route_message,
                            {"probe_parse": "probe_parse", "extract": "extract"})
    g.add_edge("extract", "web_lookup")  # no-ops instantly when nothing to search
    g.add_conditional_edges("web_lookup", ne.readiness, {
        "retrieve_recommend": "retrieve_recommend",
        "hardware_probe": "hardware_probe",
        "retrieve_clarify": "retrieve_clarify",
    })
    g.add_conditional_edges("probe_parse", ne.readiness, {
        "retrieve_recommend": "retrieve_recommend",
        "hardware_probe": "hardware_probe",
        "retrieve_clarify": "retrieve_clarify",
    })
    g.add_edge("hardware_probe", END)
    g.add_edge("retrieve_clarify", "ask_clarifying")
    # If every remaining question was already asked, stop interrogating and
    # recommend with what we have.
    g.add_conditional_edges(
        "ask_clarifying",
        lambda s: "retrieve_recommend" if (s.recommend_now and not s.reply) else "end",
        {"retrieve_recommend": "retrieve_recommend", "end": END})
    g.add_edge("retrieve_recommend", "query_catalog")
    g.add_edge("query_catalog", "recommend")
    g.add_edge("recommend", END)

    return g.compile()


def run_turn(app, deps: AgentDeps, state: AgentState, user_message: str) -> AgentState:
    """Process one user message through the graph and return the new state."""
    state.messages.append({"role": "user", "content": user_message})
    state = maybe_summarize(state, deps.llm)
    result = app.invoke(state)
    new_state = AgentState.model_validate(result)
    if new_state.reply:
        new_state.messages.append({"role": "assistant", "content": new_state.reply})
    return new_state


def run_turn_stream(app, deps: AgentDeps, state: AgentState, user_message: str,
                    emit) -> AgentState:
    """run_turn, but activity lines are pushed to `emit` as each node finishes,
    so the UI can show what the agent is doing while it works."""
    state.messages.append({"role": "user", "content": user_message})
    state = maybe_summarize(state, deps.llm)
    # stream_mode="values" yields the INPUT state first; without this reset the
    # previous turn's activity would be re-emitted (seen in user testing as a
    # thinking trace carried into the next message).
    state.activity, state.reply, state.notices = [], "", []
    seen = 0
    latest = state
    for step in app.stream(state, stream_mode="values"):
        latest = AgentState.model_validate(step)
        for line in latest.activity[seen:]:
            emit(line)
        seen = len(latest.activity)
    if latest.reply:
        latest.messages.append({"role": "assistant", "content": latest.reply})
    return latest
