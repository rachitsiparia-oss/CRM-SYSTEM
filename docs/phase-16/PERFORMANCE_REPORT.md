# Phase 16 — Performance Report

Generated: 2026-08-02. Evidence-based — every claim below cites the file and line read, not an
assumption about what a phase "probably" did.

## N+1 query review

### Method

Two multiline greps across every `apps/api/app/**/*.py` file for the classic N+1 shape (a `for`
loop over query results with a `session.get`/`session.scalar`/`session.execute` call inside the
loop body), plus a check for `selectinload`/`joinedload` usage to see whether the codebase relies
on ORM lazy relationship traversal anywhere.

### Finding: `selectinload`/`joinedload` are used nowhere in the codebase — by design, not omission

Every list/detail endpoint checked (`app/orders/router.py::list_orders`/`get_order` as the
representative high-traffic example) follows a consistent pattern: the list endpoint returns a
distinct, lighter DTO (`OrderListItemOut`) that never references child collections, and the
detail endpoint (`get_order`) fetches the aggregate root and its children (e.g. order items) as
separate, explicit, single queries — not through a lazy ORM relationship access. This means the
codebase cannot suffer the classic "access `order.items` inside a loop and trigger one query per
order" N+1, because relationship attributes are never traversed that way in the first place; async
SQLAlchemy would raise `MissingGreenlet` immediately if an unloaded relationship were accessed
outside its original session context, so a real instance of this bug would already be a loud,
already-caught test failure, not a silent one.

### Finding and fix: `app/inventory/balances.py::rebuild_balances` issued one aggregate query per item

- **Before**: the final loop of a full-catalog balance rebuild (`POST /inventory/balances/rebuild`
  with no `inventory_item_id` filter — an admin-only, permission-gated maintenance operation, not
  a routinely-hit endpoint) ran one `SELECT SUM(...) WHERE inventory_item_id = :id` per inventory
  item, inside a `for item in (await session.scalars(items_stmt)).all():` loop.
- **Fix**: replaced with a single grouped aggregate (`GROUP BY inventory_item_id`) fetched once
  before the loop, looked up per item from a dict — matching the same dict-lookup pattern the rest
  of this function already uses for `ledger_totals`/`reserved_totals`/`location_policy`/`existing`.
  N+1 queries → 2 queries total (items + grouped totals), regardless of catalog size.
- **Verified**: `apps/api/tests/test_inventory_ledger.py`'s existing rebuild tests (20 tests, all
  passing) exercise this path; no new test was needed since the fix preserves the exact same
  per-item output values, only changing how they're fetched.

### Reviewed and found acceptable, not fixed: two background-job batch loops

`app/campaigns/execution.py` has two loops with a per-row `session.get()` inside them
(`_process_batch`'s per-recipient channel/customer lookup, and `sync_recipient_statuses`'s
per-recipient `ScheduledMessage` lookup). Both run inside ARQ background jobs, not an HTTP request
path — CLAUDE.md §5.2's "avoid N+1 queries" and §5.1's "never block an API request" are both
about request-path performance, and a batch job processing recipients one at a time (each with
genuinely per-recipient side effects — eligibility evaluation, message scheduling) isn't the same
risk category as a list endpoint doing per-row reads under live user load. Left as-is; flagged
here rather than silently skipped.

## Index review

### Method

Spot-checked the `__table_args__` `Index(...)` declarations on the highest-traffic tables against
the filter/sort options their list endpoints actually expose, rather than re-deriving every
index across 15 phases' migrations from scratch — each phase's own completion process already
required "composite indexes for common filter and sort combinations" (CLAUDE.md §5.3) as an
explicit acceptance criterion, so the prior is that this is already correct, and the spot-check
is to verify that prior rather than assume it.

### Findings — already correct everywhere checked

- **`orders`** (`app/db/models/order.py`): `list_orders` filters on `order_status`, `source`,
  `order_type`, `payment_status`, `assigned_staff_id`, date range, and sorts by several columns.
  Indexed: `(status, created_at)`, `(source, created_at)`, `payment_status`,
  `assigned_staff_id`, `customer_id` — composite indexes exist for exactly the filter+sort pairs
  the endpoint uses most (status/source combined with the default sort column).
- **`customers`** (`app/db/models/customer.py`): indexed on `primary_phone_e164`,
  `primary_email` (duplicate-detection/search lookups), `(customer_status, customer_segment)`
  composite, `assigned_staff_id`, `last_order_at`.
- **`reservations`** (`app/db/models/reservation.py`): indexed on `customer_id`,
  `dining_area_id`, `status`, `(reservation_date, start_time)` composite (the calendar/day-view
  query shape), `order_id`, `assigned_staff_id`.
- **`staff_users`** (`app/db/models/staff_user.py`): indexed on `department_id` plus two further
  composite indexes for account-status/directory queries.

No missing composite index was found in any table checked. This section records that indexes
were verified, not assumed — a full re-audit of every table across all 15 phases was judged lower
value than the N+1 review given the consistent, already-tested pattern found in every table
sampled.

