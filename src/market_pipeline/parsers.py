"""Turn raw API payloads into typed rows. Pure functions: no I/O, easy to unit test.

Money values are parsed as Decimal, not float: floats can't represent most decimal
fractions exactly (0.1 + 0.2 != 0.3), which is unacceptable for prices.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class CryptoPrice:
    coin_id: str
    price_ts: datetime
    price_usd: Decimal
    market_cap_usd: Decimal | None
    volume_usd: Decimal | None


@dataclass(frozen=True)
class StockPriceDaily:
    symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def _dec(value: Any) -> Decimal | None:
    # str() first: Decimal(0.1) gives 0.1000000000000000055..., Decimal("0.1") gives 0.1
    return None if value is None else Decimal(str(value))


def parse_coingecko(coin_id: str, payload: dict[str, Any]) -> list[CryptoPrice]:
    """CoinGecko sends three parallel lists of [epoch_ms, value]; join them on timestamp."""
    caps = {ts: v for ts, v in payload.get("market_caps", [])}
    volumes = {ts: v for ts, v in payload.get("total_volumes", [])}
    rows = {}
    for ts_ms, price in payload["prices"]:
        if price is None:
            continue
        # Keyed by timestamp, so a duplicated point in one response collapses to one row.
        rows[ts_ms] = CryptoPrice(
            coin_id=coin_id,
            price_ts=datetime.fromtimestamp(ts_ms / 1000, tz=UTC),
            price_usd=_dec(price),
            market_cap_usd=_dec(caps.get(ts_ms)),
            volume_usd=_dec(volumes.get(ts_ms)),
        )
    return list(rows.values())


def parse_alpha_vantage(symbol: str, payload: dict[str, Any]) -> list[StockPriceDaily]:
    """Alpha Vantage sends {"2026-09-25": {"1. open": "227.10", ...}, ...} with string values."""
    return [
        StockPriceDaily(
            symbol=symbol,
            trade_date=date.fromisoformat(day),
            open=Decimal(bar["1. open"]),
            high=Decimal(bar["2. high"]),
            low=Decimal(bar["3. low"]),
            close=Decimal(bar["4. close"]),
            volume=int(bar["5. volume"]),
        )
        for day, bar in payload["Time Series (Daily)"].items()
    ]
