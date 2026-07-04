---
category: guide
tags: [gpu, hosting, self-host, server, setup, vram, cost, cloud-gpu, rent, deploy]
updated: 2026-07-04
---

# Guide: GPU Setups and Self-Hosting Costs

## The decision in one line
Self-hosting makes sense for privacy, unlimited usage at flat cost, or offline needs. For light or moderate use, APIs are almost always cheaper than buying or renting a GPU.

## What hardware runs what (q4 quantization)
- No GPU needed: models up to ~9B run on a modern laptop CPU or Apple Silicon at usable speed. Start here before buying anything.
- Used RTX 3090 or 4060 Ti 16GB (roughly $400-900, 35k-75k INR): 8B-14B models fast, 24B-27B tight.
- RTX 4090 / 5090 (24-32GB VRAM, $1,800-2,500+): 32B models comfortably, 70B quantized but slow.
- Mac Studio or MacBook Pro with 48-128GB unified memory: large MoE models (gpt-oss-120b class) without a discrete GPU, at moderate speeds.
- Multi-GPU or A100/H100 class: only for serving many users; not a hobbyist path.

## Software setup, simplest first
1. Ollama (one installer, Mac/Linux/Windows): `ollama pull <model>` then chat or serve an OpenAI-compatible API on port 11434. Right answer for one user.
2. llama.cpp or LM Studio: similar scope, more knobs.
3. vLLM on Linux + NVIDIA: production-grade throughput, serves many concurrent users, needs real VRAM headroom.

## Running costs
- Electricity: a 300-450W GPU under load costs roughly $0.04-0.10 per hour (3-8 INR); idle draw is small.
- Renting instead of buying: cloud GPUs (RunPod, Lambda, and similar) run about $0.30-0.80/hour for a 24GB card, $2-4/hour for A100/H100 class. <!-- VERIFY current rates -->
- Break-even mental math: a $600 GPU equals roughly 1,000-2,000 hours of rented 24GB time. Rent first, buy when usage is proven.

## When NOT to self-host
- Budget under ~$50/month and usage is casual: an API or a free tier wins.
- You need frontier quality: no consumer setup matches the top API models.
- You need it reachable from the internet: hosting a public endpoint adds networking, auth, and uptime work that an API gives you for free.
