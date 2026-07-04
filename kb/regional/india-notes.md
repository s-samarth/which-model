---
category: regional
tags: [india, inr, hindi, indic, sarvam, pricing, availability]
updated: 2026-07-04
---

# Guide: India-Specific Notes

## Currency
Catalog prices are USD. Convert at roughly 84 INR per USD for mental math (the app uses the configured USD_TO_INR rate for displays). <!-- VERIFY exchange rate drift -->
A $10/month API bill is about 840 INR/month.

## Payment and availability
- OpenRouter, OpenAI, Anthropic, and Google APIs accept Indian cards; UPI is generally not accepted for API billing directly. <!-- VERIFY current payment options -->
- Consumer subscriptions (ChatGPT, Claude, Gemini) have INR pricing in India; Gemini has offered aggressive India-specific plans. <!-- VERIFY current plans -->

## Indian languages
- Frontier models handle Hindi and major Indic languages (Tamil, Telugu, Bengali, Marathi) well for chat and translation; quality drops for code-mixed Hinglish nuance and low-resource languages.
- Indic scripts tokenize 2-4x heavier than English: the same sentence costs more tokens, which raises API bills and fills context windows faster.

## Indian providers
- Sarvam AI builds Indic-focused models (Sarvam-M line) with Hindi and regional language strengths, plus speech models; relevant for voice bots and Indic-first products. <!-- VERIFY current Sarvam model lineup and API availability -->
- Krutrim (Ola) and others offer India-hosted inference; relevant when data residency in India is required. <!-- VERIFY current status -->

## Practical notes
- Data residency: most global APIs process data outside India; regulated sectors (finance, health) may need India-region hosting or local deployment. Local open-weights models sidestep this entirely.
- Latency to US-hosted APIs from India adds 200-400ms; fine for chat, noticeable for voice.
