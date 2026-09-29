"""Load raw landed files into Postgres, incrementally and idempotently.

Usage:  python -m market_pipeline.load

  - Incremental: only files not yet listed in raw.loaded_files are processed.
  - Idempotent:  rows are upserted, so even re-loading a file never duplicates data.
  - Atomic per file: a file's rows and its manifest entry are committed in one
    transaction. A crash mid-file leaves no partial data, and the file is retried next run.
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from market_pipeline import db
from market_pipeline.config import load_settings
from market_pipeline.parsers import parse_alpha_vantage, parse_coingecko

log = logging.getLogger(__name__)

# source name (as written by the extract step) -> (parser, upsert function)
HANDLERS = {
    "coingecko": (parse_coingecko, db.upsert_crypto),
    "alpha_vantage": (parse_alpha_vantage, db.upsert_stocks),
}


@dataclass
class LoadSummary:
    files_loaded: int = 0
    rows_upserted: int = 0
    failed: dict[str, str] = field(default_factory=dict)  # file path -> error

    @property
    def ok(self) -> bool:
        return not self.failed


def pending_files(conn: psycopg.Connection, raw_root: Path) -> list[Path]:
    already_loaded = db.loaded_file_paths(conn)
    # Sorted, so files load in the order they were extracted (the path ends in date/time).
    return [
        path
        for path in sorted(raw_root.rglob("*.json"))
        if path.relative_to(raw_root).as_posix() not in already_loaded
    ]


def load_file(conn: psycopg.Connection, raw_root: Path, path: Path) -> int:
    envelope = json.loads(path.read_text())
    source, entity = envelope["source"], envelope["entity"]
    parse, upsert = HANDLERS[source]
    rows = parse(entity, envelope["payload"])
    # Store paths relative to the raw root, so the manifest stays valid if the data
    # directory moves (e.g. mounted at a different path inside a Docker container).
    rel_path = path.relative_to(raw_root).as_posix()

    with conn.transaction():
        count = upsert(conn, rows, rel_path)
        db.record_loaded_file(conn, rel_path, source, entity, count)
    return count


def run_load(conn: psycopg.Connection, raw_root: Path) -> LoadSummary:
    db.ensure_schema(conn)
    summary = LoadSummary()
    files = pending_files(conn, raw_root)
    log.info("%d new file(s) to load from %s", len(files), raw_root)

    for path in files:
        try:
            count = load_file(conn, raw_root, path)
        except Exception as exc:  # noqa: BLE001 - record and continue with the next file
            log.error("FAILED %s: %s", path, exc)
            summary.failed[str(path)] = str(exc)
        else:
            log.info("loaded %s (%d rows)", path, count)
            summary.files_loaded += 1
            summary.rows_upserted += count

    log.info(
        "load done: %d file(s), %d row(s) upserted, %d failed",
        summary.files_loaded,
        summary.rows_upserted,
        len(summary.failed),
    )
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    with db.connect(settings.postgres_dsn) as conn:
        summary = run_load(conn, settings.raw_data_dir)
    return 0 if summary.ok else 1


if __name__ == "__main__":
    sys.exit(main())
