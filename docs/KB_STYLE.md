# Knowledge Base Style Guide

The `kb/` corpus is a product component, not documentation. It is what makes a 4B serving model useful: retrieved chunks are injected into its context to ground questions and recommendations. Write accordingly.

## File anatomy

```markdown
---
category: taxonomy | benchmark | guide | regional
tags: [words, a, user, would, type]
updated: YYYY-MM-DD
---

# Title

## Section
Short, factual prose.
```

- **category** drives filtered retrieval; exactly one of the four values.
- **tags** are retrieval fuel: BM25 boosts them heavily. Use the vocabulary of user messages ("offline", "receipts", "rupee"), not ours ("inference", "modality").
- **updated** is the review date; bump it whenever you touch the file.
- Filename is the slug; the agent references docs as `category-dir/slug`.

## Writing rules

1. **Small models read this.** Short sentences. Concrete numbers over adjectives. No tables of more than a few rows; prose compresses better in a tight context window.
2. **Budget ~500 words per doc.** Docs are trimmed to 1,500 characters when injected; front-load the parts that must survive (what it is, how to read it, the numbers).
3. **Facts must earn their place.** Every claim either is stable knowledge, comes from the catalog (then say "in our catalog"), or carries a VERIFY marker (below).
4. **Anchor jargon immediately.** "32k tokens (about 50 pages)". The agent quotes these anchors to users verbatim.
5. **Point at catalog data, never restate it.** Write "rank by livebench_coding", never "GPT-X scores 74", because prices and scores in prose go stale and the model might parrot them.
6. **Taxonomy docs need example phrasings.** The router and retrieval lean on 2-3 realistic user quotes per task doc.
7. No em dashes, matching the repo-wide documentation rule.

## The VERIFY convention

Time-sensitive or uncertain claims carry an inline HTML comment so they are grep-able and invisible to users:

```markdown
Frontier agents score 45-65% as of mid 2026. <!-- VERIFY current scores -->
```

- Add VERIFY when writing anything that will drift: leaderboard states, pricing plans, provider lineups, exchange rates.
- Review cadence: `grep -rn "VERIFY" kb/` monthly, or when a refresh log or user report contradicts a doc. Fix the fact, bump `updated`, remove the marker only if the claim became stable.
- Never resolve a VERIFY by asserting from memory; check the primary source.

## Adding or changing docs

Checklist (also in [RUNBOOK.md](RUNBOOK.md)):

1. Write the doc following the anatomy above.
2. New taxonomy doc: register it in `TASK_DOC` in `whichmodel/agent/nodes_elicit.py`.
3. Add a retrieval routing test (`tests/test_retrieval.py`): a realistic query must surface the doc in the top 3.
4. `make test`, then commit the doc and test together.
