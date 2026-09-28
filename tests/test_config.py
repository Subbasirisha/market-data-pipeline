from market_pipeline.config import _split_csv, load_settings


def test_split_csv_trims_and_drops_empty_items():
    assert _split_csv(" bitcoin, ethereum,,solana ") == ["bitcoin", "ethereum", "solana"]


def test_env_vars_override_defaults(monkeypatch):
    monkeypatch.setenv("STOCK_SYMBOLS", "TSLA,AMZN")
    monkeypatch.setenv("POSTGRES_PORT", "6543")

    settings = load_settings()

    assert settings.stock_symbols == ["TSLA", "AMZN"]
    assert settings.postgres_port == 6543
    assert ":6543/" in settings.postgres_dsn
