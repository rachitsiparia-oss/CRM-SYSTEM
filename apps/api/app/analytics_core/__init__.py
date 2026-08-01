"""Deterministic analytics core — GROWTH_AND_INTELLIGENCE.md section 13.4:
"metric definitions must not live only in frontend code." This package is
the single source of truth for what a metric means and how it is computed;
`app.reports`, `app.anomalies`, `app.forecasts`, and `app.controlled_ai`
all read metrics through `app.analytics_core.engine.run_metric_query`
rather than querying domain tables directly, so every consumer sees the
same numbers computed the same way.

Deliberately NOT a generic query engine over arbitrary tables/columns
(GROWTH_AND_INTELLIGENCE.md section 13.1: "must not become an unrestricted
query engine over raw production tables"). Each metric has one hand-written,
reviewed SQLAlchemy calculator function; clients only ever supply a
`metric_code` (validated against `METRICS`) plus a bounded time window —
never raw SQL, table names, or column names.
"""
