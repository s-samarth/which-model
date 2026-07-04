---
category: guide
tags: [local, hardware, vram, ram, quantization, ollama, gpu, macbook, offline]
updated: 2026-07-04
---

# Guide: Local Inference

## Memory: the binding constraint
A model must fit in fast memory. Apple Silicon Macs use unified memory (the GPU shares system RAM, so a 16GB Mac has roughly 10-11GB usable for a model). PCs need the model in GPU VRAM for speed; spilling to system RAM slows generation 5-20x.

## Quantization
Weights compressed to fewer bits per parameter. Rule of thumb for file size: params (billions) x bytes per param, plus about 20% runtime overhead for KV cache and buffers.
- q4_K_M (4-bit, the default): about 0.6 GB per billion params. Small, slightly lossy. A 9B model needs about 6.5GB.
- q5_K_M: about 0.72 GB per billion. Slightly better quality.
- q8_0 (8-bit): about 1.07 GB per billion. Near lossless, double the size.
- fp16: 2 GB per billion. Reference quality; rarely worth it for chat.
Quality loss from q4 is small but real: noticeable on math and code edge cases, negligible for casual chat.

## What fits where (q4 quant)
- 8GB RAM/VRAM: up to ~7B comfortably (4B leaves room for apps).
- 16GB: up to ~14B comfortably; 24-27B is possible but tight with little context headroom.
- 24GB: up to ~27-32B.
- 32-48GB: 70B dense models or large MoE (gpt-oss-120b at ~60GB needs 64GB+).
- MoE models (e.g. 35B-A3B) still need memory for all params but run at the speed of their active params.

## Speed expectations (rough, q4)
- Apple M-series (M2/M3/M4 base): 4B at 25-50 tok/s, 9B at 12-25, 27B at 4-10.
- Mid gaming GPU (RTX 4060 Ti/4070, 12-16GB): 8B at 40-80 tok/s.
- High-end GPU (4090/5090, 24-32GB): 32B at 25-45 tok/s.
- CPU only: 2-8 tok/s even for small models; painful beyond short replies.
Readable speed is about 10 tok/s; below 5 feels broken.

## Thermals
Fanless machines (MacBook Air) throttle under sustained load: the first minutes are fast, long sessions slow down noticeably. Fine for chat, frustrating for batch jobs.
