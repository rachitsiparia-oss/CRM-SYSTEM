"""Per-metric calculator functions, grouped by reporting domain. Each
function takes `(session, window)` and returns a single aggregate value —
plain, hand-written SQLAlchemy against the real domain tables, never a
client-composed query. `app.analytics_core.registry.METRICS` maps a metric
code to exactly one of these callables.
"""
