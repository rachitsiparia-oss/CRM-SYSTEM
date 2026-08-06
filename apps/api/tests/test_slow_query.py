import time
from typing import Any

import pytest
from app.core.slow_query import instrument_slow_queries
from sqlalchemy import create_engine, event, text


class _RecordingLogger:
    """Stands in for `app.core.slow_query.logger` — the module-level
    structlog logger is a singleton object, and replacing the whole
    reference (rather than patching a `.warning` attribute onto it) avoids
    depending on how structlog's bound-logger class resolves method
    lookups internally."""

    def __init__(self, sink: list[dict[str, object]]) -> None:
        self._sink = sink

    def warning(self, event: str, **kwargs: object) -> None:
        self._sink.append({"event": event, **kwargs})


def test_slow_query_logs_warning_over_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[dict[str, object]] = []
    monkeypatch.setattr("app.core.slow_query.logger", _RecordingLogger(warnings))

    engine = create_engine("sqlite://")
    instrument_slow_queries(engine, threshold_ms=1)

    # Artificially slow the query so it reliably exceeds the 1ms threshold
    # without depending on real query latency.
    @event.listens_for(engine, "before_cursor_execute")
    def _delay(*args: Any) -> None:
        del args
        time.sleep(0.01)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    assert len(warnings) == 1
    assert warnings[0]["event"] == "slow_query"
    assert warnings[0]["statement"] == "SELECT 1"
    assert isinstance(warnings[0]["duration_ms"], float)
    assert warnings[0]["duration_ms"] >= 10


def test_fast_query_does_not_log(monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[dict[str, object]] = []
    monkeypatch.setattr("app.core.slow_query.logger", _RecordingLogger(warnings))

    engine = create_engine("sqlite://")
    instrument_slow_queries(engine, threshold_ms=60_000)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    assert warnings == []


def test_zero_threshold_disables_instrumentation(monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[dict[str, object]] = []
    monkeypatch.setattr("app.core.slow_query.logger", _RecordingLogger(warnings))

    engine = create_engine("sqlite://")
    instrument_slow_queries(engine, threshold_ms=0)

    @event.listens_for(engine, "before_cursor_execute")
    def _delay(*args: Any) -> None:
        del args
        time.sleep(0.01)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # A zero/negative threshold is a no-op (instrumentation never attached),
    # not "log everything."
    assert warnings == []
