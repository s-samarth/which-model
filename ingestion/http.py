"""HTTP helpers with exponential backoff and jitter.

Transient failures (timeouts, 429, 5xx) are retried up to MAX_RETRIES times.
Non-transient failures (404, 4xx) raise immediately so callers fail fast.
"""

import logging
import random
import time

import httpx

log = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY_S = 1.0
TIMEOUT_S = 30.0

TRANSIENT_STATUS = {429, 500, 502, 503, 504}


class SourceUnavailable(Exception):
    """Raised when a source stays unreachable after retries (transient exhausted)."""


class SourceSchemaError(Exception):
    """Raised when a source responds but the payload does not look as expected."""


def get_with_backoff(url: str, *, headers: dict | None = None) -> httpx.Response:
    """GET a URL, retrying transient failures with exponential backoff + jitter."""
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = httpx.get(url, headers=headers, timeout=TIMEOUT_S, follow_redirects=True)
            if resp.status_code in TRANSIENT_STATUS:
                raise httpx.HTTPStatusError(
                    f"transient status {resp.status_code}", request=resp.request, response=resp
                )
            resp.raise_for_status()  # non-transient 4xx raises HTTPStatusError, caught below
            return resp
        except (httpx.TimeoutException, httpx.TransportError) as err:
            last_err = err
        except httpx.HTTPStatusError as err:
            if err.response.status_code in TRANSIENT_STATUS:
                last_err = err
            else:
                # Fail fast: 404 / schema-level problems are not retryable.
                raise
        if attempt < MAX_RETRIES:
            delay = BASE_DELAY_S * (2**attempt) + random.uniform(0, 0.5)
            log.warning("GET %s failed (%s), retry %d/%d in %.1fs",
                        url, last_err, attempt + 1, MAX_RETRIES, delay)
            time.sleep(delay)
    raise SourceUnavailable(f"GET {url} failed after {MAX_RETRIES} retries: {last_err}")
