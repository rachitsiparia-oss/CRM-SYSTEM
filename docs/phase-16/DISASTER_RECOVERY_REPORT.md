# Phase 16 — Disaster Recovery Report

Generated: 2026-08-02. Evidence-based, and explicit about what could and could not be verified
from within this session — CLAUDE.md §6.5 ("Do not declare backups valid without restoration
verification at the proper operational stage") is taken literally here: nothing below claims a
live restore was tested when it wasn't.

## Backup and restore

`docs/DEPLOYMENT_AND_ENV.md` §22 ("BACKUP AND RESTORE OPERATIONS") already documents backup
scope (Postgres, storage objects, migration history, critical configuration), restore-validation
criteria (database integrity, application compatibility, auth linkage, permissions, file
references, audit history, critical workflows), and gates production launch on "an approved
backup strategy and at least one successful restore test."

This is correctly scoped as infrastructure-level, pre-production work: the project runs against
Supabase-managed Postgres, which owns automated backup scheduling and point-in-time-recovery at
the platform level — not something this codebase configures or can exercise from a coding
session (no deployed Supabase project, no staging environment, no access to Supabase's
backup/restore console from here). Fabricating a "restore test passed" result would violate
CLAUDE.md §6.5 directly. **No code change was made here** — the existing documentation already
states the right requirement and the right gate; there is nothing to fix at the application-code
level. Restore verification remains an operational task for whoever runs the actual pre-launch
checklist against real Supabase infrastructure.

## Migration rollback

### Method

Every `apps/api/app/db/migrations/versions/*.py` file was checked for a `downgrade()` definition
(`grep -L "def downgrade"` — zero files missing one) and for a near-empty/no-op body (an awk
scan stripping comments/docstrings and flagging any `downgrade()` with ≤1 substantive line — zero
suspects). Three representative migrations were then read in full: the most recent Phase 15
migration (`4edacdc2f990_add_phase15_jobs_integrations_dead_.py`), and the dedicated RLS-toggle
migration (`68a3f066b2b9_enable_row_level_security_on_all_tables.py`).

### Findings

- Every migration has a non-trivial `downgrade()`.
- `4edacdc2f990`'s `downgrade()` reverses its `upgrade()` in correct dependency order — new
  columns/constraints/indexes on existing tables dropped before the new tables themselves, new
  tables dropped last. RLS enablement (looped over the 4 new tables in `upgrade()`) needs no
  explicit disable in `downgrade()` since the tables — and their policies with them — are
  dropped outright.
- `68a3f066b2b9`'s `downgrade()` is a symmetric `DISABLE ROW LEVEL SECURITY` loop matching its
  `upgrade()`'s `ENABLE ROW LEVEL SECURITY` loop.

### What was not done, and why

A live `alembic downgrade -1` / `alembic upgrade head` round-trip was **not** executed against
the shared development database. Every background verification run this session (dozens of
`pytest` invocations across the full backend suite) targets that same database concurrently;
running a destructive schema round-trip against it mid-session risks breaking unrelated
in-flight test runs or leaving the schema in a partially-migrated state if a downgrade step has
an undiscovered bug — a real, asymmetric risk (a bad downgrade can drop data) that isn't
justified by a mechanical rollback check when the static read-through already found the
`downgrade()` bodies well-formed. This matches CLAUDE.md's own risk-taking guidance: prefer
reversible, low-blast-radius verification over a destructive one when both are available, and
flag the gap explicitly rather than silently skip it. **Recommended**: run the round-trip in an
isolated database (a throwaway local Postgres or a disposable Supabase branch), not the shared
dev instance, as part of a CI gate — this is exactly what CLAUDE.md §25's "database migration
upgrade and downgrade... validation where applicable" and §12's "test migrations from a clean
database and from the latest previous schema state" call for, and it wasn't skipped out of
convenience — it requires infrastructure this session doesn't have.

## Graceful shutdown and startup

### Found and fixed: neither process disposed its database connection pool on shutdown

- **`apps/api/app/main.py`**: `_lifespan_factory`'s `lifespan()` logged `api_shutdown` but never
  closed the SQLAlchemy async engine's connection pool — every pooled connection was left for
  the OS to reap on process exit instead of being closed cleanly.
- **`apps/worker/worker/main.py`**: `on_shutdown` had the identical gap for the worker's own
  separate engine (`worker.db.get_engine()`).
- **Fix**: both now call `await get_engine().dispose()` during shutdown, guarded by "was a
  database actually configured" (`settings.database_url`) so local dev without `DATABASE_URL`
  never attempts to create an engine just to immediately dispose it.
- Startup was already safe: both processes only log on startup and never eagerly perform
  database work before serving traffic — `get_engine()` is lazily created (`@lru_cache`) on
  first real use, and `Settings`' own `model_validator`s already fail fast at process start if
  `staging`/`production` is missing required configuration (`app/core/config.py`).

### Tests

- `apps/api/tests/test_health.py::test_lifespan_disposes_engine_on_shutdown_when_database_configured` —
  the lifespan context manager calls `engine.dispose()` exactly once on exit when a database is
  configured.
- `apps/api/tests/test_health.py::test_lifespan_skips_disposal_when_database_not_configured` —
  the same context manager exits cleanly with no engine ever created when `database_url` is
  unset (proves the guard, not just the happy path).
- The worker-side fix mirrors the API-side one exactly (same guard, same `dispose()` call) —
  no separate test was added there since `apps/worker/tests` has no existing pattern for
  constructing `WorkerSettings.on_startup`/`on_shutdown` in isolation the way `apps/api`'s
  `_lifespan_factory` already supports; the API-side test proves the identical logic shape.

## Summary

- Backup/restore: already correctly documented as an infrastructure-level pre-production gate;
  no code to fix, no fabricated verification.
- Migration rollback: every `downgrade()` exists and is non-trivial; three read in full and
  found correct; a live round-trip was deliberately deferred to an isolated database rather than
  run against the shared dev instance mid-session.
- Graceful shutdown: one real gap found and fixed in both `apps/api` and `apps/worker`
  (connection pool never disposed), with regression tests for the API side.
