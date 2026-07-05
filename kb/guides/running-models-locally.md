---
category: guide
tags: [local, ollama, lm-studio, huggingface, download, gguf, install, step-by-step, terminal]
updated: 2026-07-06
---

# Guide: Running a Model Locally, Step by Step

## Path A: Ollama (recommended default, 5 minutes)
1. Install: download from ollama.com (Mac/Windows), or `curl -fsSL https://ollama.com/install.sh | sh` on Linux.
2. Pull a model: `ollama pull qwen3.5:9b` (the tag after the colon picks the size; the library page lists tags).
3. Chat: `ollama run qwen3.5:9b`.
4. Use it from apps: Ollama serves an OpenAI-compatible API at http://localhost:11434/v1 automatically; any tool that takes a base URL and model name works with it.
5. Housekeeping: `ollama list` (installed models), `ollama rm <tag>` (free disk), `ollama ps` (what is loaded).

## Path B: LM Studio (no terminal at all)
1. Install from lmstudio.ai.
2. Use the built-in search to download a model (it shows size and whether it fits your RAM).
3. Chat in the app, or enable the local server tab for the same OpenAI-compatible API pattern.

## Path C: Straight from Hugging Face (when a model is not in Ollama's library)
1. Find the model page; for local use you want GGUF files (community accounts like bartowski publish quantized GGUFs for most popular models).
2. Pick a quantization file: q4_K_M is the standard choice (see the local inference guide for the memory math).
3. Easiest route: `ollama run hf.co/<user>/<repo>:<quant>` pulls GGUF directly from Hugging Face. LM Studio can also download GGUFs by name. <!-- VERIFY hf.co pull syntax still current -->
4. Gated models (Llama family) require accepting the license on the HF page while signed in, and `huggingface-cli login` for CLI downloads.

## What to expect
- Download sizes: a 9B at q4 is ~6GB; first token after load takes a few seconds; see the local inference guide for speed by hardware.
- Everything stays on your machine: no account, no key, no data leaving, no per-token cost.
- If a model refuses to load, it does not fit your memory; pick a smaller size or lower quant.
