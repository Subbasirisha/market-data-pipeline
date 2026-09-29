"""Shared HTTP session with timeouts and automatic retries.

APIs fail in two common ways:
  - transient errors (500/502/503/504, dropped connections): usually fine if you retry
  - rate limiting (429 Too Many Requests): fine if you wait and then retry
urllib3's Retry handles both, with exponential backoff (wait 1s, 2s, 4s, ...) and
by honouring the server's Retry-After header when it sends one.
"""

import time
from collections.abc import Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT_SECONDS = 30


class TimeoutSession(requests.Session):
    """A Session that never waits forever. requests has no timeout by default."""

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT_SECONDS)
        return super().request(*args, **kwargs)


def build_session(total_retries: int = 5, backoff_factor: float = 1.0) -> requests.Session:
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),  # only retry idempotent requests
        respect_retry_after_header=True,
    )
    session = TimeoutSession()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = "market-data-pipeline/0.1"
    return session


class Throttle:
    """Enforce a minimum gap between calls, so we stay under an API's rate limit.

    Retries handle rate limits *after* we hit them; a throttle avoids hitting them at all.
    Needed for Alpha Vantage in particular, which reports rate limits as 200 OK
    (so urllib3's Retry never sees a 429 to retry on).
    """

    def __init__(
        self,
        min_interval_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.min_interval = min_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_call: float | None = None

    def wait(self) -> None:
        if self._last_call is not None:
            remaining = self.min_interval - (self._clock() - self._last_call)
            if remaining > 0:
                self._sleep(remaining)
        self._last_call = self._clock()
