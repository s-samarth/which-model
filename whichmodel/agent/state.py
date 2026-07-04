"""Typed graph state and the structured-output schemas the LLM fills."""

from enum import StrEnum

from pydantic import BaseModel, Field

from whichmodel.schemas import (
    ContextNeed,
    Deployment,
    Hardware,
    Level,
    ModelRow,
    Recommendation,
    Requirements,
    TaskCategory,
)


class Phase(StrEnum):
    eliciting = "eliciting"
    probing_hardware = "probing_hardware"
    retrieving = "retrieving"
    recommending = "recommending"
    done = "done"


class AgentState(BaseModel):
    """Full graph state for one session, carried across turns."""

    messages: list[dict] = Field(default_factory=list)  # {"role", "content"}
    summary: str = ""  # compact summary of messages dropped from the window
    requirements: Requirements = Field(default_factory=Requirements)
    kb_context: list[str] = Field(default_factory=list)  # retrieved chunks, this turn
    candidates: list[ModelRow] = Field(default_factory=list)
    phase: Phase = Phase.eliciting
    user_turns: int = 0
    recommend_now: bool = False  # user asked to skip ahead
    pending_probe: bool = False  # we asked the user to run a probe snippet
    # Per-turn outputs consumed by the web layer:
    reply: str = ""
    recommendation: Recommendation | None = None
    notices: list[str] = Field(default_factory=list)  # degraded-mode messages


class RequirementsPatch(BaseModel):
    """What the extraction LLM may update this turn. All fields optional."""

    task_category: TaskCategory | None = None
    task_description: str | None = None
    deployment: Deployment | None = None
    budget_monthly_usd: float | None = None
    hardware: Hardware | None = None
    context_need: ContextNeed | None = None
    latency_need: Level | None = None
    privacy_need: Level | None = None
    language_needs: str | None = None
    usage_level: str | None = None
    wants_recommendation_now: bool = False


def merge_patch(req: Requirements, patch: RequirementsPatch) -> Requirements:
    """Non-None patch fields win; hardware merges field-wise."""
    data = req.model_dump()
    for field, value in patch.model_dump(exclude={"wants_recommendation_now"}).items():
        if value is None:
            continue
        if field == "hardware" and req.hardware is not None:
            merged = req.hardware.model_dump()
            merged.update({k: v for k, v in value.items() if v is not None})
            data["hardware"] = merged
        else:
            data[field] = value
    return Requirements(**data)


class PickPlan(BaseModel):
    """The recommend LLM's only job: choose candidate ids and explain why."""

    top_pick_id: str
    runner_up_id: str | None = None
    budget_pick_id: str | None = None
    why_top: str
    why_runner_up: str | None = None
    why_budget: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class ClarifyingQuestions(BaseModel):
    """Next questions to ask (1-2), grounded in KB context."""

    questions: list[str] = Field(min_length=1, max_length=2)
