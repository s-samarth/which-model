---
category: guide
tags: [ollama, lm-studio, vllm, sglang, llama-cpp, serving, inference, deploy, self-host]
updated: 2026-07-05
---

# Guide: Inference Serving Stacks

Which software actually runs a local model, and when each is the right call.

## For one person on one machine
- Ollama: command line, one installer, `ollama pull model` and go. Exposes an OpenAI-compatible API on port 11434, so apps can talk to it. The default recommendation.
- LM Studio: same idea with a graphical interface, model browser, and chat window. Best for people who do not live in a terminal.
- llama.cpp: the engine underneath both; use it directly only if you want maximum control or minimal footprint.

## For serving many users
- vLLM: the production standard on NVIDIA GPUs. Batches concurrent requests (continuous batching), so 20 simultaneous users cost far less than 20x one user. OpenAI-compatible endpoint. Linux only in practice.
- SGLang: same niche as vLLM, often faster on structured output and multi-turn workloads thanks to prefix caching (RadixAttention). Also OpenAI-compatible. <!-- VERIFY current vLLM vs SGLang performance balance -->
- Rule of thumb: hobby or single user, Ollama/LM Studio; a real service with concurrent users, vLLM or SGLang on a Linux GPU box.

## Why the choice matters less than it looks
All of these speak the same OpenAI-compatible protocol, so an app written against one works with any other by changing a URL. Pick for your workload, not fear of lock-in.

## What changes between them
- Throughput under concurrency: vLLM/SGLang >> Ollama (Ollama processes requests mostly one at a time).
- Setup effort: Ollama minutes, vLLM an afternoon (CUDA drivers, Python env).
- Quantization formats: Ollama/LM Studio use GGUF quants (q4_K_M etc.); vLLM/SGLang typically run FP8/AWQ/GPTQ variants and need more VRAM headroom.
- Platforms: Ollama and LM Studio run on Mac/Windows/Linux; vLLM and SGLang want Linux + NVIDIA.
