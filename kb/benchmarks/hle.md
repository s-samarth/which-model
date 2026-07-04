---
category: benchmark
tags: [hle, humanitys-last-exam, reasoning, frontier, hard, knowledge]
updated: 2026-07-05
---

# Benchmark: Humanity's Last Exam (HLE)

## What it measures
Thousands of expert-written questions across dozens of academic fields, deliberately built to be unsolvable by memorization and to stay hard as older exams (MMLU, GPQA) saturate. The de facto "how smart is the frontier" number in 2025-2026. Not in our catalog data; used as background when users ask about frontier reasoning.

## How to read the score
Percentage correct, usually with web tools disabled.
- Frontier reasoning models score in the tens of percent, not near 100; mid-2026 leaders sit well under half. <!-- VERIFY current top scores -->
- A model scoring in single digits is not "dumb"; HLE questions are brutally specialized.
- Tool-augmented (search-enabled) runs score far higher; check which mode a number comes from.

## Caveats
- Measures esoteric expert knowledge and careful reasoning, not helpfulness, speed, or coding.
- Almost irrelevant for chatbots, summarization, translation, or everyday coding choices.
- Contamination-resistant by construction but not immune to future leakage; the maintainers rotate held-out sets. <!-- VERIFY -->
- If a user quotes an HLE number as the reason to pick a model for a shop chatbot, gently redirect to task-relevant measures.
