"""Ingest LiveBench release scores.

LiveBench publishes a per-task CSV per release (table_YYYY_MM_DD.csv) plus a
task-to-category mapping (categories_YYYY_MM_DD.json) on livebench.ai. We
aggregate task scores into category means, collapse run variants (thinking /
effort levels) to the best score per base model, and store rows as
`livebench_<category>` benchmarks.
"""

import csv
import io
import json
import logging
import re
import sqlite3
from pathlib import Path

from ingestion import aliases
from ingestion.http import get_with_backoff

log = logging.getLogger(__name__)

BASE_URL = "https://livebench.ai"
# Known-good release, bumped when LiveBench ships a new one (see docs/RUNBOOK.md).
FALLBACK_RELEASE = "2026-01-08"
SNAP_DIR = Path(__file__).parent / "snapshots"


def discover_release() -> str:
    """Find the current release date by scraping the site bundle; fall back if it moves."""
    try:
        html = get_with_backoff(BASE_URL).text
        js_path = re.search(r'src="\./(static/js/main\.[a-z0-9]+\.js)"', html)
        if js_path:
            bundle = get_with_backoff(f"{BASE_URL}/{js_path.group(1)}").text
            versions = re.findall(r"LiveBench-(\d{4}-\d{2}-\d{2})", bundle)
            if versions:
                return max(versions)
    except Exception as err:  # any scrape failure falls back to the pinned release
        log.warning("livebench release discovery failed (%s), using %s", err, FALLBACK_RELEASE)
    return FALLBACK_RELEASE


def fetch(offline: bool = False) -> tuple[str, list[dict], dict[str, list[str]]]:
    """Return (release_date, table_rows, category_map), from web or snapshots."""
    if offline:
        release = json.loads((SNAP_DIR / "livebench_meta.json").read_text())["release"]
        table = list(csv.DictReader((SNAP_DIR / "livebench_table.csv").open()))
        cats = json.loads((SNAP_DIR / "livebench_categories.json").read_text())
        return release, table, cats
    release = discover_release()
    tag = release.replace("-", "_")
    table_text = get_with_backoff(f"{BASE_URL}/table_{tag}.csv").text
    cats = get_with_backoff(f"{BASE_URL}/categories_{tag}.json").json()
    table = list(csv.DictReader(io.StringIO(table_text)))
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    (SNAP_DIR / "livebench_table.csv").write_text(table_text)
    (SNAP_DIR / "livebench_categories.json").write_text(json.dumps(cats, indent=1))
    (SNAP_DIR / "livebench_meta.json").write_text(json.dumps({"release": release}))
    return release, table, cats


def _category_scores(row: dict, cats: dict[str, list[str]]) -> dict[str, float]:
    """Mean per category over the tasks present in the row, plus a global mean."""
    out: dict[str, float] = {}
    cat_means = []
    for cat, tasks in cats.items():
        vals = []
        for t in tasks:
            raw = row.get(t, "")
            try:
                vals.append(float(raw))
            except (TypeError, ValueError):
                continue
        if vals:
            mean = sum(vals) / len(vals)
            key = "livebench_" + cat.lower().replace(" ", "_")
            out[key] = round(mean, 2)
            cat_means.append(mean)
    if cat_means:
        out["livebench_global"] = round(sum(cat_means) / len(cat_means), 2)
    return out


def upsert(conn: sqlite3.Connection, release: str, table: list[dict],
           cats: dict[str, list[str]]) -> int:
    """Aggregate, collapse variants to best score, resolve names, upsert. Returns rows."""
    slug_index = aliases.build_slug_index(conn)
    best: dict[str, dict[str, float]] = {}  # model_id -> benchmark -> max score
    unmatched: set[str] = set()
    for row in table:
        name = row.get("model", "")
        model_id = aliases.resolve(conn, name, slug_index)
        if model_id is None:
            unmatched.add(aliases.normalize(name))
            continue
        aliases.remember(conn, name, model_id)
        scores = _category_scores(row, cats)
        target = best.setdefault(model_id, {})
        for bench, score in scores.items():
            target[bench] = max(target.get(bench, 0.0), score)
    written = 0
    for model_id, scores in best.items():
        for bench, score in scores.items():
            conn.execute(
                "INSERT INTO benchmarks(model_id, benchmark, score, source, as_of_date) "
                "VALUES(?,?,?,?,?) ON CONFLICT(model_id, benchmark) DO UPDATE SET "
                "score=excluded.score, source=excluded.source, as_of_date=excluded.as_of_date",
                (model_id, bench, score, f"livebench.ai release {release}", release),
            )
            written += 1
    conn.commit()
    if unmatched:
        log.warning("livebench: %d unmatched model names (skipped): %s",
                    len(unmatched), ", ".join(sorted(unmatched)))
    log.info("livebench: %d benchmark rows for %d models (release %s)",
             written, len(best), release)
    return written
