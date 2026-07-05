---
category: guide
tags: [benchmarks, scores, evaluation, which-benchmark, trust, task, leaderboard, compare]
updated: 2026-07-05
---

# Guide: Which Benchmark Matters for Which Task

No single number ranks models. The right question is "which measurement predicts MY task".

## Task to benchmark map
- Coding day to day: LiveBench agentic coding (multi-step repo work) first, Aider polyglot (reliable code editing) second, SWE-bench Verified for agentic repair, noting its top is compressed above 90%.
- Autonomous agents and tool use: Terminal-Bench 2.0 and LiveBench agentic coding; instruction following (LiveBench IF) predicts schema obedience.
- Chatbots and assistants: LiveBench global for a quality floor plus IF for staying on script; Arena Elo reflects style preference, not correctness.
- Documents, RAG, summarization: LiveBench language and data analysis; context window specs matter as much as any score.
- Deep reasoning and research: HLE and ARC-AGI-2 separate frontier models where older exams (GPQA, AIME) are saturated.
- Vision: MMMU (and MMMU-Pro) for charts and diagrams; test OCR on your own documents regardless.

## Reading any leaderboard honestly
1. Check the date and whether the benchmark refreshes; a static exam ages into a memorization test.
2. Gaps under ~5 points (or Elo under ~50) are noise; treat such models as tied.
3. Scaffold matters for agent benchmarks; compare only rows using the same harness.
4. Missing score means unmeasured, not bad; small local models are chronically under-measured.
5. Beware saturation: when the top ten crowd above 90%, the benchmark can no longer separate them.

## What our catalog carries
Fresh LiveBench category scores (the ranking signal in this app) plus prices and context windows. Other benchmarks above are explained in this knowledge base for context; when a score is not in the catalog it is discussed, never quoted as a number.
