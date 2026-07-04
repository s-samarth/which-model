# Runbook

Operational recipes for keeping the recommender honest.

## A data source broke

Symptoms: `make refresh-data` logs `<source> refresh failed` or `partial refresh`.

1. The refresh is partial by design: other sources still updated, the app keeps serving the last good data, and the footer shows its age. Nothing is on fire.
2. Reproduce with detail: `uv run python -m ingestion.refresh --db /tmp/scratch.db`.
3. Diagnose by source:
   - **openrouter**: check `curl -s https://openrouter.ai/api/v1/models | head`. A schema change raises `SourceSchemaError`; adjust `ingestion/openrouter.py` field mapping.
   - **livebench**: release discovery scrapes livebench.ai for `LiveBench-YYYY-MM-DD` and derives `table_YYYY_MM_DD.csv`. If the site layout changed, update `discover_release()` or pin `FALLBACK_RELEASE` in `ingestion/livebench.py` to the newest working release.
   - **local_models (Hugging Face)**: 401s on gated repos are normal and harmless; the curated fallback param counts apply. Only investigate if every lookup fails (rate limit or network).
4. Worst case, rebuild from bundled snapshots: `make seed` (no network).

## LiveBench shipped a new release

Usually zero-touch: discovery finds the newest date automatically. Verify after the next refresh:

```bash
sqlite3 data/models.db "SELECT value FROM meta WHERE key='livebench_release'"
```

If discovery missed it, set `FALLBACK_RELEASE` in `ingestion/livebench.py` and refresh. Then check the unmatched-names warning in the log (next section).

## Adding a model to the alias map

The refresh log prints `livebench: N unmatched model names (skipped)`. Unmatched means a benchmark row was dropped rather than guessed, which is correct unless you know the mapping.

1. Confirm the target exists in the catalog: `sqlite3 data/models.db "SELECT id FROM models WHERE id LIKE '%<slug>%'"`.
2. Add an entry to `ALIAS_SEED` in `ingestion/aliases.py`. Keys must be the normalized form (lowercase, run-variant suffixes and date stamps stripped; see `normalize()`). Map only genuinely identical base models; version mismatches stay unmatched on purpose.
3. `make refresh-data`, confirm the warning shrank, commit.

## Adding a local model to the curated list

Edit `LOCAL_MODELS` in `ingestion/local_models.py`: catalog id (reuse the OpenRouter id if the model is served there, else `local/<slug>`), HF id, Ollama tag, fallback param count, active params for MoE, context length for local-only entries. Refresh and spot-check:

```bash
sqlite3 data/models.db "SELECT id, param_b, ollama_tag FROM models WHERE available_local=1"
```

## Swapping the serving model

1. Edit `.env`: `MODEL_NAME=<new-tag>` (and `OPENAI_BASE_URL` if the backend moved).
2. `ollama pull <new-tag>` (or equivalent on the new backend).
3. Run the gate: `make eval`. Requirement: at least 12/15 scenarios pass with zero grounding violations.
4. If extraction scenarios fail, the new model likely emits sloppier JSON; check the `structured output invalid` warnings in the server log. The repair loop tolerates occasional slips; systematic failure means the model is too weak for extraction.

## Adding a new benchmark as a ranking signal

Three touch points: ingest rows into the `benchmarks` table (follow `ingestion/livebench.py`; every row needs source and as_of_date), map the task in `catalog.CATEGORY_BENCHMARKS`, and add a plain-language entry to `catalog.BENCHMARK_BLURBS` plus a KB explainer doc. Reject sources whose latest data predates the current model generation; stale scores mixed into rankings mislead (this is why the Aider leaderboard, last updated late 2025, is not ingested).

## Adding a knowledge-base doc

1. Write `kb/<category>/<slug>.md` following [KB_STYLE.md](KB_STYLE.md) (frontmatter: category, tags, updated).
2. Tags drive retrieval: include the words a user would actually type.
3. If it is a new task taxonomy doc, map the enum value in `TASK_DOC` (`whichmodel/agent/nodes_elicit.py`).
4. Add a routing case to `tests/test_retrieval.py` (query -> expected doc) and run `make test`.

## Retrieval looks off after editing KB docs

Embedding vectors cache in `data/kb_embeddings.json` keyed by content hash; edited docs re-embed automatically on next boot. If results still look stale or the file is corrupt, delete it and restart. To rule the embedding side out entirely, set `RETRIEVER_BACKEND=bm25` and compare.

## Web search misbehaving

`WEB_SEARCH=off` disables it entirely (the agent then simply says a model is not in its catalog). Search only triggers for unknown model-ish names or explicit "search the web" requests; if it fires too often, tighten `_MODELISH_RE` or `_NOISE` in `whichmodel/tools/websearch.py` and add a regression case to `tests/test_web.py`.

## Ollama is down or slow

The chat degrades cleanly: the user gets "I hit a problem talking to my reasoning model" plus the data age, and the session survives. Check `ollama ps`, restart with `ollama serve`. Slow first reply after idle is model load, not a bug. On fanless laptops, sustained sessions throttle; expect it.

## Session weirdness

Sessions are in-memory with a TTL (default 1h): a server restart or expiry silently starts fresh, which is acceptable v1 behavior. "Start over" in the UI does the same on demand.
