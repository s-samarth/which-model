# Go-To-Market

## The honest starting point

This is a free B2C utility in a world where everyone already has a chatbot. Nobody will pay for it, nobody will download an app for it, and "ask Claude" is the default competitor. GTM therefore optimizes for one thing: **being the answer that surfaces at the exact moment someone asks "which AI should I use?"**, and being visibly better than a chatbot's answer in that moment.

## Why anyone would use this over Claude or ChatGPT

The pitch is not "cheaper", and it is not "chatbots are stale" (they are not: ChatGPT and Claude ship with web search and can pull current pages). The honest differentiation is systematic versus ad-hoc:

1. **The whole market, not a few search hits.** A chatbot with web search grounds its answer in whichever handful of pages one query surfaced. This compares every model in a daily-refreshed catalog with consistent per-task scores and consistent cost math, every time. The difference shows on exactly the queries that matter: "cheapest model that fits my task and budget" is a database query, not a reading assignment.
2. **Neutrality.** Each lab's harness structurally favors its own models; ChatGPT recommending OpenAI is not a bug, it is a conflict of interest. A recommender with no model to sell, visible data age, and cited scores is trustworthy by construction. This is the entire brand.
3. **Hardware fitting.** No chatbot runs the "paste your Mac's memory readout" flow and filters to models that physically fit, with quantization math shown. This is the feature that makes people screenshot the product.
4. **Consistency and verifiability.** Deterministic cost basis, named benchmarks with explanations, an eval gate asserting zero ungrounded model mentions. Chatbot answers to the same question vary run to run; this is a product whose answers can be audited.

## Ideal customer profiles, ranked by GTM leverage

1. **Local-LLM hobbyists** (r/LocalLLaMA, Hacker News): most likely to try it, hardest to impress, and the community whose approval creates credibility. The hardware-fit flow is built for them.
2. **Students and budget developers** (India-first): free-tier and INR-aware answers are genuinely differentiated; this segment shares tools aggressively.
3. **Non-technical business owners**: largest long-term pool, reached only indirectly (search, embeds), never by community marketing.
4. **Content creators and dev-tool writers**: not end users but distributors; they embed or cite the tool in "best LLM for X" content.

## Distribution: three engines

### 1. Programmatic SEO (the compounding engine)

The catalog is a content machine. Generate static, fast, honest pages from the same data and evals that power the chat:

- "Best LLM for {task} under {budget}" for every task/budget cell
- "Will {model} run on {hardware}?" for every local model and common machine
- "{Model A} vs {Model B}" comparison pages with per-task scores and monthly cost math
- Each page ends in the chat with context prefilled ("refine this for your exact situation")

This is the PCPartPicker playbook: the tool is the destination, the generated pages are the funnel, freshness is the moat. Nobody else regenerates these pages from a daily-refreshed catalog with an eval-gated recommender behind them.

### 2. Share loops (the trust engine)

- Every recommendation gets a permalink and a clean share card (picks, costs, data age). People do not share chatbots; they share verdicts.
- "I asked Which Model and it told me my laptop can run X" is inherently postable content for segment 1.

### 3. Community launches (the ignition)

Sequenced, each with a tailored angle:

1. r/LocalLLaMA: "I built a hardware-aware local-model picker; it runs on a 4B model itself." The self-referential angle (small model recommending models) is the hook.
2. Hacker News Show HN: lead with the engineering story (grounded 4B agent, zero-hallucination design); HN rewards architecture honesty.
3. Product Hunt: consumer framing ("stop asking ChatGPT which AI to use").
4. X/LinkedIn build-in-public thread series from the engineering story document.
5. India dev communities: the INR/Hindi angle is a genuine wedge nobody else has.

## Embed and API (the B2B2C extension)

The same recommender as an embeddable widget or JSON API for dev-tool docs, newsletters, and "AI stack" consultancies: "Powered by Which Model" with the neutrality guarantee. This is how the product reaches non-technical users at scale without owning that audience, and the only near-term path that resembles revenue (sponsor-free licensing) if ever wanted.

## Launch checklist (product gaps before real users)

1. Recommendation permalinks + share cards (the loop depends on it).
2. Feedback capture: one-tap "this helped / this missed" on every answer.
3. Privacy-respecting analytics (Plausible-class) + conversation quality sampling.
4. Rate limiting and abuse guards (free GPU inference invites abuse).
5. A hosted, always-on deployment (see DEPLOYMENT.md) with uptime monitoring.
6. Terms/privacy page: sessions are anonymous, conversations sampled for quality.

## Positioning statement

For anyone deciding which AI model to use, Which Model? is a free advisor that gives a current, neutral, personally-fitted answer in one conversation, unlike chatbots that recall a stale market from memory, and unlike leaderboards that rank models for nobody in particular.

## What we will not do

- No pay-for-placement, ever; it would delete the only durable asset (trust).
- No accounts before there is a reason (saved history across devices is the first legitimate one).
- No general-chatbot scope creep; every off-domain feature dilutes the one query we want to own.
