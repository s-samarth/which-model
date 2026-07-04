---
category: taxonomy
tags: [agentic, tool-use, agents, automation, function-calling, workflows]
updated: 2026-07-04
---

# Task: Agentic / Tool Use

## What it demands
Multi-step autonomous work: calling tools, reading results, deciding next actions. Needs reliable structured output (function calls), planning over long horizons, and recovery from errors. Context grows fast because tool results accumulate, so 128k+ windows help. This is the most demanding common task type; small models drop the thread after a few steps.

## Which benchmarks predict quality
- livebench_agentic_coding is the closest proxy in our catalog (multi-step repo tasks).
- livebench_if for whether the model obeys tool schemas.
- Terminal-Bench and OSWorld measure real agent work but are not in our catalog data, and a 2026 Berkeley RDI study showed several agent benchmarks can be gamed, so treat published agent scores with caution.

## Typical model tier
- Production agents: frontier tier. Reliability gaps compound across steps, a 5% per-step failure rate ruins a 10-step workflow.
- Simple 2-3 step automations: mid tier works.
- Local: only the largest local models (70B+, or strong MoE around 30B active 3B) sustain multi-step tool use, and slowly.

## Example user phrasings
- "an agent that books things for me", "automate my workflow"
- "AI that can use my APIs", "something that browses and fills forms"
- "an assistant that files tickets automatically"
