from contextlib import nullcontext

from market_pipeline import pipeline
from market_pipeline.extract import ExtractSummary
from market_pipeline.load import LoadSummary


def test_load_still_runs_when_extract_partly_fails(monkeypatch):
    calls = []
    failed_extract = ExtractSummary(failed={"alpha_vantage:AAPL": "rate limited"})

    monkeypatch.setattr(pipeline, "run_extract", lambda settings: failed_extract)
    monkeypatch.setattr(pipeline.db, "connect", lambda dsn: nullcontext("conn"))
    monkeypatch.setattr(
        pipeline, "run_load", lambda conn, root: calls.append("load") or LoadSummary()
    )

    ok = pipeline.run_pipeline()

    assert calls == ["load"]  # load ran despite the extract failure
    assert ok is False  # but the run as a whole is reported as failed
