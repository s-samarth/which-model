"""Central logging configuration."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging once, with a compact single-line format."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )
    # Quiet noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
