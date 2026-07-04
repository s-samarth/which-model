---
category: taxonomy
tags: [coding, programming, software, debugging, agentic-coding]
updated: 2026-07-04
---

# Task: Coding

## What it demands
Code generation, debugging, refactoring, and agentic coding (editing real repos over many steps). Needs strong reasoning, large context for real codebases (32k minimum, 128k+ for repo-wide work), and reliable instruction following. Speed matters for interactive use (autocomplete, pair programming) but quality dominates for harder tasks.

## Which benchmarks predict quality
- livebench_agentic_coding and livebench_coding are the primary ranking signals in our catalog.
- SWE-bench Verified and Terminal-Bench measure real-repo agentic work but the top of those leaderboards is compressed, small gaps there mean little.
- Aider polyglot correlates with pair-programming quality.

## Typical model tier
- Serious daily coding: frontier tier (top 10 on agentic coding scores).
- Hobby projects, learning, scripts: mid tier works, including strong open models.
- Local coding is viable at 24B+ params with a coder-tuned model, expect a clear quality gap vs frontier APIs on multi-step tasks.

## Example user phrasings
- "something that codes for me", "I want help building my app"
- "fix bugs in my Python project", "a copilot alternative"
- "an AI that can work in my terminal"
