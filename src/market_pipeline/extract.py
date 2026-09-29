"""Run every extractor and land the raw results.

Usage:  python -m market_pipeline.extract

Design choice: one failing entity (say, a bad stock symbol) must not stop the others
from being extracted, so failures are collected and reported at the end. The process
still exits non-zero if anything failed, so a scheduler like Airflow or cron sees the failure.
"""

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from market_pipeline.config import Settings, load_settings
from market_pipeline.http import Throttle, build_session
from market_pipeline.landing import RawRecord, write_raw
from market_pipeline.sources import alpha_vantage, coingecko

log = logging.getLogger(__name__)

# Minimum seconds between calls to each API (free tiers):
#   Alpha Vantage documents ~1 request/second, but 1.5s gaps still tripped its burst limit
#   in practice, so leave generous headroom. CoinGecko's public API allows ~5-30 requests/minute.
MIN_INTERVAL_SECONDS = {"coingecko": 2.0, "alpha_vantage": 3.0}


@dataclass
class ExtractSummary:
    written: list[Path] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)  # "source:entity" -> error

    @property
    def ok(self) -> bool:
        return not self.failed


# (source, entity, function that fetches one RawRecord)
Job = tuple[str, str, Callable[[], RawRecord]]


def run_extract(settings: Settings) -> ExtractSummary:
    """Latest data for every configured coin and stock (the CLI / Docker entrypoint)."""
    session = build_session()
    return _run_jobs(
        settings,
        [
            ("coingecko", coin, lambda c=coin: coingecko.extract(session, c))
            for coin in settings.crypto_ids
        ]
        + _stock_jobs(settings, session),
    )


def run_stock_extract(settings: Settings) -> ExtractSummary:
    """Latest daily bars for every configured stock."""
    return _run_jobs(settings, _stock_jobs(settings, build_session()))


def run_crypto_interval_extract(
    settings: Settings, start: datetime, end: datetime
) -> ExtractSummary:
    """Crypto prices for exactly [start, end): what a scheduled or backfilled run asks for."""
    session = build_session()
    return _run_jobs(
        settings,
        [
            ("coingecko", coin, lambda c=coin: coingecko.extract_range(session, c, start, end))
            for coin in settings.crypto_ids
        ],
    )


def _stock_jobs(settings: Settings, session) -> list[Job]:
    return [
        (
            "alpha_vantage",
            symbol,
            lambda s=symbol: alpha_vantage.extract(session, s, settings.alpha_vantage_api_key),
        )
        for symbol in settings.stock_symbols
    ]


def _run_jobs(settings: Settings, jobs: list[Job]) -> ExtractSummary:
    summary = ExtractSummary()
    throttles = {source: Throttle(gap) for source, gap in MIN_INTERVAL_SECONDS.items()}

    for source, entity, job in jobs:
        throttles[source].wait()
        try:
            path = write_raw(settings.raw_data_dir, job())
        except Exception as exc:  # noqa: BLE001 - record and continue with the next entity
            log.error("FAILED %s:%s: %s", source, entity, exc)
            summary.failed[f"{source}:{entity}"] = str(exc)
        else:
            log.info("wrote %s", path)
            summary.written.append(path)

    log.info("extract done: %d written, %d failed", len(summary.written), len(summary.failed))
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    summary = run_extract(load_settings())
    return 0 if summary.ok else 1


if __name__ == "__main__":
    sys.exit(main())
