---
category: benchmark
tags: [livecodebench, coding, competitive-programming, contamination, algorithms]
updated: 2026-07-05
---

# Benchmark: LiveCodeBench Pro

## What it measures
Competitive-programming problems collected continuously from live contests (Codeforces and similar) AFTER models' training cutoffs, so solutions cannot have been memorized. Problems are tiered by difficulty; the hard tier still separates frontier models in 2026 where older coding exams saturate. Not in our catalog data; livebench_coding is the in-catalog cousin.

## How to read the score
Solve rate per difficulty tier (an Elo-style rating is also published).
- Read the hard tier for frontier comparisons; easy-tier numbers cluster near the top. <!-- VERIFY current scores -->
- Ratings map loosely to human competitive-programmer levels, which makes headlines but says little about day-to-day software work.

## Caveats
- Competitive programming is algorithm puzzles under time pressure: correlated with, but different from, real engineering (no legacy code, no ambiguity, no tooling).
- For "which model should write my app" questions, agentic benchmarks (LiveBench agentic coding, SWE-bench class) predict better.
- Freshness is the whole point; quote only post-cutoff windows.
