---
category: guide
tags: [context, context-window, tokens, long-context, documents]
updated: 2026-07-04
---

# Guide: Context Length

## What a token is
Roughly three quarters of an English word. 1,000 tokens is about 750 words. Hindi and other non-Latin scripts often use 2-4x more tokens per word.

## Concrete anchors
- 8k tokens: about 12 pages of text. One long email thread, a short story, a single source file. Enough for chat.
- 32k tokens: about 50 pages. A typical contract, a research paper plus notes, a small module of code (2-4k lines).
- 128k tokens: about 200 pages. A novel, an annual report, a mid-size codebase slice (15-20k lines), a long meeting transcript with room to answer.
- 256k-1M tokens: entire books, large codebases, weeks of chat history. Few tasks truly need this, and quality often degrades near the limit ("lost in the middle").

## Inferring the user's real need
- "Chatbot", "assistant", "write emails": short (8k-16k is plenty).
- "Summarize documents/PDFs/meetings", "single contracts": medium (32k covers most single documents).
- "My whole codebase", "book manuscript", "hundreds of pages", "long legal discovery": long (128k+).
- RAG systems retrieve chunks, so the model usually sees 4k-16k of retrieved text per question; the store holds the rest. Users who say "search all my documents" often need RAG, not a giant window.

## Cost coupling
Long contexts multiply per-query cost: a 100k-token prompt at $3 per million input tokens costs $0.30 per question, before the answer. Budget-sensitive long-document users should prefer cheap-input models or RAG.
