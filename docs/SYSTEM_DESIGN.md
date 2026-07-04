# System Design

## The core bet

A 4B local model is useful if, and only if, it is never trusted with facts. The design splits responsibilities hard:

- The LLM elicits, routes, and narrates.
- SQLite answers "which models, what price, what score".
- A curated markdown knowledge base answers "what does this benchmark mean, what fits in 32k tokens".
- A validation layer rejects LLM output that names models outside the grounded candidate set.

If the LLM disappeared tomorrow, the tools would still produce a correct (if robotic) recommendation. That fallback actually exists and ships: every LLM-dependent node has a deterministic degraded path.

## Graph

```mermaid
flowchart TD
    START --> R[router<br/>deterministic]
    R -->|pasted probe output| PP[probe_parse]
    R -->|anything else| EX[extract_requirements<br/>LLM, JSON + repair]
    EX --> READY{readiness}
    PP --> READY
    READY -->|required fields filled,<br/>impatient, or turn 6| RR[retrieve_kb<br/>purpose: recommend]
    READY -->|local + hardware unknown| HP[hardware_probe<br/>canned snippet] --> END1[END]
    READY -->|gaps remain| RC[retrieve_kb<br/>purpose: clarify] --> ASK[ask_clarifying<br/>LLM, max 2 questions] --> END2[END]
    RR --> QC[query_catalog<br/>deterministic SQL] --> REC[recommend<br/>LLM picks + validation] --> END3[END]
```

One graph invocation handles one user turn and ends. The web layer persists the returned state per session and re-invokes on the next message. No human-in-the-loop interrupts exist inside the graph.

## State schema

`AgentState` (pydantic): `messages` (rolling window), `summary` (compact string for older turns), `requirements` (the typed extraction below), `kb_context` (chunks retrieved this turn), `candidates` (catalog rows), `phase` (eliciting, probing_hardware, retrieving, recommending, done), `user_turns`, `recommend_now`, `pending_probe`, and per-turn outputs (`reply`, `recommendation`, `notices`).

`Requirements`: task_category (10-value enum), task_description, deployment (local/api/either), budget_monthly_usd, hardware (ram_gb, gpu, vram_gb, os), context_need (short/medium/long), latency_need, privacy_need, language_needs, usage_level, open_questions. `missing_required()` derives what must still be asked: task and deployment always; budget only for API deployment; hardware only for local.

## Node responsibilities and failure policy

| Node | LLM? | On LLM failure |
|---|---|---|
| router | no | n/a, pure rules (probe detection, impatience regex) |
| extract_requirements | yes, JSON schema | one repair re-prompt with the error, then continue with unchanged requirements |
| retrieve_kb | no | n/a, deterministic doc selection + BM25, capped at 2 rounds |
| ask_clarifying | yes | canned per-gap questions from a fixed table |
| hardware_probe | no | n/a, snippet library only; second attempt asks the user directly |
| query_catalog | no | n/a; empty result relaxes budget once, then reports honestly |
| recommend | yes | grounding-validated retry, then fully deterministic plan from rankings |

The structured-output wrapper (`agent/llm.py`) validates JSON against the pydantic schema, re-prompts once with the validation error, and raises after the second failure so each node can take its fallback. A conversation never crashes because a tool or the model failed; the web layer catches everything else and answers with a data-age disclosure.

## Why deterministic tools instead of RAG for facts

Facts here are relational: filter by price, join scores, compare context windows, check memory fit. SQL does this exactly; retrieval-augmented generation does it probabilistically and invites the model to blend half-remembered numbers with retrieved ones. The rule "if it is not in the DB, it does not exist" is also what makes the adversarial case tractable: when a user asks about SuperGPT-9000, `lookup_model` returns nothing and the agent says so instead of confabulating.

The knowledge base is the complement: distilled judgment (what a benchmark means, what 32k tokens holds) that has no schema. That is retrieval's job, and only that.

## Voice and answer composition

The product is "Claude, narrowly specialized in choosing AI models": a shared persona prompt frames every LLM call, clarify turns acknowledge before asking, and the recommendation reply is written by the model itself, shaped by what the user actually asked, with reasoning first. Structure survives underneath: the LLM's narrative and per-pick "why" text pass the same grounding validation as before, ids are rank-sanitized, and every number in the card is computed, not generated. Templates still exist but only fire when the LLM fails outright. The benchmark used for ranking is always named and explained in plain language (BENCHMARK_BLURBS), selected per task category, never a silent global default.

Local picks carry a computed `local_setup` block: quantization options with memory footprints from the DB's quant_factors table and fit flags against the user's hardware, a tok/s estimate by hardware tier (MoE models rated at active-parameter speed), a mixture-of-experts explanation when applicable, and serving-stack guidance (Ollama/LM Studio for one user, vLLM/SGLang for concurrent serving). The comparison table shows parameter count and q4 memory for unbenchmarked local rows instead of dashes.

A note on benchmark sources: the Aider polyglot leaderboard was evaluated as a second ranking signal and rejected because its data (last update late 2025) predates every current catalog model; mixing stale scores into rankings would mislead. The ingestion path (benchmarks table + CATEGORY_BENCHMARKS + BENCHMARK_BLURBS) is the extension point when a fresh source appears.

## Grounding enforcement

The recommend LLM receives a fixed candidate list and returns only ids plus short "why" strings. Assembly is deterministic: prices, INR conversion, score columns, and the comparison table come from `ModelRow` objects, never from generated text. Post-generation, `grounding.foreign_model_mentions()` scans all free text for surface forms of every catalog model (name, id, slug tail) and flags any mention outside the candidate set, with span logic so "GPT-5.4" inside "GPT-5.4-mini" does not false-positive. One violation triggers a corrective retry; a second one discards the LLM plan entirely for the deterministic fallback. The eval harness asserts zero violations across all scenarios.

