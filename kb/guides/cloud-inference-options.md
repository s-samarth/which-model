---
category: guide
tags: [cloud, aws, azure, gcp, bedrock, fireworks, together, groq, managed, endpoint, deploy]
updated: 2026-07-06
---

# Guide: Cloud Options for Serving Models

Three genuinely different ways to get a model running "in the cloud", in rising order of effort.

## Tier 1: Managed inference endpoints (no servers, per-token billing)
You call an API; someone else owns the GPUs. For open-weights models this is usually the sweet spot between local and self-hosting.
- **Fireworks, Together, Groq, DeepInfra**: OpenAI-compatible endpoints for popular open models (Qwen, Llama, DeepSeek and friends), per-token prices typically far below frontier APIs, and very fast (Groq especially). Sign up, get a key, done in minutes. Some offer free starter credits. <!-- VERIFY current lineups and credits -->
- **Hyperscaler versions**: AWS Bedrock, Azure AI Foundry, Google Vertex AI expose many of the same models with enterprise contracts, regional control, and cloud credits eaten happily. More console clicking than the startups, same per-token idea. Bedrock and Azure now expose OpenAI-compatible endpoints for many models, so apps built against the OpenAI protocol work with a base-URL change. <!-- VERIFY compatibility coverage -->
- When to pick this tier: you want a specific open model without hardware, or you have cloud/startup credits to burn.

## Tier 2: Serverless GPU (your code, their autoscaling)
RunPod Serverless, Modal, Replicate and similar run your inference container per request and scale to zero. Per-second billing means a low-traffic app costs single-digit dollars monthly instead of an idle GPU's hundreds. Trade-off: cold starts (seconds to a minute) when traffic wakes it. Right for bursty or hobby-scale services.

## Tier 3: A GPU machine you manage (maximum control)
Rent a GPU VM and run vLLM or SGLang yourself.
- Marketplace clouds (RunPod, Vast.ai, Lambda): consumer cards like an RTX 4090 at roughly $0.30-0.60/hour; cheapest, minimal ceremony. <!-- VERIFY prices -->
- Hyperscalers: AWS EC2 g6/g5 (L4/A10G class), Azure NC-series, GCP G2; pricier per hour but inside your existing account, credits apply, and networking/IAM integrate with everything else.
- The setup shape is the same everywhere: pick a CUDA image, install vLLM (`pip install vllm`), run `vllm serve <model>`, put it behind your app's base URL. Budget for the GPU running 24/7 or add your own start/stop automation.
- When to pick this tier: steady traffic, custom models or adapters, or strict data-control needs.

## The moving target
Inference offerings change monthly: new hosts, price drops, faster chips. Treat any specific price here as approximate and check the provider page; the pattern (managed endpoint vs serverless vs owned VM) is the stable knowledge.
