import pytest
import responses

from market_pipeline.http import build_session
from market_pipeline.sources import alpha_vantage, coingecko

CG_URL = f"{coingecko.BASE_URL}/coins/bitcoin/market_chart"


@responses.activate
def test_coingecko_returns_raw_record():
    body = {"prices": [[1727510400000, 65000.0]], "market_caps": [], "total_volumes": []}
    responses.get(CG_URL, json=body)

    record = coingecko.extract(build_session(), "bitcoin")

    assert record.source == "coingecko"
    assert record.entity == "bitcoin"
    assert record.payload == body


@responses.activate
def test_session_retries_after_server_error():
    # First call fails with 503, second succeeds: the retry should hide the blip.
    responses.get(CG_URL, status=503)
    responses.get(CG_URL, json={"prices": []})

    record = coingecko.extract(build_session(backoff_factor=0), "bitcoin")

    assert record.payload == {"prices": []}
    assert len(responses.calls) == 2


@responses.activate
def test_alpha_vantage_rate_limit_with_200_status_is_an_error():
    responses.get(alpha_vantage.BASE_URL, json={"Information": "rate limit is 25 requests per day"})

    with pytest.raises(alpha_vantage.AlphaVantageError, match="rate limit"):
        alpha_vantage.extract(build_session(), "AAPL", api_key="test-key")


@responses.activate
def test_alpha_vantage_api_key_not_saved_in_record():
    responses.get(alpha_vantage.BASE_URL, json={"Time Series (Daily)": {}})

    record = alpha_vantage.extract(build_session(), "AAPL", api_key="secret-123")

    assert "secret-123" not in record.to_json()


def test_alpha_vantage_requires_api_key():
    with pytest.raises(alpha_vantage.AlphaVantageError, match="not set"):
        alpha_vantage.extract(build_session(), "AAPL", api_key="")