## Retrieval: hybrid BM25 + embeddings

v1 shipped BM25 only; user testing showed vague and Hinglish phrasings ("kitna paisa lagega har mahine") that keyword matching cannot reach, so the default is now a hybrid. Both retrievers run per query and their rankings merge with reciprocal rank fusion (1/(60+rank) per list), which needs no score normalization. Embeddings come from the same OpenAI-compatible endpoint as the chat model (nomic-embed-text via Ollama); document vectors cache on disk keyed by content hash, so the corpus embeds once. Everything sits behind the `Retriever` protocol (`search`, `get`); `RETRIEVER_BACKEND` selects bm25, embedding, or hybrid, and the factory degrades to BM25 with a log line if the embedding model is unavailable. Deterministic doc pulls (`get` by name) never involve either ranker.

## Web search

The catalog rule ("if it is not in the DB, it does not exist") stays absolute for picks, but users ask about models we do not carry, and stonewalling them tested badly. A `web_lookup` node detects model-ish names that resolve to nothing in the catalog (full hyphenated chains, so `claude-sonnet-5` resolves and `SuperGPT-9000` does not) and runs a DuckDuckGo search (ddgs, no API key, `WEB_SEARCH=off` to disable). Findings enter the turn's context as labeled `[web search: ...]` chunks and the user gets a deterministic sentence with the top source URL. The catalog node also searches when coverage is thin (fewer than 3 candidates survive filtering), so the narration can honestly acknowledge options the catalog lacks. The grounding boundary is unchanged in both cases: web results inform narration, never picks.

## Activity streaming

Users need to see what the agent is doing during slow local-model turns. Nodes append plain-language lines to `state.activity` ("Reading knowledge base: guides/gpu-hosting", "Searching the web: ..."); `POST /chat/stream` re-emits them as SSE events by diffing activity after each LangGraph node completes (`stream_mode="values"`), then sends a final event with the full payload. The frontend renders the lines live and dims them once the reply arrives. Plain `POST /chat` remains as the fallback transport.

## Context budget and latency strategy for small models

The serving model may have 8-16k usable tokens and runs on laptop CPU. Discipline applied:

- System prompts are templates under ~350 tokens each; the largest (recommend) stays under ~1,200 with candidates and KB inlined.
- The compact `requirements` object is the durable memory; the model window carries only the last 6 messages, each clipped to 400 chars (long recommendation replies were drowning extraction in user testing).
- Older messages fold into a 2-3 sentence LLM summary (best effort; requirements hold the facts regardless).
- KB docs are injected per turn, trimmed to 1,500 chars each, at most 4 docs, selected deterministically for the turn's purpose.
- Each turn makes 1-2 LLM calls (extract + either clarify or recommend), keeping latency tolerable on a laptop.
- Thinking models: `reasoning_effort=none` disables reasoning tokens (extraction does not need them; they tripled turn time). `keep_alive=30m` prevents Ollama from unloading the model between slow human turns, which was the main cause of late-conversation slowdowns. Both are env-configurable and retried without if a backend rejects them.

## Conversation-repair rules (from user testing)

- `recommend_now` is strictly per-turn. The sticky version replayed stale recommendations at every follow-up.
- Currency conversion is code, not model: extraction returns `budget_amount` + `budget_currency`; a 4B once turned 2000 INR into $2.38.
- Asked questions accumulate in state and are injected as a do-not-repeat list, with a word-overlap check as the backstop; when nothing new is left to ask, the graph recommends instead of interrogating.
- "I am not sure" about deployment maps to `either`, so indecision cannot loop the same question.
- The LLM's pick plan is rank-sanitized: top pick from the top 3, runner-up from the top 4, budget pick strictly cheaper than the top pick; violations are replaced deterministically. The comparison table always leads with the picks.

## Sessions

Cookie-keyed server-side store behind a `SessionStore` protocol; v1 is an in-memory dict with TTL. Page refresh resumes the session; "Start over" deletes it. Persistent per-user memory is a future implementation of the same protocol, not a redesign.

## Freshness pipeline

`ingestion/` refreshes SQLite from three sources, each independently fallible (partial refresh with warnings): OpenRouter models API (pricing, context, modalities), LiveBench release CSVs (per-category scores aggregated to `livebench_*` benchmarks, run variants collapsed to best-of), and the Hugging Face API (param counts for a curated local-model list, with hardcoded fallbacks). Cross-source name matching uses a normalizer plus an explicit alias seed; unmatched names are logged and skipped, never guessed. Snapshots of every fetch are committed, so `--offline` rebuilds the seed DB deterministically. All HTTP uses exponential backoff with jitter, max 3 retries, transient-only; 404s and schema changes fail fast. The app reads the local DB only and surfaces `last_refresh` age in the UI.

## Extension points

- **New model backend**: change `OPENAI_BASE_URL` and `MODEL_NAME` in `.env`, run `make eval`. Nothing else.
- **Embedding retriever**: implement `Retriever` over the same KB, swap in `web/app.py`.
- **New data source**: add a module in `ingestion/` following the openrouter/livebench pattern (fetch, snapshot, upsert, meta timestamp) and register it in `refresh.py`.
- **New benchmark for ranking**: ingest rows into `benchmarks`, map it in `catalog.CATEGORY_BENCHMARKS`, add a KB explainer doc.
- **Persistent sessions**: implement `SessionStore` over SQLite; the web layer stays unchanged.
- **SSE streaming**: v1 uses plain request/response because each turn is 1-2 short internal LLM calls, not one long generation; a streaming variant would wrap the final narration only.
