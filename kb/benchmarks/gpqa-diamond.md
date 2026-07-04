---
category: benchmark
tags: [gpqa, reasoning, science, phd, knowledge]
updated: 2026-07-04
---

# Benchmark: GPQA Diamond

## What it measures
Graduate-level multiple-choice science questions (biology, physics, chemistry) written so that even skilled humans with web access struggle. Tests deep scientific reasoning and knowledge rather than everyday usefulness. Not in our catalog data; livebench_reasoning is the closest in-catalog signal.

## How to read the score
Percentage correct out of 198 questions. Random guessing scores 25%.
- 85%+: frontier reasoning models. <!-- VERIFY current top scores -->
- 60-85%: strong reasoners, more than enough for everyday analysis.
- 40-60%: mid tier.
- PhD-level human experts score around 65-70% in their own domain.

## Caveats
- Multiple choice inflates scores via elimination strategies.
- Only 198 questions, so a few points of difference is statistical noise.
- Measures esoteric science, not writing, coding, or helpfulness. A user who needs a shop chatbot should ignore GPQA entirely.
- Widely used in marketing precisely because it sounds impressive; check task-relevant benchmarks instead.
