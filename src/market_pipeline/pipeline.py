"""Run the whole pipeline: extract, then load.

Usage:  python -m market_pipeline.pipeline

The load step runs even if some extracts failed: whatever did land should still reach
the database. The exit code is non-zero if either step had failures, so the scheduler
still flags the run.
"""

import logging
import sys

from market_pipeline import db
from market_pipeline.config import load_settings
from market_pipeline.extract import run_extract
from market_pipeline.load import run_load

log = logging.getLogger(__name__)


def run_pipeline() -> bool:
    settings = load_settings()
    extract_summary = run_extract(settings)
    with db.connect(settings.postgres_dsn) as conn:
        load_summary = run_load(conn, settings.raw_data_dir)
    return extract_summary.ok and load_summary.ok


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return 0 if run_pipeline() else 1


if __name__ == "__main__":
    sys.exit(main())
