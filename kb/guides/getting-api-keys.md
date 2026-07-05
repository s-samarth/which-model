---
category: guide
tags: [api-key, signup, openai, anthropic, google, openrouter, getting-started, account, billing]
updated: 2026-07-06
---

# Guide: Getting API Access, Step by Step

## The two-decision shortcut
Decision 1: one aggregator key or direct provider keys? For beginners and for anyone comparing models, OpenRouter (one key, hundreds of models, pay as you go) is the simplest start. Decision 2: prepaid credits or monthly billing? Prefer prepaid wherever offered; it caps your downside.

## OpenRouter (recommended first stop)
1. Sign in at openrouter.ai with Google or GitHub.
2. Buy credits (cards work internationally, small minimum). <!-- VERIFY current minimum and payment methods -->
3. Create a key under Keys. Use it with any OpenAI-compatible library by setting the base URL to https://openrouter.ai/api/v1.
4. Model names look like "anthropic/claude-sonnet-5"; prices per million tokens are on each model page.

## Direct providers
- OpenAI: platform.openai.com, add prepaid credits, create a key under API keys. Separate from a ChatGPT subscription; ChatGPT Plus does not include API usage.
- Anthropic: console.anthropic.com, similar flow. Claude Pro likewise does not include API usage.
- Google: aistudio.google.com gives a free-tier Gemini API key in about a minute; rate limits are tight but real. <!-- VERIFY free tier limits -->
- Fast open-model hosts (Fireworks, Together, Groq): sign up, grab a key, OpenAI-compatible endpoints; often the cheapest and fastest way to use open-weights models without owning a GPU. Some offer free starter credits. <!-- VERIFY current free credit offers -->

## Practical hygiene
- Never paste a key into client-side code or a shared notebook; treat it like a password.
- Set a monthly spend limit or use prepaid credits before the first real workload.
- Expect a cold-start rate limit tier that rises after some spend history.
- Keys work from India and most countries; billing is card-based, UPI generally not accepted directly. <!-- VERIFY -->
