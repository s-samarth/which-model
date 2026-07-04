---
category: benchmark
tags: [mmmu, vision, multimodal, image, charts, diagrams]
updated: 2026-07-04
---

# Benchmark: MMMU

## What it measures
Massive Multi-discipline Multimodal Understanding: college-level questions that require reading images (charts, diagrams, medical scans, art, engineering schematics) plus text. The standard measure of serious image understanding. Not in our catalog data; we filter models by image input support and rank by livebench_global instead.

## How to read the score
Percentage correct.
- 75%+: frontier vision models, reliable on charts and documents. <!-- VERIFY current top scores -->
- 55-75%: good general vision, spotty on dense diagrams.
- Under 50%: casual photo description only.
- Human expert baseline is around 88%.

## Caveats
- Academic exam images differ from real receipts, screenshots, and low-light photos; test on your own images.
- Multiple choice inflates scores.
- OCR quality (reading small text) is not isolated by MMMU; a model can score well yet misread totals on an invoice.
- MMMU-Pro is the harder successor and separates top models better.
