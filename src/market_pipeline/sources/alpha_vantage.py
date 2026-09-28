"""Alpha Vantage: daily stock prices (free key, 25 requests/day).

Endpoint: /query?function=TIME_SERIES_DAILY&symbol=AAPL&outputsize=compact
Returns the last 100 trading days:
    {"Meta Data": {...}, "Time Series (Daily)": {"2026-09-25": {"1. open": "227.1", ...}}}

Gotcha: when you hit the rate limit, Alpha Vantage still returns HTTP 200 OK,
with a body like {"Information": "...rate limit..."} or {"Note": "..."}.
A naive pipeline would save that as if it were data. Always check the body,
not just the status code.
"""

from datetime import UTC, datetime

import requests

from market_pipeline.landing import RawRecord

BASE_URL = "https://www.alphavantage.co/query"
SERIES_KEY = "Time Series (Daily)"


class AlphaVantageError(RuntimeError):
    """The API answered 200 OK but the body is an error or rate-limit message."""


def extract(session: requests.Session, symbol: str, api_key: str) -> RawRecord:
    if not api_key:
        raise AlphaVantageError("ALPHA_VANTAGE_API_KEY is not set (see .env.example)")

    params = {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"}
    # The key goes in the request but NOT in request_params, so it never lands on disk.
    response = session.get(BASE_URL, params={**params, "apikey": api_key})
    response.raise_for_status()
    payload = response.json()

    if SERIES_KEY not in payload:
        message = (
            payload.get("Error Message") or payload.get("Information") or payload.get("Note")
        )
        raise AlphaVantageError(f"No data for {symbol!r}: {message or payload}")

    return RawRecord(
        source="alpha_vantage",
        entity=symbol,
        request_params=params,
        payload=payload,
        extracted_at=datetime.now(UTC),
    )
