---
category: guide
tags: [hardware, gpu, buy, mac, nvidia, rtx, vram, unified-memory, workstation, budget]
updated: 2026-07-06
---

# Guide: The Hardware Landscape for Local AI

## The one rule
Fast memory capacity decides what you can run; everything else decides how fast. Size by the models you want (see the local inference guide's fit table), then buy the cheapest thing that holds them.

## The common options, cheapest first
- **What you already own**: any M-series Mac or a PC with 16GB RAM runs 4B-9B models today at usable speed. Start here before spending anything.
- **Used NVIDIA RTX 3090 (24GB VRAM)**: the classic value pick for a dedicated rig; runs 27-32B models at q4 fast. Used market roughly $600-800. <!-- VERIFY current used prices -->
- **RTX 4060 Ti 16GB / 4070 class**: new, modest cost, good for 8-14B fast and 24B tight.
- **RTX 4090 / 5090 (24-32GB)**: consumer top end; 32B comfortable, 70B quantized but slow.
- **Mac with big unified memory (32-128GB)**: the quiet workstation path; large MoE models (gpt-oss-120b class) run at readable speed on a Mac Studio, no GPU driver hassle, low power. Slower than NVIDIA per token but far simpler.
- **Multi-GPU / used server cards**: enthusiast territory; only worth it when serving many users or 70B+ dense models routinely.

## Reading a spec sheet in ten seconds
- VRAM or unified memory: the capacity number that matters.
- Memory bandwidth: the speed number that matters (generation is bandwidth-bound); a 4090 at ~1TB/s is several times an M-chip's bandwidth, which is why it is faster at the same model size.
- CUDA vs Apple: NVIDIA has the widest software support (vLLM, SGLang need it); Macs run Ollama/LM Studio/llama.cpp beautifully but not the server-grade stacks.

## Anti-recommendations
- Do not buy hardware for a use case an API serves for under $20/month; rent or use APIs until usage proves itself (see the GPU hosting guide's break-even math).
- Avoid 8GB GPUs for AI purposes in 2026; the models worth running have outgrown them.
- AMD and Intel GPUs work with some stacks but add friction; only pick them knowingly. <!-- VERIFY current ROCm/oneAPI support state -->
