---
category: benchmark
tags: [terminal-bench, agentic, terminal, cli, devops, automation]
updated: 2026-07-04
---

# Benchmark: Terminal-Bench

## What it measures
Whether an agent can complete real tasks in a Unix terminal: build projects, wrangle data, configure servers, debug failing systems. Each task runs in a container and is checked by tests. Terminal-Bench 2.0 (late 2025) is the current version. The closest in-catalog signal is livebench_agentic_coding.

## How to read the score
Percentage of tasks completed.
- Frontier agents score in the 45-65% band on 2.0 as of mid 2026, so even the best fail often. <!-- VERIFY current scores -->
- 20-40%: usable for supervised terminal work, not autonomy.
- Harness matters: the same model with a better agent wrapper can gain 10+ points.

## Caveats
- Scores mix model quality with scaffold quality; compare same-harness rows only.
- The 2026 Berkeley RDI exploit study flagged agent benchmarks, including this one, as gameable through harness loopholes.
- Long tasks are expensive; a run can cost dollars per task, so cost-per-solve differs wildly between models.
- Low absolute scores are normal here; do not read 50% as "bad" the way you would on a knowledge quiz.
