"""Shared typed state: requirements, hardware, catalog rows, recommendations.

These models are the agent's memory. The graph reads and writes them; the
frontend renders the Recommendation payload directly.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class TaskCategory(StrEnum):
    coding = "coding"
    chat_assistant = "chat_assistant"
    rag_doc_qa = "rag_doc_qa"
    summarization = "summarization"
    agentic_tool_use = "agentic_tool_use"
    image_understanding = "image_understanding"
    creative_writing = "creative_writing"
    web_search_heavy = "web_search_heavy"
    translation = "translation"
    other = "other"


class Deployment(StrEnum):
    local = "local"
    api = "api"
    either = "either"


class Level(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class ContextNeed(StrEnum):
    short = "short"  # up to ~16k tokens
    medium = "medium"  # up to ~32k
    long = "long"  # 128k+


class Hardware(BaseModel):
    ram_gb: float | None = None
    gpu: str | None = None
    vram_gb: float | None = None
    os: str | None = None  # macos | linux | windows

    @property
    def usable_memory_gb(self) -> float | None:
        """Memory available for model weights: VRAM, or ~70% of unified/system RAM."""
        if self.vram_gb:
            return self.vram_gb
        if self.ram_gb:
            return round(self.ram_gb * 0.7, 1)
        return None


class Requirements(BaseModel):
    """Structured extraction built up over the conversation."""

    task_category: TaskCategory | None = None
    task_description: str | None = None
    deployment: Deployment | None = None
    budget_monthly_usd: float | None = None
    hardware: Hardware | None = None
    context_need: ContextNeed | None = None
    latency_need: Level | None = None
    privacy_need: Level | None = None
    language_needs: str | None = None
    usage_level: str | None = None  # light | moderate | heavy
    open_questions: list[str] = Field(default_factory=list)

    def missing_required(self) -> list[str]:
        """Fields still needed before a solid recommendation for this task."""
        missing = []
        if self.task_category is None:
            missing.append("task_category")
        if self.deployment is None:
            missing.append("deployment")
        if self.budget_monthly_usd is None and self.deployment != Deployment.local:
            missing.append("budget_monthly_usd")
        if self.deployment == Deployment.local and (
            self.hardware is None or self.hardware.usable_memory_gb is None
        ):
            missing.append("hardware")
        return missing


class ModelRow(BaseModel):
    """One catalog model with its scores, as returned by the query tools."""

    id: str
    name: str
    provider: str = ""
    context_length: int | None = None
    input_modalities: str = "text"
    prompt_usd_per_m: float | None = None
    completion_usd_per_m: float | None = None
    is_free: bool = False
    available_api: bool = False
    available_local: bool = False
    open_weights: bool = False
    param_b: float | None = None
    active_param_b: float | None = None
    ollama_tag: str | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    rank_score: float = 0.0
    est_monthly_usd: float | None = None
    est_memory_gb: float | None = None  # q4 runtime footprint for local models


class Pick(BaseModel):
    """One recommended model in the final payload."""

    model_id: str
    name: str
    role: str  # top_pick | runner_up | budget_pick
    why: str
    mode: str = "api"  # api | local: how this user should run it
    get_started: str = ""  # concrete first step (signup or ollama pull)
    monthly_cost_usd: float | None = None
    monthly_cost_inr: float | None = None
    ollama_tag: str | None = None


class Recommendation(BaseModel):
    """Final structured payload rendered by the frontend."""

    picks: list[Pick]
    comparison: list[dict] = Field(default_factory=list)  # table rows for the UI
    assumptions: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    score_legend: str = ""  # what the score column means, in plain language
    cost_basis: str = ""  # how the monthly estimates were computed
    data_age: str = ""
