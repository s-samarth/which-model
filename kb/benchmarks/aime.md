---
category: benchmark
tags: [aime, math, mathematics, competition, reasoning]
updated: 2026-07-04
---

# Benchmark: AIME

## What it measures
The American Invitational Mathematics Examination, a high-school olympiad qualifier with 15 hard integer-answer problems per exam. Labs report the percentage solved, usually on the most recent year's exam to limit contamination. Tests multi-step mathematical reasoning. In our catalog, livebench_mathematics covers similar ground with fresher questions.

## How to read the score
- 90%+: reasoning models with long thinking budgets essentially solve the exam. Saturated at the top as of 2026. <!-- VERIFY -->
- 50-90%: strong math reasoning.
- Under 30%: weak formal math, still fine for everyday arithmetic and estimates.

## Caveats
- Saturation: top models cluster near 100% on older exams, making AIME useless for separating frontier models. Newer variants (HMMT, olympiad-level sets) took over that role.
- Answers are single integers, so lucky guesses and memorized solutions inflate scores.
- Math scores transfer poorly to general tasks. High AIME does not mean better emails, code, or chat.
- Thinking-mode results consume far more tokens, so the quoted score may cost 10-50x more per query than the default mode.
