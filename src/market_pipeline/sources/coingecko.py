"""CoinGecko: free crypto prices, no API key required.

Two endpoints, same response shape:
  /coins/{id}/market_chart?vs_currency=usd&days=1
      the last N days, relative to *now*
  /coins/{id}/market_chart/range?vs_currency=usd&from=<unix s>&to=<unix s>
      a fixed time window: the same request always asks for the same data,
      which is what makes scheduled runs and backfills reproducible

    {"prices": [[1727510400000, 65123.4], ...], "market_caps": [...], "total_volumes": [...]}
Timestamps are Unix epoch *milliseconds*.

Granularity is decided by CoinGecko, not by us: data from the last ~24 hours comes back
~5 minutes apart, while older data is hourly. So a live hourly run gets ~13 points, but a
backfill of last week gets 2 (both ends of the hour, inclusive).
"""

from datetime import UTC, datetime
from typing import Any

import requests

from market_pipeline.landing import RawRecord

BASE_URL = "https://api.coingecko.com/api/v3"


def _fetch(session: requests.Session, coin_id: str, path: str, params: dict[str, Any]) -> RawRecord:
    response = session.get(f"{BASE_URL}/coins/{coin_id}/{path}", params=params)
    response.raise_for_status()
    payload = response.json()

    if "prices" not in payload:
        raise ValueError(f"CoinGecko response for {coin_id!r} has no 'prices': {payload}")

    return RawRecord(
        source="coingecko",
        entity=coin_id,
        request_params=params,
        payload=payload,
        extracted_at=datetime.now(UTC),
    )


def extract(session: requests.Session, coin_id: str, days: int = 1) -> RawRecord:
    return _fetch(session, coin_id, "market_chart", {"vs_currency": "usd", "days": days})


def extract_range(
    session: requests.Session, coin_id: str, start: datetime, end: datetime
) -> RawRecord:
    params = {"vs_currency": "usd", "from": int(start.timestamp()), "to": int(end.timestamp())}
    return _fetch(session, coin_id, "market_chart/range", params)
