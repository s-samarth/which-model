"""Graph nodes for the eliciting side: routing, extraction, KB retrieval,
clarifying questions, hardware probing."""

import logging
import re

from whichmodel.agent import prompts
from whichmodel.agent.llm import LLMClient, StructuredOutputError, structured
from whichmodel.agent.state import (
    AgentState,
    ClarifyingQuestions,
    Phase,
    RequirementsPatch,
    merge_patch,
)
from whichmodel.retrieval.base import Retriever
from whichmodel.schemas import Deployment, TaskCategory
from whichmodel.tools import hardware as hw_tools

log = logging.getLogger(__name__)

IMPATIENCE_RE = re.compile(
    r"just (tell|recommend|give|pick)|whatever you think|stop asking|don'?t ask|"
    r"pick (one|for me)|surprise me|best model\b.{0,12}$", re.I)

TASK_DOC = {t: f"taxonomy/{t.value.replace('_', '-')}" for t in TaskCategory}
TASK_DOC[TaskCategory.chat_assistant] = "taxonomy/chat-assistant"
TASK_DOC[TaskCategory.rag_doc_qa] = "taxonomy/rag-doc-qa"
TASK_DOC[TaskCategory.other] = None

FALLBACK_QUESTIONS = {
    "task_category": "What would you mainly use the AI for, day to day?",
    "deployment": "Would you rather run it on your own computer (private, free to run), "
                  "or use a cloud service (more capable, pay per use)?",
    "budget_monthly_usd": "Roughly how much per month are you comfortable spending, if anything?",
    "hardware": "What computer would it run on (e.g. MacBook Air 16GB, gaming PC)?",
    "usage_level": "How much would you use it: a few chats a day, about an hour a day, "
                   "or several hours daily?",
    "context_need": "Will you feed it long material (contracts, whole codebases), "
                    "or mostly short questions?",
}
DOC_TRIM_CHARS = 1500


def last_user_message(state: AgentState) -> str:
    for msg in reversed(state.messages):
        if msg["role"] == "user":
            return msg["content"]
    return ""


def router(state: AgentState) -> AgentState:
    """Deterministic turn routing; semantic nuances are handled by extraction."""
    state.user_turns += 1
    # recommend_now is a per-turn signal. It must NOT persist: a sticky flag
    # made every post-recommendation follow-up short-circuit to a stale answer.
    state.recommend_now = bool(IMPATIENCE_RE.search(last_user_message(state)))
    state.reply, state.recommendation, state.notices = "", None, []
    state.kb_context, state.activity, state.reply_prefix = [], [], ""
    return state


def route_message(state: AgentState) -> str:
    if state.pending_probe and hw_tools.looks_like_probe_output(last_user_message(state)):
        return "probe_parse"
    return "extract"


def extract(state: AgentState, llm: LLMClient, usd_to_inr: float = 84.0) -> AgentState:
    """LLM structured extraction with repair; falls back to asking directly."""
    state.activity.append("Reading your message for requirements")
    system = prompts.EXTRACT_SYSTEM.format(
        requirements=state.requirements.model_dump_json(exclude_none=True,
                                                        exclude={"open_questions"}))
    # Long assistant replies (recommendation text) would drown a small model;
    # the requirements object is the real memory, so clip each message hard.
    window = [{"role": m["role"], "content": m["content"][:400]}
              for m in state.messages[-6:]]
    if state.summary:
        window = [{"role": "system", "content": f"Earlier: {state.summary}"}, *window]
    try:
        patch = structured(llm, system, window, RequirementsPatch, max_tokens=400)
        state.requirements = merge_patch(state.requirements, patch, usd_to_inr)
        # The small model flags this spuriously on first contact; trust it only
        # once the user has had a real chance to be asked something.
        if patch.wants_recommendation_now and state.user_turns >= 2:
            state.recommend_now = True
    except StructuredOutputError:
        log.warning("extraction failed twice; continuing with unchanged requirements")
        state.notices.append("extraction_failed")
    return state


