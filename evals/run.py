"""Eval driver: play scenarios through the graph, assert, and report.

Usage:
    python -m evals.run              # live model from .env (Ollama by default)
    EVAL_MOCK=1 python -m evals.run  # heuristic mock, plumbing check only
"""

import os
import sys
import time
from pathlib import Path

import yaml

from evals import checks
from evals.mock_llm import HeuristicLLM
from whichmodel.agent.graph import AgentDeps, build_graph, run_turn
from whichmodel.agent.state import AgentState, Phase
from whichmodel.config import get_settings
from whichmodel.retrieval import BM25Retriever, load_kb
from whichmodel.tools import catalog

ROOT = Path(__file__).parent.parent
NUDGE = "just give me your best recommendation"
MAX_TURNS = 6
GATE_PASS = 12


def make_deps() -> AgentDeps:
    settings = get_settings()
    if os.environ.get("EVAL_MOCK"):
        llm = HeuristicLLM()
    else:
        from whichmodel.agent.llm import OpenAICompatClient
        llm = OpenAICompatClient(settings)
    return AgentDeps(
        llm=llm, retriever=BM25Retriever(load_kb(settings.kb_dir)),
        conn=catalog.connect(settings.db_path), db_path=str(settings.db_path),
        snippets_path=settings.snippets_path, usd_to_inr=settings.usd_to_inr)


def play(scenario: dict, deps: AgentDeps) -> AgentState:
    app = build_graph(deps)
    state = AgentState()
    queue = list(scenario.get("turns", []))
    probe = scenario.get("probe_output")
    while state.user_turns < MAX_TURNS:
        if state.phase == Phase.probing_hardware and probe:
            msg, probe = probe, None
        elif queue:
            msg = queue.pop(0)  # scripted turns continue even past a recommendation
        elif state.phase == Phase.done:
            break
        else:
            msg = NUDGE
        state = run_turn(app, deps, state, msg)
    return state


def evaluate(scenario: dict, state: AgentState, deps: AgentDeps) -> list[tuple[str, str]]:
    expect = scenario.get("expect") or {}
    results = [
        ("grounding", checks.check_grounding(state, deps.db_path, deps.conn)),
        ("recommendation", checks.check_reached_recommendation(
            state, MAX_TURNS, expect.get("done_within"))),
        ("fields", checks.check_fields(state, expect)),
        ("shell_safety", checks.check_shell_safety(state, deps.snippets_path)),
        ("schema", checks.check_schema(state)),
        ("expectations", checks.check_expectations(state, expect)),
    ]
    return [(name, err) for name, err in results if err]


def main() -> int:
    scenarios = yaml.safe_load((ROOT / "evals" / "scenarios.yaml").read_text())["scenarios"]
    deps = make_deps()
    mode = "MOCK" if os.environ.get("EVAL_MOCK") else "LIVE"
    print(f"Running {len(scenarios)} scenarios ({mode} llm)\n")
    passed, grounding_violations = 0, 0
    rows = []
    for sc in scenarios:
        t0 = time.time()
        try:
            state = play(sc, deps)
            failures = evaluate(sc, state, deps)
        except Exception as err:  # a crash is a failure, not an abort
            failures = [("crash", f"{type(err).__name__}: {err}")]
        took = time.time() - t0
        ok = not failures
        passed += ok
        grounding_violations += any(n == "grounding" for n, _ in failures)
        rows.append((sc["name"], ok, failures, took))
        detail = "" if ok else "  " + "; ".join(f"{n}: {e}" for n, e in failures)
        print(f"  {'PASS' if ok else 'FAIL'}  {sc['name']:<34} {took:5.1f}s{detail}")

    print(f"\n{passed}/{len(scenarios)} passed, {grounding_violations} grounding violations")
    gate_ok = passed >= GATE_PASS and grounding_violations == 0
    print("GATE:", "PASS" if gate_ok else "FAIL",
          f"(need >={GATE_PASS} passing and zero grounding violations)")
    return 0 if gate_ok else 1


if __name__ == "__main__":
    sys.exit(main())
