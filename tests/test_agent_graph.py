"""Graph logic tests with a mocked LLM. No running model required."""

from pathlib import Path

import pytest

from tests.mocks import queue
from whichmodel.agent.graph import AgentDeps, build_graph, run_turn
from whichmodel.agent.state import AgentState, Phase
from whichmodel.retrieval import BM25Retriever, load_kb
from whichmodel.tools import catalog

ROOT = Path(__file__).parent.parent
SEED_DB = ROOT / "data" / "models.db"
SNIPPETS = ROOT / "data" / "hardware_snippets.yaml"


@pytest.fixture(scope="module")
def retriever():
    return BM25Retriever(load_kb(ROOT / "kb"))


def make_deps(llm, retriever) -> AgentDeps:
    return AgentDeps(llm=llm, retriever=retriever, conn=catalog.connect(SEED_DB),
                     db_path=str(SEED_DB), snippets_path=SNIPPETS)


def turn(deps, state, msg):
    app = build_graph(deps)
    return run_turn(app, deps, state, msg)


class TestElicitation:
    def test_vague_message_yields_clarifying_questions(self, retriever):
        llm = queue(
            {"task_category": "chat_assistant", "task_description": "chatbot for shop"},
            {"questions": ["Would you rather run it on your own computer, or use a "
                           "cloud service?", "Any monthly budget in mind?"]},
        )
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "I want a chatbot for my shop")
        assert state.phase == Phase.eliciting
        assert "?" in state.reply
        assert state.requirements.task_category == "chat_assistant"
        assert state.recommendation is None

    def test_malformed_llm_json_falls_back_to_canned_question(self, retriever):
        llm = queue("not json at all", "still not json", "nope", "no")
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "I want something that helps me")
        assert state.phase == Phase.eliciting
        assert state.reply, "must still ask something"
        assert "?" in state.reply

    def test_kb_context_grounds_clarifying_turn(self, retriever):
        llm = queue(
            {"task_category": "summarization", "task_description": "summarize legal PDFs"},
            {"questions": ["Are your documents usually under 50 pages?"]},
        )
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "I want to summarize legal PDFs")
        assert any("taxonomy/summarization" in c for c in state.kb_context)


class TestHardwareProbe:
    def test_local_deployment_triggers_canned_snippet(self, retriever):
        llm = queue({"task_category": "chat_assistant", "deployment": "local"})
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "offline chatbot on my macbook please")
        assert state.phase == Phase.probing_hardware
        assert state.pending_probe
        assert "system_profiler" in state.reply  # from the library, not generated

    def test_probe_output_parsed_and_recommendation_follows(self, retriever):
        llm = queue(
            {"task_category": "chat_assistant", "deployment": "local"},
            "Given your 16GB Mac, a small local model is the right call.",
        )
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "offline chatbot on my mac")
        state = turn(deps, state, "Chip: Apple M2\n      Memory: 16 GB\n15.5")
        assert state.requirements.hardware.ram_gb == 16
        assert state.phase == Phase.done
        assert state.candidates, "answer must be grounded in candidates"
        assert "16GB Mac" in state.reply


class TestRecommendation:
    def test_impatient_user_gets_recommendation_first_turn(self, retriever):
        llm = queue({"task_category": None}, "My pick given what I know so far...")
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "just tell me the best model")
        assert state.phase == Phase.done
        assert state.reply
        assert state.candidates

    def test_facts_block_carries_grounded_numbers(self, retriever):
        """The prompt's FACTS block must contain real scores and prices so the
        LLM has every number it may use."""
        llm = queue(
            {"task_category": "coding", "deployment": "api", "budget_amount": 100,
             "budget_currency": "usd", "usage_level": "moderate",
             "wants_recommendation_now": True},
            "Grounded answer citing agentic coding scores.",
        )
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "coding assistant, $100/mo, cloud, just pick")
        assert state.phase == Phase.done
        system = llm.calls[-1]["system"]
        assert "FACTS" in system
        assert "agentic coding" in system
        top = state.candidates[0]
        assert top.id in system
        assert f"{top.scores['livebench_agentic_coding']:.0f}/100" in system

    def test_foreign_model_mention_gets_visible_correction(self, retriever):
        llm = queue(
            {"task_category": "coding", "deployment": "api",
             "wants_recommendation_now": True},
            "You should really use Claude 3 Haiku for this.",  # not a candidate
        )
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "coding model, cloud, just pick one")
        assert "Correction:" in state.reply
        assert "claude-3-haiku" in state.reply

    def test_recommendation_by_turn_six_regardless(self, retriever):
        llm = queue({})  # extraction never learns anything
        deps = make_deps(llm, retriever)
        state = AgentState()
        for i in range(6):
            state = turn(deps, state, f"hmm I am not sure ({i})")
            if state.phase == Phase.done:
                break
        assert state.phase == Phase.done
        assert state.reply, "must still answer with assumptions stated"


class TestSummarization:
    def test_window_folds_into_summary(self, retriever):
        from whichmodel.agent.graph import maybe_summarize
        llm = queue("User wants a coding model, budget $20.")
        state = AgentState(messages=[
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
            for i in range(12)
        ])
        state = maybe_summarize(state, llm)
        assert len(state.messages) == 6
        assert "coding" in state.summary


class TestFeedbackRegressions:
    """Bugs found in real user testing (screenshots, 2026-07-04)."""

    def test_recommend_now_not_sticky_after_done(self, retriever):
        """Follow-up after a recommendation must re-elicit, not replay."""
        llm = queue(
            {"task_category": "chat_assistant", "deployment": "api",
             "budget_amount": 20, "budget_currency": "usd",
             "wants_recommendation_now": True},
            {"top_pick_id": "X", "why_top": "x"},  # falls back deterministically
            # turn 2: user pivots to local; extraction updates deployment
            {"deployment": "local"},
        )
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "chatbot, cloud, $20, just pick one")
        assert state.phase == Phase.done
        state = turn(deps, state, "what if I want a local LLM hosted myself?")
        # must NOT short-circuit to another recommendation; hardware is unknown
        assert state.phase == Phase.probing_hardware
        assert state.recommendation is None

    def test_inr_budget_converted_deterministically(self, retriever):
        llm = queue({"budget_amount": 2000, "budget_currency": "inr"},
                    {"questions": ["What will you mainly use it for?"]})
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "my budget is 2000 rupees a month")
        assert state.requirements.budget_monthly_usd == round(2000 / 84.0, 2)

    def test_repeated_question_is_suppressed(self, retriever):
        q = "Will customers ask mostly simple questions, or complex problem-solving?"
        llm = queue(
            {"task_category": "chat_assistant"},
            {"questions": [q]},
            {},  # turn 2 extraction learns nothing
            {"questions": [q]},  # LLM tries to re-ask the exact same thing
        )
        deps = make_deps(llm, retriever)
        state = turn(deps, AgentState(), "customer service chatbot for my food business")
        assert q in state.asked_questions
        state = turn(deps, state, "honestly I am not sure about any of this")
        assert state.reply != q, "verbatim repeat must be suppressed"