def readiness(state: AgentState) -> str:
    """Decide the next hop after extraction. Guarantees an answer by turn 6."""
    missing = state.requirements.missing_required()
    if state.recommend_now or not missing or state.user_turns >= 6:
        return "retrieve_recommend"
    if "hardware" in missing and state.requirements.deployment == Deployment.local:
        return "hardware_probe"
    return "retrieve_clarify"


def _gaps(state: AgentState) -> list[str]:
    req = state.requirements
    gaps = state.requirements.missing_required()
    for soft, val in (("usage_level", req.usage_level), ("context_need", req.context_need)):
        if val is None and soft not in gaps:
            gaps.append(soft)
    return gaps[:3]


def retrieve_kb(state: AgentState, retriever: Retriever, purpose: str) -> AgentState:
    """Deterministic doc selection plus BM25 over the user's own words.

    Second round (capped): when recommending, ensure the benchmark explainer
    for the ranking signal is present so scores can be narrated honestly.
    """
    req = state.requirements
    msg = last_user_message(state)
    names: list[str] = []
    if req.task_category and TASK_DOC.get(req.task_category):
        names.append(TASK_DOC[req.task_category])
    if req.deployment in (Deployment.local, None) or req.privacy_need == "high":
        names.append("guides/local-inference")
    if re.search(r"host|gpu|server|self-?host|setup", msg, re.I):
        names.append("guides/gpu-hosting")
    if purpose == "clarify" and re.search(
            r"not sure|don'?t know|no idea|whatever|confus|maybe|i guess", msg, re.I):
        names.append("guides/reading-user-language")
    if purpose == "clarify" and req.context_need is None:
        names.append("guides/context-length")
    if purpose == "recommend" and req.deployment != Deployment.local:
        names.append("guides/pricing-mental-models")
    if req.language_needs and re.search(r"hindi|indi|tamil|telugu|inr|rupee",
                                        req.language_needs, re.I):
        names.append("regional/india-notes")
    docs = [d for n in names if (d := retriever.get(n))]
    for extra in retriever.search(msg or (req.task_description or ""), k=2):
        if extra.name not in {d.name for d in docs}:
            docs.append(extra)
    if purpose == "recommend" and not any(d.name == "benchmarks/livebench" for d in docs):
        if lb := retriever.get("benchmarks/livebench"):  # round 2 of 2
            docs.append(lb)
    web_chunks = [c for c in state.kb_context if c.startswith("[web")]
    state.kb_context = web_chunks + [f"[{d.name}]\n{d.text[:DOC_TRIM_CHARS]}"
                                     for d in docs[:4]]
    state.activity.extend(f"Reading knowledge base: {d.name}" for d in docs[:4])
    state.phase = Phase.retrieving
    return state


def _is_repeat(question: str, asked: list[str]) -> bool:
    """Cheap similarity: shared 4+ letter word overlap above half the question."""
    words = {w for w in re.findall(r"[a-z]{4,}", question.lower())}
    if not words:
        return False
    return any(len(words & {w for w in re.findall(r"[a-z]{4,}", a.lower())}) / len(words) > 0.6
               for a in asked)


