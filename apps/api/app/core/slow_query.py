"""Slow-query logging — CLAUDE.md section 19 ("slow endpoints must be
observable", "expensive endpoints must be measured"). A structured warning
log per query over threshold, not a new metrics backend or query-plan
collector: `app.core.metrics`'s own docstring already establishes this
project's narrow instrumentation scope (Prometheus counters/gauges/
histograms only, no dashboard deployment), and a slow-query log line is the
equivalent minimal addition for the database side.

Timing is stashed on the SQLAlchemy `ExecutionContext` (`context._query_start`),
not a module-level variable — concurrent async connections interleave
`before_cursor_execute`/`after_cursor_execute` calls across different
statements, so a shared variable would attribute one query's duration to
another.
"""

import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_LOGGED_STATEMENT_CHARS = 500


def instrument_slow_queries(engine: Engine, *, threshold_ms: int) -> None:
    if threshold_ms <= 0:
        return
    threshold_seconds = threshold_ms / 1000

    @event.listens_for(engine, "before_cursor_execute")
    def _before(
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        del conn, cursor, statement, parameters, executemany
        context._query_start = time.monotonic()

    @event.listens_for(engine, "after_cursor_execute")
    def _after(
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        del conn, cursor, parameters, executemany
        start = getattr(context, "_query_start", None)
        if start is None:
            return
        duration = time.monotonic() - start
        if duration >= threshold_seconds:
            logger.warning(
                "slow_query",
                duration_ms=round(duration * 1000, 1),
                statement=statement[:_MAX_LOGGED_STATEMENT_CHARS],
            )
