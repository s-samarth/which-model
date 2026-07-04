---
category: guide
tags: [pricing, cost, budget, tokens, subscription, api, estimate]
updated: 2026-07-04
---

# Guide: Pricing Mental Models

## Units
API pricing is USD per million tokens, separately for input (your prompt plus context) and output (the model's reply). Output is typically 3-8x pricier than input. Reasoning models bill their hidden thinking as output tokens, which can triple effective cost.

## Tokens per activity (typical)
- One chat exchange: 200-500 input + 150-400 output tokens.
- One coding question with a file pasted: 2k-6k input + 500-1,500 output.
- Summarizing a 20-page document: ~13k input + 500 output.
- One agent step: 1k-5k input (accumulating) + 200-800 output; a 10-step agent run: 30k-100k total.
- RAG answer over retrieved chunks: 3k-8k input + 300 output.

## From "hours a day" to monthly cost
Assume an active user sends 15-30 messages per hour of use.
- Light use (a few chats a day, ~30k tokens/day): under $1/month on budget models, $3-10 on frontier.
- A few hours daily (~300k tokens/day): $2-8/month budget tier, $30-120 frontier tier.
- Heavy agentic coding (millions of tokens/day): $100-1,000+/month; flat-rate coding subscriptions usually beat raw API here.

## Worked example
Customer chatbot, 100 conversations/day, 8 exchanges each, ~600 tokens per exchange round trip: about 0.5M tokens/day, 15M/month. At $0.30/$1.20 per M (budget tier): roughly $8/month. At $3/$15 (frontier): roughly $100/month. The tier decision changes cost 10x; whether the bot is noticeably better is the real question.

## Rules of thumb
- Input length dominates document and RAG workloads; output length dominates chat.
- Free tiers and free models exist for prototyping; they rate-limit hard.
- Local models cost electricity, roughly $0.01-0.05 per hour of active use on a laptop, but the hardware must already be adequate.
