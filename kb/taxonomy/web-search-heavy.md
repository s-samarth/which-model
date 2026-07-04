---
category: taxonomy
tags: [web-search, research, current-events, news, deep-research]
updated: 2026-07-04
---

# Task: Web-Search-Heavy / Research

## What it demands
Fresh information beyond the model's training cutoff. The model itself cannot know today's news; what matters is whether the product or API around it does live search and how well the model synthesizes retrieved pages. Long context helps digest many sources. Citation reliability matters.

## Which benchmarks predict quality
- No catalog benchmark measures search quality directly. Use livebench_global for synthesis ability plus livebench_data_analysis for aggregating messy sources.
- Search quality depends mostly on the provider's search integration, not the base model.

## Typical model tier
- Quick lookups: any tier via a search-integrated product (Perplexity Sonar line is built for this).
- Deep research reports: frontier tier with a deep-research mode.
- Local models cannot search by themselves; pairing a local model with a search API is a DIY project, not a turnkey choice.

## Example user phrasings
- "keep me updated on my industry", "research competitors"
- "an AI that knows current news", "fact-check with sources"
- "market research reports"
