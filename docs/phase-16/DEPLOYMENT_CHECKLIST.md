# Phase 16 — Deployment Checklist

Generated: 2026-08-06. This is the one Phase 16 §P deliverable with no existing home in
`docs/phase-16/` — every other named deliverable (Security Audit Report, Performance Report,
Accessibility Report, etc.) already exists as its own file; see the index at the bottom of this
document for where each one lives, including where several were deliberately consolidated rather
than duplicated.

This checklist is a **pre-production gate**, not a claim that production deployment happened.
Nothing in this repository has been deployed to Railway, Vercel, or a production Supabase
project. Every item below is either (a) already true today, verified by this session or an
earlier phase and cited accordingly, or (b) an infrastructure-level action that requires real
deployed infrastructure this sandboxed development session does not have — those are marked
**not executable from here** rather than silently checked off.

## How to use this checklist

Work top to bottom before the first production deploy. Items marked "verified" are safe to trust
as-is (re-verify only if the cited code path changes). Items marked "not executable from here"
are the actual remaining work for whoever runs the real launch — do not mark Phase 16 or any
later phase "complete" by assuming these passed.

## 1. Security

| Item | Status | Evidence |
|---|---|---|
| Security response headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) | Verified | `app/core/security_headers.py`, tested in `test_health.py` |
| HSTS sent only in staging/production | Verified | same file; `test_health.py` asserts absence outside staging/production |
| Interactive API docs disabled outside local/test | Verified | `app/main.py::create_app()` |
| Webhook inbound/status endpoints reject unregistered providers (no silent fail-open to the mock adapter) | Verified | `app/communications/providers.py::get_registered_provider`, `test_communications_webhooks.py` |
| Webhook idempotency via unique `(provider, provider_event_id)` | Verified | `app/communications/webhooks.py` |
| Progressive rate-limit backoff on repeated violations | Verified | `app/core/rate_limit.py`, `test_rate_limit.py` |
| Account auto-lock after 10 permission denials in 5 minutes | Verified | `app/permissions/dependencies.py::require_permission`, `test_permission_lockout.py` |
| File upload MIME/extension/signature triple-check + EXIF stripping | Verified | `app/storage/validation.py`, `app/knowledge/attachments.py`, `test_file_upload_validation.py` |
| Malware-scan hook wired on every upload path that exists today (honest `"skipped"` status, no fabricated `"clean"`) | Verified | `app/storage/scanning.py`, `test_attachment_scanning.py` |
| Secret/token/password redaction in structured logs | Verified | `app/core/logging.py::_redact_sensitive_fields`, `test_logging_redaction.py` |
| Sensitive HR document access is audited | Verified | `app/staff_operations/router.py`, `test_staff_document_access_audit.py` |
| SQL injection / SSRF / command injection / stored-XSS review | Verified, no gaps found | `docs/phase-16/SECURITY_AUDIT_REPORT.md` §8 |
| AI prompt-injection, oversized-prompt, and AI-specific rate-limit hardening | Verified | `app/controlled_ai/grounding.py`, `test_controlled_ai.py`, `test_phase14_api.py` |
| Authorization coverage across every registered endpoint | Verified — 565 endpoints scanned, 0 confirmed gaps | `docs/phase-16/AUTHORIZATION_COVERAGE_REPORT.md` |
| Production secrets never committed, `.env.example` has placeholders only | Verified | repo `.env.example`, `git status` shows no `.env` tracked |
| Real WhatsApp/email/SMS/AI provider credentials configured | **Not executable from here** | no credentials exist yet; every channel runs on `internal_mock` / mock AI provider by design (`docs/TOOLS.md` §10) |
| MFA enforced for owner/high-privilege accounts | **Not executable from here** | requires a live Supabase Auth project with MFA enrollment; app-side enforcement point is `app/auth/dependencies.py`, unchanged this phase |

## 2. Database and migrations

