---
category: guide
tags: [moe, mixture-of-experts, active-parameters, a3b, sparse, speed, memory]
updated: 2026-07-05
---

# Guide: Mixture-of-Experts (MoE) Models

## The idea in one paragraph
A mixture-of-experts model splits its brain into many small "expert" networks and activates only a few per token. A model named like "35B-A3B" has 35 billion parameters total but only about 3 billion active for any given token. You pay memory for all 35B (they must all be loaded) but get the speed of a 3B.

## Why it matters when choosing
- Memory: size by TOTAL parameters. A 35B-A3B at 4-bit needs roughly the same ~25GB as a dense 35B.
- Speed: expect generation speed close to a dense model the size of the ACTIVE parameters. That makes big MoE models surprisingly usable on Macs with lots of unified memory.
- Quality: usually between the two sizes; closer to the total for knowledge, closer to active for tricky reasoning chains. Benchmarks, not the name, are the guide.

## Practical readings of common names
- "30B-A3B": needs ~22GB at q4, runs like a 3B (fast). Great when you have memory but want speed.
- "120B-A5B" class (gpt-oss-120b style): needs 64GB+ machines, but generates at readable speed on a Mac Studio.
- Dense "9B": needs ~6.5GB at q4, runs like a 9B. Simpler mental model, no surprises.

## When to prefer MoE locally
You have unified memory to spare (32GB+ Mac) and want more quality without dropping to single-digit tokens per second. When memory is the bottleneck (8-16GB), dense small models remain the right call.
