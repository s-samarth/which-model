# Which Model? Product Document

## One sentence

Which Model? is a free, chat-first advisor that turns a plain-language description of what someone wants from AI ("a chatbot for my shop", "something that codes offline on my laptop") into a grounded, current, personally-fitted model recommendation, with real prices, real benchmark scores, and the exact setup steps.

## The problem

Choosing an AI model in 2026 is a research project. There are 300+ commercially available models, a dozen benchmark leaderboards that disagree with each other, prices spanning four orders of magnitude, and a local-model ecosystem with its own vocabulary (quantization, VRAM, MoE, context windows). The people who most need help are exactly the people who cannot parse any of that: shop owners, students, indie developers, small teams.

Their current options all fail them:

- **Asking ChatGPT or Claude**: training-data staleness, self-preference, and no live prices. A frontier chatbot will confidently recommend last year's models at wrong prices, and never says "actually, a 6GB model on your own laptop would do".
- **Leaderboards** (LMArena, LiveBench, HLE): accurate but unreadable for non-experts, and they rank models in a vacuum with no notion of budget, hardware, or use case.
- **Quiz/wizard sites**: static forms that cannot handle "honestly I am not sure" or "what if I hosted it myself?".

## What the product signifies

Two theses, one product:

1. **Advice should be grounded, not recalled.** Every model name, price, and score in an answer traces to a row in a versioned catalog refreshed daily, or to a cited web search. The LLM narrates; it is never the source of facts. This is the opposite of asking a chatbot to remember the market.
2. **Small models plus curated knowledge beat big models without it, for narrow jobs.** The entire service runs on a 4B-parameter open model. It holds a natural conversation, extracts structured requirements, and writes expert-quality recommendations, because a frontier model's judgment was distilled into its knowledge base ahead of time. The product is an existence proof that vertical AI products do not need frontier inference costs.

## Who it is for (ideal user profiles)

| Profile | Trigger moment | What they get |
|---|---|---|
| Non-technical business owner | "I keep hearing I should use AI for customer service" | A concrete pick with monthly cost in their currency and a signup link |
| Student / hobbyist developer | "I want coding help but cannot pay" | Free-tier and local options ranked honestly, hardware-checked |
| Privacy-conscious professional (legal, health, finance) | "Client data cannot leave my machine" | A local model that fits their RAM, with quantization and setup explained |
| Indie hacker / small team CTO | "Which API do we build on, and what will it cost at scale?" | Task-relevant benchmark comparison plus usage-based cost projection |
| India-first builder | "Hindi support, rupee budgets" | INR pricing, Indic-language guidance, regional provider notes |

## The user journey

1. **Arrive** (from a shared recommendation link, a search result, or a community post) and see one input box: "Tell me what you're trying to do."
2. **Converse.** The agent asks at most a couple of plain-language questions per turn, shows its work live (reading its knowledge base, querying the catalog, searching the web), and never repeats a question. An impatient user hits "Recommend now" at any time; a recommendation always arrives within six turns.
3. **Hardware moment** (local users only): the agent hands over one safe, read-only terminal command from a fixed library; the user pastes the output; the catalog is filtered to what actually fits their machine.
4. **The answer**: a streamed, written recommendation, reasoning first, benchmarks named and explained, trade-offs stated, costs computed, setup commands ready to copy. Tables appear only when they help.
5. **Follow up.** "What if I wanted to host it myself?" produces a fresh answer, not a replay.

## Positioning

"PCPartPicker for AI models." Neutral, current, fit-to-you. The product never sells a model, never takes placement fees, and shows its data age in the footer. Neutrality and freshness are the brand.

## What it is not

- Not a leaderboard: it answers "for you", not "in general".
- Not a router or gateway: it recommends; it does not proxy traffic (a possible future, see ROADMAP).
- Not a general chatbot: it does one job. Off-topic conversations are redirected.

## Success measures (pre-revenue)

- Conversations that reach a recommendation (target: >85%).
- Recommendation link shares and return visits (the honest signal of usefulness).
- "Followed the advice" confirmations via lightweight feedback prompt.
- Zero grounding violations in production sampling (trust is the product).
