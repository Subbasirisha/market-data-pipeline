"""Raw landing zone: save API responses exactly as received, before any processing.

Why keep raw data?
  - Replay: if a bug is found in the load/transform step, fix it and reprocess the
    saved files, with no need to call the API again (some APIs only serve recent data).
  - Debugging/auditing: you can always see exactly what the source sent.

Files are partitioned Hive-style:  <root>/<source>/<entity>/dt=YYYY-MM-DD/<HHMMSS>.json
The same layout is used by data lakes on S3, so tools like Spark or Athena can
skip whole days of data when filtering by date ("partition pruning").
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    source: str  # e.g. "coingecko"
    entity: str  # e.g. "bitcoin" or "AAPL"
    request_params: dict[str, Any]
    payload: Any  # the untouched API response body
    extracted_at: datetime

    def to_json(self) -> str:
        # An "envelope" of metadata around the payload: later steps know where
        # and when the data came from without guessing from the filename.
        return json.dumps(
            {
                "source": self.source,
                "entity": self.entity,
                "extracted_at": self.extracted_at.isoformat(),
                "request_params": self.request_params,
                "payload": self.payload,
            }
        )


def landing_path(root: Path, record: RawRecord) -> Path:
    ts = record.extracted_at.astimezone(UTC)
    return (
        root
        / record.source
        / record.entity
        / f"dt={ts:%Y-%m-%d}"
        / f"{ts:%H%M%S}.json"
    )


def write_raw(root: Path, record: RawRecord) -> Path:
    path = landing_path(root, record)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file then rename: rename is atomic, so a crash mid-write
    # never leaves a half-written file that the loader would choke on.
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(record.to_json())
    tmp.replace(path)
    return path
