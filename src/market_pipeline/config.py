"""Central configuration, read from environment variables.

Every setting lives in one place, so the rest of the code never calls os.getenv directly.
The same code then runs on a laptop (values from .env), in Docker, or in Airflow
(values from real environment variables) without changes.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _split_csv(value: str) -> list[str]:
    """Turn 'a, b,,c' into ['a', 'b', 'c']."""
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    alpha_vantage_api_key: str
    crypto_ids: list[str]
    stock_symbols: list[str]
    raw_data_dir: Path
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def load_settings() -> Settings:
    # Does not override variables that are already set, so real env vars win over .env.
    load_dotenv()
    return Settings(
        alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY", ""),
        crypto_ids=_split_csv(os.getenv("CRYPTO_IDS", "bitcoin,ethereum")),
        stock_symbols=_split_csv(os.getenv("STOCK_SYMBOLS", "AAPL,MSFT")),
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", "data/raw")),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "market"),
        postgres_user=os.getenv("POSTGRES_USER", "pipeline"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
    )
