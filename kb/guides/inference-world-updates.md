---
category: guide
tags: [inference, news, trends, whats-new, speculative-decoding, quantization, hosting, 2026]
updated: 2026-07-06
---

# Guide: What Is Changing in the Inference World

This doc exists to be refreshed. It tracks the moving parts of how models get served, so recommendations reflect the current landscape rather than last year's. Review monthly alongside the VERIFY sweep.

## Current state of play (mid-2026)
- **Small models got good.** 4-9B open models now hold conversations and follow instructions well enough to power narrow products; the interesting question moved from "can it" to "how cheap and how fast".
- **Prices keep collapsing.** Per-token costs for open models on managed endpoints have fallen steadily; assume any price memorized more than a quarter ago is wrong, in the user's favor. <!-- VERIFY current representative prices -->
- **Speed as a product**: dedicated inference hardware (Groq-class LPUs, Cerebras) and aggressive speculative decoding make some hosts feel instant; latency now differentiates providers as much as price.
- **Prefix caching went mainstream.** vLLM and SGLang cache shared prompt prefixes, making agent workloads (same system prompt every call) dramatically cheaper and faster; providers increasingly discount cached input tokens.
- **Quantization matured.** FP8 on server GPUs and 4-bit GGUF locally are default choices, not exotic tricks; quality loss talk has shifted from "if" to "measured on which task".
- **Thinking budgets everywhere.** Most current models expose a reasoning-effort dial; serving cost now depends on how much hidden thinking a task triggers, which matters more than sticker price for reasoning-heavy work.
- **MoE for the memory-rich.** Sparse models (tens of billions total, few active) became the way to get big-model knowledge at small-model speed on unified-memory machines.

## What to watch next
- OpenAI-compatible becoming a true universal standard across hyperscalers (it is close). <!-- VERIFY -->
- On-device NPUs (phone and laptop) taking the smallest models out of the GPU conversation entirely.
- Serverless GPU cold starts approaching negligibility via snapshot/restore tricks, which would make scale-to-zero the default for small products.

## How to use this doc in answers
When a user asks "what is new" or when advising on hosting, cite the pattern (prices fall, caching matters, speed differentiates) and check live sources for the specific number of the week.
