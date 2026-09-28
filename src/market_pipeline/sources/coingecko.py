"""CoinGecko: free crypto prices, no API key required.

Endpoint: /coins/{id}/market_chart?vs_currency=usd&days=1
Returns price, market cap and volume points for the last 24 hours (~5 min apart):
    {"prices": [[1727510400000, 65123.4], ...], "market_caps": [...], "total_volumes": [...]}
Timestamps are Unix epoch *milliseconds*.
"""

from datetime import UTC, datetime

import requests

from market_pipeline.landing import RawRecord

BASE_URL = "https://api.coingecko.com/api/v3"


def extract(session: requests.Session, coin_id: str, days: int = 1) -> RawRecord:
    params = {"vs_currency": "usd", "days": days}
    response = session.get(f"{BASE_URL}/coins/{coin_id}/market_chart", params=params)
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