def ask_clarifying(state: AgentState, llm: LLMClient) -> AgentState:
    """Ask 1-2 grounded questions; canned questions if the LLM output is broken.

    Previously-asked questions are injected into the prompt and re-checked
    here, because a small model will happily re-ask (seen in user testing).
    """
    state.activity.append("Deciding what to ask next")
    gaps = _gaps(state)
    n = min(2, len(gaps)) or 1
    asked = state.asked_questions[-8:]
    system = prompts.CLARIFY_SYSTEM.format(
        n=n, gaps=", ".join(gaps), asked="\n".join(f"- {q}" for q in asked) or "- none yet",
        kb="\n\n".join(state.kb_context)[:3000])
    try:
        qs = structured(llm, system, state.messages[-4:], ClarifyingQuestions, max_tokens=200)
        questions = [q for q in qs.questions[:2] if not _is_repeat(q, asked)]
    except StructuredOutputError:
        questions = []
    if not questions:  # LLM broken or everything it produced was a repeat
        questions = [FALLBACK_QUESTIONS[g] for g in gaps[:2]
                     if g in FALLBACK_QUESTIONS and not _is_repeat(FALLBACK_QUESTIONS[g], asked)]
    if not questions:  # nothing new left to ask; stop interrogating
        state.recommend_now = True
        state.reply = ""
        return state
    state.asked_questions.extend(questions)
    state.requirements.open_questions = questions
    state.reply = (state.reply_prefix + " ".join(questions)).strip()
    state.phase = Phase.eliciting
    return state


def web_lookup(state: AgentState, provider, conn) -> AgentState:
    """Search the web for model names the catalog does not know, or on request.

    Results enter kb_context as labeled chunks and the finding is reported to
    the user via reply_prefix. Picks still come only from the catalog.
    """
    from whichmodel.tools import websearch

    if provider is None:
        return state
    msg = last_user_message(state)
    unknown = websearch.unknown_model_mentions(msg, conn)
    queries = [f"{name} AI model" for name in unknown]
    if websearch.wants_web_search(msg) and not queries:
        queries = [msg[:90]]
    notes = []
    for name, query in zip(unknown or ["your question"], queries, strict=False):
        state.activity.append(f'Searching the web: "{query}"')
        results = provider.search(query, k=3)
        state.activity.extend(f"Reading: {r.url}" for r in results)
        if results:
            joined = "\n".join(f"- {r.title}: {r.snippet} ({r.url})" for r in results)
            state.kb_context.append(f"[web search: {query}]\n{joined}")
            if name != "your question":
                notes.append(
                    f'"{name}" is not in my catalog, so I cannot recommend it, but the '
                    f'web says: {results[0].title} ({results[0].url}).')
        elif name != "your question":
            notes.append(f'"{name}" is not in my catalog and a web search found '
                         "nothing solid either; it may not exist.")
    if notes:
        state.reply_prefix = " ".join(notes) + "\n\n"
    return state


def hardware_probe(state: AgentState, snippets_path) -> AgentState:
    """Emit a canned probe command (never generated), or ask directly on retry."""
    if state.pending_probe:  # probe already attempted; fall back to a plain question
        state.reply = ("No problem. Roughly how much memory (RAM) does your computer "
                       "have, and is it a Mac or a Windows/Linux machine?")
        state.phase = Phase.probing_hardware
        return state
    os_name = state.requirements.hardware.os if state.requirements.hardware else None
    snip = hw_tools.snippet_for_os(snippets_path, os_name)
    others = "" if os_name else (
        "\n\nNot on a Mac? Say so and I'll give you the Windows or Linux version instead.")
    state.reply = (
        "To suggest models that actually run on your machine, I need to know its "
        f"memory and chip. {snip.explanation}\n\n```\n{snip.command}\n```{others}"
    )
    state.pending_probe = True
    state.phase = Phase.probing_hardware
    return state


def probe_parse(state: AgentState) -> AgentState:
    """Parse pasted probe output into requirements.hardware."""
    hw = hw_tools.parse_probe_output(last_user_message(state))
    state.pending_probe = False
    req_hw = state.requirements.hardware
    if req_hw is None:
        state.requirements.hardware = hw
    else:
        merged = req_hw.model_dump()
        merged.update({k: v for k, v in hw.model_dump().items() if v is not None})
        state.requirements.hardware = type(hw)(**merged)
    found = state.requirements.hardware
    if found.usable_memory_gb:
        state.notices.append(
            f"Detected: {found.ram_gb:.0f}GB RAM"
            + (f", {found.gpu}" if found.gpu else "")
            + (f", {found.vram_gb:.0f}GB VRAM" if found.vram_gb else ""))
    return state
