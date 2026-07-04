---
category: taxonomy
tags: [image, vision, multimodal, photos, screenshots, ocr, charts]
updated: 2026-07-04
---

# Task: Image Understanding

## What it demands
Interpreting images: photos, screenshots, charts, scanned documents, handwriting. The model must accept image input (check the input_modalities flag in our catalog, only some models do). OCR-heavy work (receipts, forms) and chart reading are different skills from natural-photo description. Latency and cost per image vary widely.

## Which benchmarks predict quality
- Our catalog does not ingest vision benchmark scores yet. Rank vision-capable models by livebench_global as a general quality proxy, then filter by image input support.
- MMMU is the standard vision benchmark to read externally (see the MMMU explainer).

## Typical model tier
- Casual photo questions: mid tier vision models are fine.
- Document OCR pipelines, chart analysis: frontier vision models are noticeably better.
- Local vision models exist (Gemma 3 line, Qwen VL line) but lag API models on hard OCR. <!-- VERIFY current local vision model quality -->

## Example user phrasings
- "read receipts and extract totals", "describe photos for alt text"
- "answer questions about screenshots", "analyze charts in reports"
- "digitize handwritten forms"
