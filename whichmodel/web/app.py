"""FastAPI application: POST /chat, POST /reset, GET /health, static frontend.

A signed-enough random cookie keys the server-side session. A tool or LLM
failure never crashes the conversation; the user gets a clean degraded reply.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, FastAPI, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from whichmodel.agent import AgentDeps, AgentState, build_graph
from whichmodel.agent.llm import OpenAICompatClient
from whichmodel.config import get_settings
from whichmodel.logging_setup import setup_logging
from whichmodel.retrieval import build_retriever, load_kb
from whichmodel.sessions import InMemorySessionStore
from whichmodel.tools import catalog

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    reply: str
    phase: str
    recommendation: dict | None = None
    notices: list[str] = []
    data_age: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    conn = catalog.connect(settings.db_path)
    deps = AgentDeps(
        llm=OpenAICompatClient(settings),
        retriever=build_retriever(load_kb(settings.kb_dir), settings),
        conn=conn,
        db_path=str(settings.db_path),
        snippets_path=settings.snippets_path,
        usd_to_inr=settings.usd_to_inr,
    )
    app.state.deps = deps
    app.state.graph = build_graph(deps)
    app.state.sessions = InMemorySessionStore(ttl_s=settings.session_ttl_s)
    log.info("app ready: model=%s base_url=%s", settings.model_name, settings.openai_base_url)
    yield
    conn.close()


app = FastAPI(title="Which Model?", lifespan=lifespan)


def _session_id(cookie_value: str | None, response: Response) -> str:
    sid = cookie_value or uuid.uuid4().hex
    if cookie_value is None:
        response.set_cookie("wm_session", sid, httponly=True, samesite="lax")
    return sid


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, response: Response,
               wm_session: str | None = Cookie(default=None)) -> ChatResponse:
    from whichmodel.agent.graph import run_turn

    sid = _session_id(wm_session, response)
    store = app.state.sessions
    state = store.get(sid) or AgentState()
    deps = app.state.deps
    try:
        state = await run_in_threadpool(run_turn, app.state.graph, deps, state, req.message)
    except Exception:
        log.exception("turn failed")
        age = catalog.data_age(deps.conn)
        return ChatResponse(
            reply=("I hit a problem talking to my reasoning model just now. Your answers "
                   "are saved, please send that again in a moment. "
                   f"(Catalog data: refreshed {age}.)"),
            phase=state.phase, data_age=age)
    store.put(sid, state)
    return ChatResponse(
        reply=state.reply,
        phase=state.phase,
        recommendation=state.recommendation.model_dump() if state.recommendation else None,
        notices=[n for n in state.notices if not n.endswith("_failed")],
        data_age=catalog.data_age(deps.conn),
    )


@app.post("/reset")
async def reset(response: Response, wm_session: str | None = Cookie(default=None)) -> dict:
    if wm_session:
        app.state.sessions.delete(wm_session)
    return {"ok": True}


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.model_name,
        "data_age": catalog.data_age(app.state.deps.conn),
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