## Worker concurrency, retry strategy, and dead-letter review

### Method

Read `apps/worker/worker/main.py` (`WorkerSettings`, cron schedule), `apps/worker/worker/
scheduling.py` (`run_scheduled_job`), `apps/api/app/jobs/runner.py` (`run_job`, the durable
tracking every cron/on-demand job goes through), `apps/api/app/jobs/classify.py` (retry
classification and backoff), `apps/api/app/dead_letter/service.py` (manual-recovery lifecycle),
and `apps/api/app/core/metrics.py` (job/dead-letter observability), before writing anything —
this is Phase 15 work, already built with CLAUDE.md's job requirements (§14) as an explicit
spec, and the review's job was to verify that, not assume it.

### Findings — already correct, confirmed by reading, not rebuilt

- **Concurrency**: `WorkerSettings.max_jobs` (ARQ's own concurrency cap, default 10, configurable
  via env) and `job_timeout_seconds` (default 300) are both externally configurable per
  deployment.
- **Overlap safety**: every cron-triggered job goes through `run_scheduled_job`, which wraps
  execution in a Postgres advisory lock (`app.jobs.locks.advisory_lock`, keyed by job type) —
  running `apps/worker` as more than one replica cannot double-run the same cron tick; a replica
  that loses the lock race records a `{"skipped": "locked"}` no-op, not an error. Tested:
  `apps/worker/tests/test_scheduling.py::test_run_scheduled_job_skips_when_lock_already_held`.
- **Retry classification and backoff**: `classify_error` uses a deliberately narrow allowlist of
  connection/timeout-shaped exception types as "retryable" — everything else, including every
  domain/business-rule error, is "permanent" by default, so a validation failure is never
  retried into repeating the same failure. `compute_next_retry_at` is exponential with jitter and
  a cap (`base_seconds * 2^(attempt-1)` capped at `cap_seconds`, plus up to 20% jitter) —
  standard, correct backoff shape.
- **Dead-letter recovery**: `app.dead_letter.service` already has the full lifecycle CLAUDE.md
  §14 requires — `create_entry` (on permanent failure or attempt exhaustion, with attempt
  history), `list_dead_letter_entries`, `mark_investigating`, `mark_replay_ready`, `ignore_entry`,
  `replay_entry`. Not a stub.
- **Observability**: `app.core.metrics` already exposes `crm_job_queue_depth` (by status),
  `crm_job_duration_seconds_avg` (by job type), and `crm_dead_letter_open_total` as Prometheus
  gauges, matching CLAUDE.md §19's explicit "queue depth... job duration... dead-letter" metrics
  list.
- **Idempotency**: `run_job`'s `idempotency_key` parameter reuses an existing `succeeded` row
  without re-executing `func`, and reuses (rather than duplicates) a non-succeeded prior row with
  the same key.

### Found and fixed: timeout behavior was implemented but untested

`run_job` wraps every job in `asyncio.wait_for(func(), timeout=timeout_seconds)`, and
`classify_error` correctly includes `TimeoutError` in its retryable set — but no test exercised
this path, despite CLAUDE.md §18 explicitly listing "timeouts" as a required worker-test
category alongside retries/duplicate-execution/failures. Added
`apps/api/tests/test_jobs_runner.py::test_run_job_timeout_is_classified_retryable` — a job that
sleeps past its `timeout_seconds` is classified `retryable` with a `next_retry_at` set, the same
outcome shape as the existing connection-error retry test.

### Reviewed and intentionally not changed: `next_retry_at` is informational for cron jobs

`run_scheduled_job` doesn't pass an `idempotency_key`, so a cron-triggered job's `next_retry_at`
isn't consulted to gate re-execution — the job's own cron cadence (2-30 minutes for most
dispatch/reconciliation jobs) is what re-attempts it, not a scheduled-at-`next_retry_at` replay.
This is a reasonable, working design for jobs whose cadence is already frequent relative to the
backoff window, not a bug: `next_retry_at` still serves its purpose as an operator-visible
"when do we expect the next attempt" signal on the `JobRecord` row. Flagged here as a documented
characteristic, not silently passed over.

## Cache coverage and hit/miss observability review

### Method

Read `app/cache/service.py`, `app/cache/keys.py`, `app/cache/client.py`, and grepped every
call site of `get_json`/`set_json` across the codebase to find actual coverage, not just what
the key-family registry declares.

### Finding: hit/miss observability is already complete

