---
category: benchmark
tags: [swe-bench, coding, agentic, software-engineering, github]
updated: 2026-07-04
---

# Benchmark: SWE-bench (Verified)

## What it measures
Whether a model, running as an agent, can resolve real GitHub issues from popular Python repos: read the codebase, write a patch, pass the repo's tests. SWE-bench Verified is the human-validated 500-issue subset. It is the most cited agentic coding benchmark. Not in our catalog data; use livebench_agentic_coding as the in-catalog equivalent.

## How to read the score
Percentage of issues resolved.
- The top of the leaderboard is compressed above 85-90% as of mid 2026, so small gaps there mean little. <!-- VERIFY current top scores -->
- 50-70% was frontier as recently as 2025; models in this band are still very capable pair programmers.
- Under 40%: struggles with multi-file real-repo work.

## Caveats
- Scores depend heavily on the agent scaffold (retries, tooling), not just the model. Compare only same-scaffold numbers.
- Python-only and drawn from popular repos, so it may overstate quality on other languages or private codebases.
- A 2026 Berkeley RDI study showed agent benchmarks like this can be exploited by loopholes in the harness; treat leaderboard extremes skeptically.
- Near saturation at the top: differences between the best models are better judged on newer, harder sets (SWE-bench-Live, Terminal-Bench).
