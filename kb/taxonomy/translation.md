---
category: taxonomy
tags: [translation, multilingual, languages, hindi, localization]
updated: 2026-07-04
---

# Task: Translation / Multilingual

## What it demands
Accurate meaning transfer plus register and idiom. Quality varies sharply by language pair: high-resource pairs (English-Spanish, English-Hindi) are strong across tiers; low-resource languages and dialects need frontier models. Document translation needs context length; live chat translation needs speed.

## Which benchmarks predict quality
- livebench_language is a weak proxy (English-centric). No multilingual benchmark is in our catalog data.
- For Indian languages, models with explicit Indic training (Sarvam, and large frontier models) do best. <!-- VERIFY current Sarvam model lineup and availability -->

## Typical model tier
- High-resource pairs, casual use: budget tier is fine.
- Professional or legal translation: frontier tier, and human review.
- Local: mid-size open models translate major languages decently; verify on your target pair before committing.

## Example user phrasings
- "translate my product pages to Hindi", "multilingual customer support"
- "subtitle translation", "localize my app"
- "English to Tamil translation at scale"
