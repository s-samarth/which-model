---
category: taxonomy
tags: [rag, documents, doc-qa, retrieval, knowledge-base, pdfs, legal]
updated: 2026-07-04
---

# Task: RAG / Document Q&A

## What it demands
Answering questions grounded in provided documents. Needs strong long-context comprehension, faithfulness (no invented facts), and citation ability. Context window is the critical spec: the model must fit retrieved chunks plus the question. Privacy often matters because documents are sensitive (legal, medical, internal).

## Which benchmarks predict quality
- livebench_language and livebench_data_analysis are the closest signals in our catalog (comprehension and structured extraction).
- livebench_global as a general quality floor.
- No public benchmark cleanly measures RAG faithfulness; test on your own documents.

## Typical model tier
- Casual document Q&A: mid tier with 32k+ context.
- Legal, medical, compliance: frontier tier or a strong open model run privately. 128k context recommended for long contracts.
- Privacy-sensitive: open-weights model on your own hardware or a private cloud endpoint.

## Example user phrasings
- "summarize and search my PDFs", "ask questions about my legal documents"
- "a knowledge base bot for company docs", "chat with my files"
- "RAG over research papers"
