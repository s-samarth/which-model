"""Refresh orchestrator: `python -m ingestion.refresh [--offline] [--db PATH]`.

Runs each source independently. A failed source logs a warning and the refresh
continues (partial refresh); the exit code is non-zero only if every source
failed. Offline mode rebuilds the DB from bundled snapshots, no network.
"""

import argparse
import logging
import sys
from pathlib import Path

from ingestion import livebench, local_models, openrouter
from ingestion.schema import connect, set_meta, utcnow

log = logging.getLogger("ingestion.refresh")


def run(db_path: Path, offline: bool = False) -> dict[str, bool]:
    """Refresh all sources into db_path. Returns per-source success flags."""
    conn = connect(db_path)
    results: dict[str, bool] = {}

    try:
        models = openrouter.fetch(offline=offline)
        openrouter.upsert(conn, models)
        set_meta(conn, "refresh_openrouter", utcnow())
        results["openrouter"] = True
    except Exception as err:
        log.error("openrouter refresh failed: %s", err)
        results["openrouter"] = False

    try:
        local_models.upsert(conn, offline=offline)
        set_meta(conn, "refresh_local_models", utcnow())
        results["local_models"] = True
    except Exception as err:
        log.error("local models refresh failed: %s", err)
        results["local_models"] = False

    try:
        release, table, cats = livebench.fetch(offline=offline)
        livebench.upsert(conn, release, table, cats)
        set_meta(conn, "refresh_livebench", utcnow())
        set_meta(conn, "livebench_release", release)
        results["livebench"] = True
    except Exception as err:
        log.error("livebench refresh failed: %s", err)
        results["livebench"] = False

    if any(results.values()):
        set_meta(conn, "last_refresh", utcnow())
    conn.commit()
    conn.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the model catalog database.")
    parser.add_argument("--offline", action="store_true",
                        help="rebuild from bundled snapshots, no network")
    parser.add_argument("--db", type=Path, default=Path("data/models.db"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    results = run(args.db, offline=args.offline)
    failed = [s for s, ok in results.items() if not ok]
    if failed:
        log.warning("partial refresh, failed sources: %s", ", ".join(failed))
    if not any(results.values()):
        log.error("refresh failed: no source succeeded")
        return 1
    log.info("refresh complete: %s", ", ".join(f"{s}={'ok' if ok else 'FAILED'}"
                                               for s, ok in results.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
