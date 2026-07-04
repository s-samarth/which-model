---
category: benchmark
tags: [arena, elo, lmarena, human-preference, chat]
updated: 2026-07-04
---

# Benchmark: Arena Elo (LMArena)

## What it measures
Human preference. Users chat with two anonymous models and vote for the better answer; votes feed an Elo-style rating. It captures style, helpfulness, and formatting appeal for everyday prompts. Not in our catalog data; livebench_global plus livebench_if is the closest grounded substitute.

## How to read the score
Relative, not absolute. A 50-point Elo gap means the higher model wins about 57% of head-to-head votes; 100 points is about 64%.
- Ratings shift as new models arrive; only rank order within a snapshot is meaningful.
- Category leaderboards (coding, hard prompts, style-controlled) are more informative than the overall board.

## Caveats
- Measures what impresses a voter in one reading: confident, long, well-formatted answers win votes even when subtly wrong.
- Style-control adjustments help but do not remove the bias.
- Labs optimize for it heavily. A high Arena rank with mediocre task benchmarks suggests a model tuned to please rather than perform.
- Voters skew toward tech-savvy English speakers, so it may not reflect your users.
