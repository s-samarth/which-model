---
category: benchmark
tags: [aider, coding, polyglot, editing, pair-programming]
updated: 2026-07-04
---

# Benchmark: Aider Polyglot

## What it measures
Whether a model can correctly edit existing code across several languages (C++, Go, Java, JavaScript, Python, Rust) using the Aider pair-programming tool's edit formats. 225 hard Exercism exercises. It rewards precise diff-following as much as raw coding skill, which mirrors real assisted-coding workflows. Not in our catalog data; livebench_coding is the in-catalog proxy.

## How to read the score
Percentage of exercises passing tests after at most two attempts.
- 80%+: excellent daily-driver coding assistants. <!-- VERIFY current top scores -->
- 50-80%: solid for routine edits.
- Under 40%: expect malformed edits and retries.

## Caveats
- Sensitive to edit-format compliance: a smart model that formats diffs badly scores low, which is informative for tool use but unfair as a pure intelligence measure.
- Exercise-sized problems, not repo-scale work; combine with agentic benchmarks for the full picture.
- Costs per run are published alongside scores; check them, some high scorers burn enormous token budgets.
