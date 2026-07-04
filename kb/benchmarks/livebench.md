---
category: benchmark
tags: [livebench, coding, reasoning, math, language, data-analysis, instruction-following, agentic-coding]
updated: 2026-07-04
---

# Benchmark: LiveBench

## What it measures
A contamination-limited benchmark that releases new questions every few months, scored automatically against ground truth (no LLM judge). Categories: Reasoning, Coding, Agentic Coding, Mathematics, Data Analysis, Language, and Instruction Following (IF). This is the primary benchmark family in our catalog, stored as livebench_reasoning, livebench_coding, livebench_agentic_coding, livebench_mathematics, livebench_data_analysis, livebench_language, livebench_if, and livebench_global (mean of category means).

## How to read the score
Scores are 0-100 per category. Our catalog keeps the best score across a model's run variants (thinking modes, effort levels), so read it as "this model at its best settings".
- 70+: frontier performance in that category.
- 55-70: strong, fine for most real work.
- 40-55: capable mid tier, expect misses on hard problems.
- Under 40: weak in that category, only acceptable for casual use or tight budgets.

## Caveats
- Fresh question sets limit contamination but do not eliminate benchmark tuning by labs.
- A 2-3 point gap is noise; only treat differences above roughly 5 points as meaningful.
- Small local models are underrepresented; a missing score means unmeasured, not bad.
- Category scores matter more than the global average: a coding-focused user should ignore a model's math score.