| Item | Status | Evidence |
|---|---|---|
| Every migration has a non-trivial, dependency-ordered `downgrade()` | Verified (static read-through, 3 migrations read in full) | `docs/phase-16/DISASTER_RECOVERY_REPORT.md` |
| Composite indexes exist for every checked high-traffic filter/sort combination (orders, customers, reservations, staff_users) | Verified | `docs/phase-16/PERFORMANCE_REPORT.md` §Index review |
| N+1 query in `inventory/balances.py::rebuild_balances` | Fixed and verified | `docs/phase-16/PERFORMANCE_REPORT.md` §N+1 review, `test_inventory_ledger.py` |
| Live `alembic downgrade -1` / `upgrade head` round-trip against an isolated database | **Not executable from here** | deliberately not run against the shared dev database mid-session (asymmetric risk — see `DISASTER_RECOVERY_REPORT.md`); run this in CI or a disposable Supabase branch before production |
| Backup scheduling and point-in-time recovery configured | **Not executable from here** | owned by Supabase-managed Postgres at the platform level once a real project exists; documented gate in `docs/DEPLOYMENT_AND_ENV.md` §22 |
| At least one successful restore test performed | **Not executable from here** | same reason; do not deploy to production without this |

## 3. Worker and background jobs

| Item | Status | Evidence |
|---|---|---|
| Cron-overlap safety across worker replicas (Postgres advisory locks) | Verified | `apps/worker/tests/test_scheduling.py` |
| Exponential backoff + jitter retry classification | Verified | `app/jobs/classify.py` |
| Job timeout classified as retryable | Fixed and tested this phase | `test_jobs_runner.py::test_run_job_timeout_is_classified_retryable` |
| Dead-letter lifecycle (create/list/investigate/replay/ignore) | Verified, pre-existing | `app/dead_letter/service.py` |
| Graceful connection-pool disposal on shutdown (`apps/api` and `apps/worker`) | Fixed and tested this phase | `app/main.py`, `worker/main.py`, `test_health.py::test_lifespan_disposes_engine_on_shutdown_when_database_configured` |

## 4. Caching and performance

| Item | Status | Evidence |
|---|---|---|
| Cache hit/miss Prometheus observability | Verified, pre-existing | `app/cache/service.py` |
| `permissions` and `settings` cache families wired to real data | Verified | `app/permissions/service.py`, `app/feature_flags/service.py` |
| `analytics`/`dashboard`/`reports`/`customer_summary` cache families | Reserved, not wired — deliberate follow-up, not a gap | `docs/phase-16/PERFORMANCE_REPORT.md` §Cache coverage |
| Slow-query and slow-request structured warning logs | Added this phase | `app/core/slow_query.py`, `app/core/metrics_middleware.py`, `test_slow_query.py` |
| k6 load test script against real endpoints with real p95/p99 numbers | **Not executable from here** — script delivered, no server running in this sandbox | `docs/phase-16/LOAD_TEST_REPORT.md`, `tests/load/api_smoke.js` |
| Conversation-timeline endpoint pagination for very long message histories | Reviewed, scoped as follow-up, not fixed this phase | `docs/phase-16/FRONTEND_PERFORMANCE_REPORT.md` |

## 5. Frontend

| Item | Status | Evidence |
|---|---|---|
| Chart components code-split (ECharts no longer in initial route bundle) | Fixed and verified this phase | `apps/dashboard/src/components/charts/*-impl.tsx`, `next build` succeeded |
| No raw `<img>` tags; `next/image` used everywhere | Verified | `docs/phase-16/FRONTEND_PERFORMANCE_REPORT.md` |
| `prefers-reduced-motion` support | Fixed this phase | `apps/dashboard/src/app/globals.css` |
| Icon-only buttons carry `aria-label` | Fixed 2 gaps this phase, 12/14 files already correct | `docs/phase-16/ACCESSIBILITY_REPORT.md` |
| Keyboard nav, focus trapping, color contrast | Verified — inherited from Radix/shadcn foundation (Phase 4) | `docs/phase-16/ACCESSIBILITY_REPORT.md` |

## 6. Observability

