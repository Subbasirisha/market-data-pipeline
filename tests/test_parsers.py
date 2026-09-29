from datetime import UTC, date, datetime
from decimal import Decimal

from market_pipeline.parsers import parse_alpha_vantage, parse_coingecko


def test_parse_coingecko_joins_lists_on_timestamp():
    payload = {
        "prices": [[1790522700000, 84556.1], [1790523000000, 84600.5]],
        "market_caps": [[1790522700000, 1.67e12]],  # second point has no market cap
        "total_volumes": [[1790522700000, 3.1e10], [1790523000000, 3.2e10]],
    }

    rows = parse_coingecko("bitcoin", payload)

    assert len(rows) == 2
    first = rows[0]
    assert first.coin_id == "bitcoin"
    assert first.price_ts == datetime(2026, 9, 27, 15, 25, tzinfo=UTC)
    assert first.price_usd == Decimal("84556.1")  # exact, not 84556.100000000005...
    assert first.market_cap_usd == Decimal("1670000000000.0")
    assert rows[1].market_cap_usd is None


def test_parse_coingecko_collapses_duplicate_timestamps():
    payload = {"prices": [[1790522700000, 1.0], [1790522700000, 2.0]]}

    rows = parse_coingecko("bitcoin", payload)

    assert [r.price_usd for r in rows] == [Decimal("2.0")]


def test_parse_alpha_vantage_converts_strings_to_types():
    payload = {
        "Time Series (Daily)": {
            "2026-09-25": {
                "1. open": "227.10",
                "2. high": "229.50",
                "3. low": "226.00",
                "4. close": "228.75",
                "5. volume": "41234567",
            }
        }
    }

    [row] = parse_alpha_vantage("AAPL", payload)

    assert row.trade_date == date(2026, 9, 25)
    assert row.close == Decimal("228.75")
    assert row.volume == 41234567
