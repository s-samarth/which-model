# Roadmap and Future Strategy

Priorities are ordered by (user trust) x (distribution leverage) / (effort). The MVP conversation loop is done; everything below builds on it.

## Now (pre-launch hardening, ~days each)

1. **Recommendation permalinks + share cards.** The growth loop. Server-side stored verdicts with stable URLs and OG images.
2. **Feedback capture.** One-tap helpful/missed on every answer, stored with the anonymized conversation for eval mining. This is the start of the data flywheel: real conversations become eval scenarios, eval failures become KB edits.
3. **Hosted deployment with monitoring.** Serverless GPU or a small dedicated instance (see DEPLOYMENT.md), uptime checks, structured logs, error alerting, rate limiting.
4. **TTFT work.** Prompt-prefix stabilization for cache reuse, candidate/KB trimming, smaller extractor model. Target: first token under 3 seconds on the hosted GPU.

## Next (the funnel, ~weeks)

5. **Programmatic SEO pages** generated from the catalog ("best X under Y", "will X run on Y", "A vs B"), statically built in CI on each data refresh, each ending in a prefilled chat.
6. **Benchmark source expansion.** The ingestion path is ready (benchmarks table + CATEGORY_BENCHMARKS + blurbs); add sources as fresh citable ones appear, with the staleness rule from RUNBOOK.md. Candidates: Artificial Analysis API (terms permitting), LiveCodeBench Pro releases, MMMU-Pro for vision.
7. **Catalog breadth.** Ollama library coverage beyond the curated list; provider availability by region; free-tier rate-limit facts (the most requested missing fact in testing).
8. **Conversation memory quality.** Cross-turn summarization tuning, and "compare my last two recommendations" support.

## Later (product depth, ~months)

9. **Verdict pages as living artifacts.** A shared recommendation re-checks the catalog on view: "prices changed since this was generated; GPT-5.4-mini is now cheaper than the pick". Nobody else can do this; it is the freshness moat made visible.
10. **Embeddable widget + JSON API** with "Powered by Which Model" attribution (the B2B2C channel).
11. **Stack recommendations, not just model picks.** Real questions are "model + where to run it + what it costs at my scale"; extend FACTS with serving-stack and cloud-instance data (the GPU-hosting KB doc already seeds this).
12. **Persistent user memory** (opt-in accounts only when history-across-devices demand is proven; SessionStore protocol is ready).
13. **Fine-tuned extractor.** Once real-conversation data exists: LoRA-tune the small model on extraction and answer composition for this domain, shrinking prompts and cutting latency further. Adapters keep the base model swappable.

## Repivots worth watching (not doing now)

- **PCPartPicker for AI, fully leaned in.** If SEO pages outperform chat, invert the product: pages first, chat as the refiner. Same data, same evals, different front door.
- **The router.** If users ask "just give me one key that picks the model per request", the recommender becomes a gateway (OpenRouter-style) with our fit logic. Big scope jump; only with real pull.
- **Procurement co-pilot for teams.** The B2B version: same engine, plus compliance/residency filters and a shareable decision memo. This is where willingness-to-pay lives if it is ever wanted.

## Explicit non-goals

- Chasing frontier-model quality in the narrator; the architecture wins by not needing it.
- Accounts, social features, or anything that adds login friction before the share loop proves retention.
- Paid placement or affiliate weighting of results (affiliate links, if ever added, must be identical across all recommended providers and disclosed).

## Standing priorities regardless of stage

- Zero grounding violations in production sampling.
- Data freshness visible everywhere a number appears.
- The eval gate runs before any model, prompt, or retrieval change ships.
- Every real-user bug becomes a scenario in the harness.