| Item | Status | Evidence |
|---|---|---|
| Structured logs with correlation IDs | Verified, pre-existing (Phase 15) | `app/core/logging.py` |
| Prometheus metrics: request latency, job duration, queue depth, dead-letter count, cache hit/miss | Verified, pre-existing (Phase 15) | `app/core/metrics.py` |
| Slow query / slow request warnings | Added this phase | see §4 above |
| Sentry error reporting with sensitive-data scrubbing configured against a real DSN | **Not executable from here** | requires a real Sentry project; app-side hook point is `docs/DEPLOYMENT_AND_ENV.md` §15, unchanged this phase |

## 7. Verification gate (CLAUDE.md §25 / Phase 16 §O)

All executable in this environment; results recorded in full in
[`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md):

- `apps/api`: `ruff format --check`, `ruff check`, `mypy --strict` — all clean. Full `pytest` —
  1040 passed (5 initially-flaky tests, unrelated to this session's changes, isolated and
  confirmed passing on re-run — see that report for the full explanation).
- `apps/worker`: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` — all clean, 3
  passed.
- `apps/dashboard`: `eslint` (0 errors, 14 pre-existing unrelated warnings), `tsc --noEmit`
  (clean), `vitest` (122 passed), `next build` (succeeded), `playwright test` (110 passed).

## Deliverable index (Phase 16 §P)

Per this phase's own instructions, the following named deliverables were requested. Several are
intentionally consolidated into one file rather than duplicated across multiple documents — noted
explicitly below rather than silently reorganized:

| Requested deliverable | Where it lives |
|---|---|
| Security Audit Report | [`SECURITY_AUDIT_REPORT.md`](SECURITY_AUDIT_REPORT.md) |
| AI Safety Report | Folded into `SECURITY_AUDIT_REPORT.md` §9 (prompt-injection/AI hardening) — AI safety findings are security findings; kept together rather than duplicated |
| Performance Report | [`PERFORMANCE_REPORT.md`](PERFORMANCE_REPORT.md) |
| Database Optimization Report | Folded into `PERFORMANCE_REPORT.md` §Index review / §N+1 review — the database-optimization findings are a subsection of the same performance pass, not a separate investigation |
| Worker Benchmark Report | Folded into `PERFORMANCE_REPORT.md` §Worker concurrency review — no live worker load benchmark was run (no deployed worker instance); the concurrency/retry/dead-letter design review is what exists |
| Cache Report | Folded into `PERFORMANCE_REPORT.md` §Cache coverage — coverage and observability findings for the one cache layer in the codebase |
| Accessibility Report | [`ACCESSIBILITY_REPORT.md`](ACCESSIBILITY_REPORT.md) |
| Deployment Checklist | This document |
| Disaster Recovery Checklist | [`DISASTER_RECOVERY_REPORT.md`](DISASTER_RECOVERY_REPORT.md) |
| API Benchmark Report | [`LOAD_TEST_REPORT.md`](LOAD_TEST_REPORT.md) — script delivered, no numbers fabricated; the closest thing to a benchmark until k6 runs against a live server |
| (supporting) Authorization coverage | [`AUTHORIZATION_COVERAGE_REPORT.md`](AUTHORIZATION_COVERAGE_REPORT.md) |
| (supporting) Frontend performance | [`FRONTEND_PERFORMANCE_REPORT.md`](FRONTEND_PERFORMANCE_REPORT.md) |
| (supporting) Full verification results | [`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md) |

**Why consolidated rather than split**: Database Optimization, Worker Benchmark, and Cache
Report all came out of the same single review pass (`docs/phase-16/PERFORMANCE_REPORT.md`'s
"Method" sections describe reading the same set of files once, not three separate
investigations), and none produced enough independent, non-overlapping content to justify a
separate document — splitting them would mean either duplicating the shared context or shipping
three near-empty files that each cross-reference the other two. Consolidation keeps one
authoritative performance narrative instead of fragmenting it. If a future phase performs a real,
independently-scoped worker load benchmark (e.g. against a live Railway deployment) or a deep
database-specific tuning pass, that is exactly the point to split it into its own file — this
decision is not permanent, just not yet warranted.
