"""Cost estimation: turn usage descriptions into monthly token volumes and USD.

Token assumptions mirror kb/guides/pricing-mental-models.md so the agent's
narration and the numbers always agree.
"""

from whichmodel.schemas import ModelRow

# (input_tokens, output_tokens) per month by usage level.
USAGE_TOKENS_PER_MONTH: dict[str, tuple[int, int]] = {
    # a few short chats a day
    "light": (600_000, 300_000),
    # steady daily use, ~1 hour a day
    "moderate": (6_000_000, 2_500_000),
    # several hours daily, coding/agents with long prompts
    "heavy": (45_000_000, 15_000_000),
}
DEFAULT_USAGE = "moderate"


def estimate_monthly_usd(model: ModelRow, usage_level: str | None) -> float | None:
    """Monthly API cost in USD for a usage level; 0 for free, None if unpriced."""
    if model.is_free:
        return 0.0
    if model.prompt_usd_per_m is None or model.completion_usd_per_m is None:
        return None
    tokens_in, tokens_out = USAGE_TOKENS_PER_MONTH.get(
        usage_level or DEFAULT_USAGE, USAGE_TOKENS_PER_MONTH[DEFAULT_USAGE]
    )
    cost = (tokens_in / 1e6) * model.prompt_usd_per_m + (
        tokens_out / 1e6
    ) * model.completion_usd_per_m
    return round(cost, 2)


def usd_to_inr(usd: float | None, rate: float) -> float | None:
    """Convert USD to INR for display; None passes through."""
    return None if usd is None else round(usd * rate)


def basis_text(usage_level: str | None) -> str:
    """One-line, honest explanation of how monthly estimates are computed."""
    level = usage_level or DEFAULT_USAGE
    tokens_in, tokens_out = USAGE_TOKENS_PER_MONTH.get(level, USAGE_TOKENS_PER_MONTH[
        DEFAULT_USAGE])
    return (f"Monthly estimates assume {level} use, about {tokens_in / 1e6:.1f}M input + "
            f"{tokens_out / 1e6:.1f}M output tokens per month, multiplied by each model's "
            "per-million-token prices. Cached-input discounts are not modeled, so real "
            "bills often come in lower.")
