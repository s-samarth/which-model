---
category: taxonomy
tags: [chat, assistant, chatbot, customer-support, general]
updated: 2026-07-04
---

# Task: Chat / General Assistant

## What it demands
Conversational quality, tone control, safety, and broad general knowledge. Latency matters a lot (users notice replies slower than a few seconds). Context needs are modest (8k to 32k covers most chats). For customer-facing bots, consistency and instruction following beat raw intelligence.

## Which benchmarks predict quality
- livebench_global is the best single ranking signal in our catalog for general assistants.
- livebench_if (instruction following) matters for bots that must follow a persona or policy.
- Arena Elo reflects human preference for chat style but is not in our catalog data.

## Typical model tier
- Personal assistant or shop chatbot: mid tier is plenty, small fast models keep costs near zero.
- High-stakes customer support: mid to frontier tier, prioritize instruction following.
- Local: 4B to 12B models handle everyday chat well on consumer hardware.

## Example user phrasings
- "a chatbot for my shop", "customer support bot for my website"
- "just a general assistant like ChatGPT", "something to answer questions"
- "an AI to talk to my customers in Hindi"
