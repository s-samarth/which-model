---
category: benchmark
tags: [arc-agi, arc, abstraction, reasoning, generalization, puzzles]
updated: 2026-07-05
---

# Benchmark: ARC-AGI-2

## What it measures
Visual grid puzzles that require inferring a novel rule from a few examples, designed so that pattern memorization does not help. Tests fluid intelligence and generalization to genuinely unseen problems, the thing most other benchmarks fail to isolate. Not in our catalog data.

## How to read the score
Percentage of held-out puzzles solved, with a cost-per-task axis published alongside.
- Ordinary humans solve most puzzles; models lag humans substantially on ARC-AGI-2, unlike almost every other benchmark. <!-- VERIFY current scores -->
- Cost matters: some high scores burn enormous compute per puzzle; the leaderboard's efficiency dimension is as informative as the score.

## Caveats
- Deliberately unlike real work: solving grid puzzles does not make a model better at writing emails or code.
- Best read as a research signal about reasoning progress, not a shopping criterion.
- Relevant to users only when their task involves novel structured reasoning with no examples to learn from, which is rare in practice.
