"""Local-inference planning: quantization options, memory fit, speed estimates,
and serving-stack guidance. Pure functions over catalog data and heuristics
that mirror kb/guides/local-inference.md, so numbers and prose agree."""

import sqlite3

from whichmodel.schemas import Hardware, ModelRow

MEMORY_OVERHEAD = 1.2  # KV cache and runtime buffers on top of weight file size

# Rough throughput constants: tok/s ~= RATE / effective_param_b (q4).
# Tiers mirror kb/guides/local-inference.md speed expectations.
_TIER_RATES = {
    "apple": 220.0,  # M-series unified memory
    "nvidia": 420.0,  # mid/high consumer GPU with the model fully in VRAM
    "cpu": 35.0,  # no usable GPU
}


def quant_options(conn: sqlite3.Connection, param_b: float,
                  usable_memory_gb: float | None) -> list[dict]:
    """Quantization choices with memory footprints and fit flags, from the DB."""
    rows = conn.execute(
        "SELECT quant, bytes_per_param, quality_note FROM quant_factors "
        "ORDER BY bytes_per_param").fetchall()
    out = []
    for r in rows:
        mem = round(param_b * r["bytes_per_param"] * MEMORY_OVERHEAD, 1)
        out.append({
            "quant": r["quant"],
            "memory_gb": mem,
            "fits": (usable_memory_gb is not None and mem <= usable_memory_gb)
            if usable_memory_gb else None,
            "note": r["quality_note"],
        })
    return out


def _tier(hw: Hardware | None) -> str:
    if hw is None:
        return "cpu"
    gpu = (hw.gpu or "").lower()
    if "apple" in gpu or (hw.os == "macos" and hw.ram_gb):
        return "apple"
    if hw.vram_gb and hw.vram_gb >= 8:
        return "nvidia"
    return "cpu"


def est_tok_s(param_b: float, active_param_b: float | None,
              hw: Hardware | None) -> str:
    """Ballpark generation speed range like '15-30 tok/s'. MoE models run at
    the speed of their active parameters, not their total size."""
    effective = active_param_b or param_b
    rate = _TIER_RATES[_tier(hw)]
    mid = rate / max(effective, 0.5)
    lo, hi = max(1, round(mid * 0.6)), round(mid * 1.3)
    return f"{lo}-{hi} tok/s"


def serving_stack(usage_level: str | None, task: str | None) -> str:
    """Which inference stack to suggest for a local deployment."""
    if usage_level == "heavy" or task == "chat_assistant":
        return ("For a bot serving multiple people at once, run vLLM or SGLang on a "
                "Linux GPU server (they batch concurrent requests). For trying it out "
                "on your own machine first, Ollama or LM Studio is enough.")
    return ("Ollama (command line, simplest) or LM Studio (graphical) are the right "
            "tools for personal use. vLLM or SGLang only matter when many users hit "
            "the model at once.")


def local_setup(conn: sqlite3.Connection, m: ModelRow, hw: Hardware | None,
                usage_level: str | None, task: str | None) -> dict | None:
    """Everything a user needs to plan running this model locally."""
    if not m.param_b:
        return None
    quants = quant_options(conn, m.param_b, hw.usable_memory_gb if hw else None)
    setup = {
        "param_b": m.param_b,
        "quants": quants,
        "est_speed": est_tok_s(m.param_b, m.active_param_b, hw),
        "serving": serving_stack(usage_level, task),
        "moe_note": None,
    }
    if m.active_param_b:
        setup["moe_note"] = (
            f"This is a mixture-of-experts model: {m.param_b:.0f}B parameters total "
            f"but only ~{m.active_param_b:.0f}B active per token, so it needs the "
            f"memory of a {m.param_b:.0f}B model while running at the speed of a "
            f"{m.active_param_b:.0f}B one.")
    return setup
