import json
from datetime import UTC, datetime

from market_pipeline.landing import RawRecord, landing_path, write_raw


def _record() -> RawRecord:
    return RawRecord(
        source="coingecko",
        entity="bitcoin",
        request_params={"days": 1},
        payload={"prices": [[1, 2.0]]},
        extracted_at=datetime(2026, 9, 28, 14, 5, 9, tzinfo=UTC),
    )


def test_landing_path_is_partitioned_by_date(tmp_path):
    path = landing_path(tmp_path, _record())
    assert path == tmp_path / "coingecko" / "bitcoin" / "dt=2026-09-28" / "140509.json"


def test_write_raw_stores_envelope_and_leaves_no_temp_file(tmp_path):
    path = write_raw(tmp_path, _record())

    saved = json.loads(path.read_text())
    assert saved["source"] == "coingecko"
    assert saved["extracted_at"] == "2026-09-28T14:05:09+00:00"
    assert saved["payload"] == {"prices": [[1, 2.0]]}
    assert not list(tmp_path.rglob("*.tmp"))
