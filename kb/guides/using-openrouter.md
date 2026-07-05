---
category: guide
tags: [openrouter, aggregator, routing, api, credits, fallback, byok]
updated: 2026-07-06
---

# Guide: Using OpenRouter Well

## What it is
A single OpenAI-compatible API in front of hundreds of models from every major lab and open-model host. One key, one bill, per-token prices that match or closely track going direct, with a small platform fee on credits. <!-- VERIFY current fee structure -->

## Why beginners should start here
- Try any model by changing one string ("openai/gpt-5.4" to "deepseek/deepseek-v4-flash") instead of making new accounts.
- One prepaid balance caps total spend across all providers.
- Free variants of some open models exist for prototyping (heavily rate limited).

## Setup in three steps
1. Get a key (see the API keys guide).
2. Point any OpenAI SDK at base URL https://openrouter.ai/api/v1 with the key.
3. Pick model ids from openrouter.ai/models, where context length, price per million tokens in and out, and supported features (tools, images) are listed per model.

## Features worth knowing
- Fallback routing: request a list of models and it fails over automatically if a provider is down.
- Provider preferences: pin or exclude specific underlying hosts (matters for privacy policies and latency region).
- BYOK: bring your own provider key and route through OpenRouter for the unified interface. <!-- VERIFY current BYOK terms -->
- Usage dashboard shows spend per model, useful for verifying cost estimates.

## Caveats
- A thin extra hop of latency versus going direct (usually negligible for chat).
- Data flows through OpenRouter to the underlying provider; check both privacy policies for sensitive workloads.
- Not every provider feature lands immediately (fine-grained caching controls, some beta features arrive on direct APIs first).
