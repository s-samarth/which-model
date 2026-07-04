"""Web layer tests: endpoints, session cookie persistence, degraded mode."""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.mocks import queue
from whichmodel.agent.graph import AgentDeps, build_graph
from whichmodel.retrieval import BM25Retriever, load_kb
from whichmodel.sessions import InMemorySessionStore
from whichmodel.tools import catalog
from whichmodel.web.app import app

ROOT = Path(__file__).parent.parent


def make_client(llm) -> TestClient:
    client = TestClient(app)
    client.__enter__()  # run lifespan with real settings
    deps = AgentDeps(
        llm=llm,
        retriever=BM25Retriever(load_kb(ROOT / "kb")),
        conn=catalog.connect(ROOT / "data" / "models.db"),
        db_path=str(ROOT / "data" / "models.db"),
        snippets_path=ROOT / "data" / "hardware_snippets.yaml",
    )
    app.state.deps = deps
    app.state.graph = build_graph(deps)
    app.state.sessions = InMemorySessionStore(ttl_s=60)
    return client


class TestEndpoints:
    def test_health(self):
        with TestClient(app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"
            assert body["data_age"]

    def test_chat_sets_cookie_and_persists_session(self):
        llm = queue(
            {"task_category": "chat_assistant", "task_description": "shop bot"},
            {"questions": ["Cloud service or your own computer?"]},
            {"deployment": "api", "budget_monthly_usd": 10, "usage_level": "light",
             "wants_recommendation_now": True},
            {"top_pick_id": "WILL_FALLBACK", "why_top": "x"},
        )
        client = make_client(llm)
        try:
            r1 = client.post("/chat", json={"message": "I want a chatbot for my shop"})
            assert r1.status_code == 200
            assert "wm_session" in r1.cookies or client.cookies.get("wm_session")
            assert r1.json()["phase"] == "eliciting"

            r2 = client.post("/chat", json={"message": "cloud is fine, $10 a month, just pick"})
            body = r2.json()
            assert body["phase"] == "done"
            assert body["recommendation"] is not None
            assert body["recommendation"]["picks"]
            assert body["data_age"]
        finally:
            client.__exit__(None, None, None)

    def test_reset_clears_session(self):
        llm = queue({"task_category": "coding"}, {"questions": ["Budget?"]})
        client = make_client(llm)
        try:
            client.post("/chat", json={"message": "coding help"})
            sid = client.cookies.get("wm_session")
            assert app.state.sessions.get(sid) is not None
            client.post("/reset")
            assert app.state.sessions.get(sid) is None
        finally:
            client.__exit__(None, None, None)

    def test_llm_outage_degrades_cleanly(self):
        class ExplodingLLM:
            def complete(self, *a, **k):
                raise ConnectionError("ollama down")

        client = make_client(ExplodingLLM())
        try:
            resp = client.post("/chat", json={"message": "hello"})
            assert resp.status_code == 200
            body = resp.json()
            assert "refreshed" in body["reply"]  # data-age disclosure
        finally:
            client.__exit__(None, None, None)

    def test_empty_message_rejected(self):
        with TestClient(app) as client:
            assert client.post("/chat", json={"message": ""}).status_code == 422


class TestSessionStore:
    def test_ttl_expiry(self, monkeypatch):
        import time as time_mod
        store = InMemorySessionStore(ttl_s=10)
        from whichmodel.agent.state import AgentState
        t = [1000.0]
        monkeypatch.setattr(time_mod, "monotonic", lambda: t[0])
        store.put("a", AgentState())
        assert store.get("a") is not None
        t[0] += 11
        assert store.get("a") is None
