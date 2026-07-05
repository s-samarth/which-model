# The Engineering Story: Building Claude for One Narrow Job on a 4B Model

This is the document to read before an interview, a demo, or a blog post. It explains the system the way its architecture deserves: as a set of deliberate trade-offs, each with a reason and a receipt.

## The one-line thesis

A 4-billion-parameter model running on a laptop can deliver frontier-quality advice in a narrow domain, if you refuse to let it be the source of any fact, distill a big model's judgment into a curated knowledge base it retrieves from, and wrap it in deterministic tools that do everything computers are already good at.

## The constraint that shaped everything

The serving model is qwen3.5:4b via Ollama on consumer hardware: roughly 8-16k of usable context, occasional malformed JSON, no reliable world knowledge, and single-digit-seconds-per-sentence generation on a fanless MacBook Air. Every architectural decision below is downstream of taking that constraint seriously instead of pretending the model is smarter than it is.

## Decision 1: The LLM narrates; it never recalls

Facts live in two places, neither of which is the model's weights:

- **SQLite catalog** for anything relational: 300+ models, prices, context windows, modality flags, per-category benchmark scores, parameter counts. Refreshed daily from the OpenRouter API and LiveBench release CSVs by an idempotent ingestion pipeline with backoff, snapshot fallbacks, and an alias table for the messy cross-source name matching (unmatched names are logged and dropped, never guessed).
- **Markdown knowledge base** (29 documents) for distilled judgment: what each benchmark actually measures and how it gets gamed, what fits in 32k tokens, why fanless laptops throttle, how users phrase uncertainty, what a mixture-of-experts model costs in memory versus speed.

The rule "if it is not in the DB, it does not exist" turned the hardest failure mode (confident hallucination about models, prices, scores) into a structural impossibility rather than a prompt-engineering hope. A post-generation validator scans every answer for catalog model names outside the grounded candidate set, with span logic so "GPT-5.4" inside "GPT-5.4-mini" does not false-positive; violations append a visible correction.

**Interview soundbite**: retrieval-augmented generation was rejected for facts. Facts here are relational (filter by price, join scores, check memory fit), and SQL does that exactly while RAG does it probabilistically. RAG-style retrieval is reserved for what it is good at: unstructured judgment.

## Decision 2: Big model writes the knowledge base; small model routes through it

This is the economic core of the system. A frontier model (Claude) authored and curates the knowledge base: benchmark explainers with honest gaming caveats, task taxonomies with example user phrasings, hardware heuristics, pricing mental models. That is a one-time (plus maintenance) cost measured in authoring sessions.

At inference time, the 4B model retrieves 3-4 of those documents and writes answers grounded in them. The expensive intelligence ran once, offline; the cheap intelligence runs per-request, online. Per-query marginal cost is effectively electricity.

Why this works: the knowledge the product needs is mostly stable, curated judgment, not per-query reasoning. The 4B model only has to do three genuinely per-query things: understand a message, pick the right knowledge, and compose it into an answer for this user. Those are exactly the things small instruction-tuned models are good at.

The corollary discipline: time-sensitive claims in the KB carry `<!-- VERIFY -->` markers and review cadence, because a distilled knowledge base is a depreciating asset if nobody owns freshness.

## Decision 3: Deterministic spine, generative skin

The LangGraph agent is an explicit typed state machine: router, extract, web lookup, retrieve, clarify, hardware probe, catalog query, recommend. The spine (routing conditions, currency conversion, cost math, memory-fit math, candidate ranking, quantization tables, tok/s estimates) is all plain code. The LLM appears at exactly three points: extracting structured requirements, asking clarifying questions, and composing the final answer.

Every LLM touchpoint has a deterministic fallback, so a total model failure degrades to a robotic but correct experience instead of a crash. The reverse also holds: the final answer is fully LLM-composed Markdown (no template, no fixed card), because user testing proved that hardcoded answer structures cannot address what a specific person actually asked.

Bugs found in real user testing hardened this split. A 4B model converting 2000 rupees to dollars produced $2.38 (off by 10x); currency conversion moved into code. It re-asked questions verbatim; asked-question memory with similarity checks moved into state. It picked a runner-up ranked below three better models; rank sanity moved into a validator.

## Decision 4: Structured output as a contract with a repair loop

Small models emit malformed JSON at a measurable rate, and worse, echo the JSON schema back instead of an instance. The fix stack, in order of impact:

1. **Skeleton prompts, not schema dumps.** A generated compact field guide (`"deployment": "local|api|either"|null`) replaced `model_json_schema()`, which the model loved to parrot. This alone cut both schema-echo failures and token truncation (verbose schemas pushed outputs past max_tokens mid-JSON).
2. **Validate, re-prompt once with the error, then fall back.** Never retry forever; never crash.
3. **Reasoning off for extraction.** qwen3.5 is a thinking model; `reasoning_effort=none` (an OpenAI-standard parameter Ollama honors) tripled effective speed for structured calls that need no deliberation.

## Decision 5: Context is a budget, latency is a feature

- The durable memory is a compact typed requirements object, not chat history; the model window carries six messages, each clipped to 400 characters.
- KB documents inject at most four per turn, trimmed to 1,500 characters, selected deterministically for the turn's purpose plus hybrid retrieval over the user's own words.
- Hybrid retrieval is BM25 fused with local embeddings (nomic-embed-text via the same OpenAI-compatible endpoint) by reciprocal rank, added when real users typed Hinglish and vague phrasings that keyword matching missed. Vectors cache on disk by content hash. The whole thing degrades to BM25 if the embedding model is absent.
- Answers stream token-by-token (contextvar channel to SSE), and an activity feed narrates each step ("Searching the web: Qwen3.5-9B SWE-bench score"), because perceived latency is mostly about visible progress.
- `keep_alive` pins the model in memory between slow human turns; without it, Ollama unloads after five minutes and the next turn pays a full reload.

## Decision 6: Portability as a hard boundary

The app speaks only the OpenAI-compatible protocol, configured by two environment variables. Swapping Ollama for vLLM, SGLang, LM Studio, or a cloud API is a config change, verified by a regression gate: 16 scripted multi-turn scenarios with programmatic assertions (grounding is binary: zero violations allowed). The eval harness runs fully mocked in two seconds for development and against the live model for release gating.

## What I would tell an interviewer this project demonstrates

1. **Constraint-driven architecture**: every component exists because of a measured limitation of a 4B model, not because of framework fashion.
2. **The distillation economics insight**: frontier judgment amortized into artifacts (KB, taxonomies, heuristics) that a small model exploits per-request. This is the pattern behind most sustainable vertical AI products.
3. **Trust engineering**: grounding enforced structurally (facts from tools) and verified adversarially (name-scanning validator, eval gate), not requested politely in a prompt.
4. **Evidence loops**: real-user screenshots drove three hardening milestones; every bug became a regression test; the eval harness is the contract for any future model swap.
5. **Full-stack ownership**: ingestion pipeline with source failures handled, typed agent graph, retrieval layer, SSE streaming API, dependency-free frontend, CI data refresh, and documentation as a product surface.

## Honest limitations

- The 4B model still occasionally needs its repair loop; extraction quality is the ceiling on conversation quality.
- Benchmark coverage is LiveBench-centric because it is the freshest citable source; other leaderboards were evaluated and rejected for staleness, with web search filling gaps at answer time.
- Single-node, in-memory sessions: deliberate MVP scope, with the interfaces (SessionStore protocol, OpenAI-compatible boundary) already in place for the scaled version.
