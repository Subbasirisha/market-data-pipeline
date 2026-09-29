"""Generate small, deterministic raw files for CI (no API calls, no real market data).

    python ci/make_fixtures.py   # writes ci/fixtures/raw/

CI loads these with the real loader, then runs `dbt build` on the result. Enough rows
are generated to exercise every model: 30 trading days (so the 20-day moving average
fills in) and 48 five-minute crypto points (spanning several hours).
"""

import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from market_pipeline.landing import RawRecord, write_raw

ROOT = Path(__file__).parent / "fixtures" / "raw"
EXTRACTED_AT = datetime(2026, 9, 1, 12, tzinfo=UTC)


def crypto_payload(start: datetime, base_price: float, points: int) -> dict:
    prices, caps, volumes = [], [], []
    for i in range(points):
        ts = int((start + timedelta(minutes=5 * i)).timestamp() * 1000)
        price = round(base_price * (1 + 0.001 * ((i % 7) - 3)), 2)  # gentle zig-zag
        prices.append([ts, price])
        caps.append([ts, price * 19_000_000])
        volumes.append([ts, 30_000_000_000.0])
    return {"prices": prices, "market_caps": caps, "total_volumes": volumes}


def stock_payload(first_day: date, base_close: float, days: int) -> dict:
    series, day = {}, first_day
    while len(series) < days:
        if day.weekday() < 5:  # trading days only
            close = round(base_close * (1 + 0.01 * ((len(series) % 5) - 2)), 2)
            series[day.isoformat()] = {
                "1. open": f"{close - 1:.2f}",
                "2. high": f"{close + 2:.2f}",
                "3. low": f"{close - 2:.2f}",
                "4. close": f"{close:.2f}",
                "5. volume": str(40_000_000 + len(series) * 1000),
            }
        day += timedelta(days=1)
    return {"Meta Data": {"2. Symbol": "TEST"}, "Time Series (Daily)": series}


def main() -> None:
    shutil.rmtree(ROOT, ignore_errors=True)
    start = datetime(2026, 9, 1, 8, tzinfo=UTC)
    for coin, price in [("bitcoin", 84000.0), ("ethereum", 2700.0)]:
        write_raw(ROOT, RawRecord("coingecko", coin, {"fixture": True},
                                  crypto_payload(start, price, 48), EXTRACTED_AT))
    for symbol, close in [("AAPL", 330.0), ("MSFT", 500.0)]:
        write_raw(ROOT, RawRecord("alpha_vantage", symbol, {"fixture": True},
                                  stock_payload(date(2026, 7, 20), close, 30), EXTRACTED_AT))
    print(f"wrote {sum(1 for _ in ROOT.rglob('*.json'))} files to {ROOT}")


if __name__ == "__main__":
    main()