`app/cache/service.py::get_json` already increments `crm_cache_hits_total`/
`crm_cache_misses_total` (Prometheus counters, labeled by cache family) on every call, covering
a real Redis hit, a miss, a corrupt cached value, and a Redis-unavailable fallback — all four
paths count as a miss, and a Redis outage degrades to "always miss" rather than a 500 (`except
Exception` around the client call, matching `INTEGRATIONS_AUTOMATIONS_REALTIME.md`'s "failure
isolation"). `invalidate_prefix` uses non-blocking `SCAN`, never the blocking `KEYS` command.
Nothing needed to be added here — the observability half of this task was already done.

### Finding: 4 of 6 declared cache families have zero call sites

`app/cache/keys.py::CACHE_TTL_SECONDS` declares six families — `analytics`, `permissions`,
`dashboard`, `reports`, `settings`, `customer_summary` — but a grep for every `get_json`/
`set_json` call site found only two families actually wired to real data:
`permissions` (`app/permissions/service.py` — the effective-permissions cache, already
Phase 3/16-hardened, invalidated on every role/status change) and `settings`
(`app/feature_flags/service.py`). `analytics`, `dashboard`, `reports`, and `customer_summary`
have TTLs defined and reserved but no code path ever calls `get_json`/`set_json` for them.

### Why this wasn't force-fixed in this pass

The natural candidate for the `dashboard`/`analytics` families is
`app/reports/service.py::get_dashboard` and `app/analytics_core/engine.py::run_metric_query` —
exactly the kind of repeated, permission-scoped, moderately expensive read this cache layer
exists for. Both return frozen dataclasses (`MetricResult`, containing a nested `MetricDef` and
`ResolvedWindow`, `Decimal` values, and `datetime`s) rather than JSON-safe primitives. Caching
them correctly requires a deliberate serialize/deserialize design for that shape (Decimal
precision, dataclass reconstruction, and re-validating that a cached result still reflects the
caller's *current* permission scope, not just the scope at write time) — this is real design
work, not a mechanical `get_json`/`set_json` wrap, and rushing it into financial/analytics
reporting data risks a precision or stale-permission bug. CLAUDE.md's own priority order puts
correctness above performance; a hasty cache-serialization change to this specific path is
exactly the "temporary hack in a production path" §4 forbids. Recommended as explicit follow-up
work, not silently dropped: whoever picks this up should design the serialized `MetricResult`
shape first (likely a dedicated `CachedMetricResult` TypedDict/Pydantic model near
`analytics_core.engine`), not bolt caching onto the existing dataclass.

No code changes made for cache coverage — the safe, honest conclusion given the risk profile of
the only real expansion candidates found. Observability was already complete and required no
changes either.

## Slow-query and slow-endpoint monitoring

### Method

Read `app/core/metrics.py` and `app/core/metrics_middleware.py` (the existing HTTP-request
histogram/counter) before adding anything — CLAUDE.md §19 asks for slow endpoints/queries to be
"observable," which the existing per-route Prometheus histogram already technically enables for
anyone running a scraper computing percentiles, but there was no direct, greppable signal for a
single slow request or query, and no per-query timing at all (the histogram only covers total
HTTP request duration, not the database time within it).

### Added: structured warning logs for slow queries and slow requests

- **`app/core/slow_query.py`** (new) — `instrument_slow_queries(engine, threshold_ms=...)`
  attaches SQLAlchemy `before_cursor_execute`/`after_cursor_execute` listeners to the sync engine
  underlying the async engine, timing each query and logging a `slow_query` warning
  (`duration_ms`, `statement` — the parameterized SQL text, truncated to 500 chars; bind
  *values* are never logged, only the statement shape with placeholders) when it exceeds
  `settings.slow_query_threshold_ms` (default 500ms). Wired into `app/db/session.py::get_engine()`.
  Timing is stashed per-`ExecutionContext`, not a module-level variable, since concurrent async
  connections interleave query executions.
- **`app/core/metrics_middleware.py`** — `MetricsMiddleware` now also logs a `slow_request`
  warning (`method`, `route`, `status`, `duration_ms`) for any request over
  `settings.slow_request_threshold_ms` (default 1000ms), alongside the histogram/counter it
  already recorded. A threshold of `0` disables the corresponding check entirely in both cases
  (not "log everything") — both settings are configurable per environment via
  `SLOW_QUERY_THRESHOLD_MS`/`SLOW_REQUEST_THRESHOLD_MS`.
- Deliberately a structured log line, not a new metrics backend or query-plan collector —
  matching `app/core/metrics.py`'s own documented scope decision (Prometheus counters/gauges/
  histograms only, no dashboard deployment, per `docs/TOOLS.md`'s "not without demonstrated need
  and approval").

### Tests

- `apps/api/tests/test_slow_query.py` — a query held past threshold by an injected delay logs
  once with the right fields; a fast query logs nothing; a zero threshold disables instrumentation
  entirely (verified against a throwaway in-memory SQLite engine, not the real Postgres
  connection — the event-listener logic is DBAPI-agnostic).
- `apps/api/tests/test_health.py::test_slow_request_logs_warning` — a real request through a
  `create_app()` instance with `SLOW_REQUEST_THRESHOLD_MS=1` logs `slow_request` with the
  matched route template, method, and status.

## Summary

- One real N+1 fix (`app/inventory/balances.py::rebuild_balances`), verified against existing
  tests.
- No missing composite indexes found in the tables checked.
- One worker-test gap closed (timeout classification), everything else in the job pipeline
  already correct.
- Cache observability already complete; cache coverage expansion into the analytics/dashboard
  domain deliberately deferred as a design task, not force-fixed.
