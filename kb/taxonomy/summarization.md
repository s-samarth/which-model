---
category: taxonomy
tags: [summarization, summary, tldr, meeting-notes, condensing]
updated: 2026-07-04
---

# Task: Summarization

## What it demands
Compressing long inputs while preserving key facts. The binding constraint is usually context length (the whole document must fit), then faithfulness. Reasoning depth needed is moderate. Cheap fast models often summarize nearly as well as frontier ones for routine material; quality gaps show on dense technical or legal text.

## Which benchmarks predict quality
- livebench_if includes an explicit summarize task, best direct signal in our catalog.
- livebench_language for comprehension of tricky prose.

## Typical model tier
- Meeting notes, articles, emails: budget tier, prioritize price per token since inputs are long.
- Legal, scientific, financial documents: mid to frontier tier for precision.
- Local: 8B+ models summarize well; make sure the context window fits your documents.

## Example user phrasings
- "summarize legal PDFs", "TLDR long reports"
- "turn meeting transcripts into notes", "condense research papers"
- "weekly digest of long email threads"
