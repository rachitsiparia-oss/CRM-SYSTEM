# Phase 17 — Deployment Report

Generated: 2026-08-07 (in progress — appended to as each task completes).

## Scope deviation from ROADMAP.md's original Phase 17 description (explicit user decision)

`ROADMAP.md`'s Phase 17 scope reads "Staging Deployment and Acceptance Testing," implying a
separate staging environment ahead of a later, separate Phase 18 production environment. Mid-phase,
inspection found that a Railway project (`CRM-SYSTEM`) already existed under the correct account
with one service already live in an environment literally named `production`, auto-deploying on
every push to `main`, and a Supabase project (`CRM-SYSTEM`) already serving as the shared
local/test database throughout Phases 1–16. The user was asked how to reconcile this with the
staging/production split the roadmap describes, and explicitly directed: treat this as one
production-track deployment inside the same existing Railway/Supabase/Vercel project set, and
deprioritize the formal Phase 18/19 staging→production promotion ceremony. This report documents
that decision plainly rather than silently reinterpreting the roadmap. What this does **not**
change: real, non-roadmap-labeling prerequisites for an actual production launch — a genuine
backup/restore rehearsal, final third-party provider credentials (WhatsApp/email/SMS/payment), and
an approved custom domain — remain unmet and are called out explicitly below, not silently skipped
just because the phase label changed.

## Infrastructure account corrections (before any provisioning)

Three of the four provider CLIs available in this session were initially authenticated to accounts
unrelated to this project (a personal/other-project Supabase and Railway account); each was caught
and corrected before any resource was created against the wrong account:

- **Supabase**: initial CLI session was on an unrelated personal org. Corrected; the real dedicated
  project is `CRM-SYSTEM` (ref `zxwqzqfabwbypnutyozm`, `ap-south-1`), already at migration head with
  canonical seed data (re-run confirmed idempotent).
- **Railway**: initial CLI session was on an unrelated account (`designerswebsite0@gmail.com`).
  Corrected; the real project is `CRM-SYSTEM` under `rachitsiparia-oss's Projects`, with one
  pre-existing service (`@rkpr/crm-backend`) already deployed and healthy.
- **Vercel**: the CLI session (`rachitsipariarx-6088`) does not have visibility into the actual
  dashboard deployment (`crm-system-dashboard`, live at
  `https://crm-system-dashboard-drab.vercel.app`), which is under a different Vercel login. This
  is unresolved as of this section being written — see the Vercel section below.

An earlier attempt to free a Supabase free-tier project slot by deleting an unrelated inactive
project (`Recovery-ai-receptionst`) was made and explicitly confirmed by the user before execution;
it turned out unnecessary once the correct account (with its own already-existing `CRM-SYSTEM`
project) was identified, but is recorded here for completeness since it was a real, irreversible
action taken mid-session.

## Redis/cache/queue hardening (prerequisite for sharing one Upstash instance across environments)

The existing Upstash Redis instance (already configured in `apps/api/.env` for local development)
is being reused for this deployment rather than provisioning a second one — consistent with the
single-project-reuse pattern above. Before pointing the deployment at it, two real gaps were found
and fixed, not just relabeled:

1. **Rate limiter had no Redis backing at all.** `app/core/rate_limit.py`'s own docstring already
   documented this as deferred to "the Phase 17 staging deployment" — an in-process limiter is only
   correct for a single API instance. Migrated to an atomic Redis Lua-script increment-and-check
   (`_LUA_SCRIPT`), preserving the Phase 16 progressive-backoff shape, with a safe fallback to the
   original in-process `RateLimiter` when Redis is unavailable. `check_rate_limit` is now `async`;
   its 4 call sites (`app/auth/dependencies.py`, `app/auth/router.py`, `app/controlled_ai/router.py`,
   `app/permissions/dependencies.py`) were updated to `await` it.
2. **Cache keys and the ARQ queue name were not environment-scoped.** `app/cache/keys.py::build_key`
   now includes `settings.environment` in every key; `apps/worker/worker/main.py`'s `WorkerSettings`
   now sets `queue_name = f"arq:queue:{settings.environment}"`. Without this, local development and
   this deployment sharing one physical Redis instance risked real collisions — a local dev worker
   consuming a deployed job, or vice versa — which DEPLOYMENT_AND_ENV.md section 27 explicitly
   prohibits ("no shared staging and production queue").

Verified: `apps/api/tests/test_rate_limit.py` (9 tests, including 4 new Redis-backed tests exercised
against the real Upstash instance, not mocked) and `apps/api/tests/test_cache_keys.py` (3 new unit
tests) all pass. `ruff format`/`ruff check`/`mypy --strict` clean on every changed file. Broader
regression coverage (`test_auth_api.py`, `test_permission_lockout.py`, `test_phase14_api.py` — all
call sites touched by the `await` migration): 36/36 passed. `apps/worker` test suite: 3/3 passed.
A full `apps/api` regression run was kicked off in the background; its result will be recorded here
once complete.

## Railway

### Existing state found

One service, `@rkpr/crm-backend`, already existed and was already live at
`https://rkprcrm-backend-production.up.railway.app`, connected via Railway's native GitHub
integration (auto-deploys on push to `main`), with `ENVIRONMENT=production`, `DATABASE_URL`,
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `AUTH_JWT_SIGNING_SECRET`, `REDIS_URL`,
`CORS_ALLOWED_ORIGINS`, and `DASHBOARD_BASE_URL` already correctly configured — this was not built
from scratch this session, only inspected and extended.

### Added: a second service for the ARQ worker

Created a new empty Railway service (`worker`), connected to the same GitHub repo/branch. Both
services necessarily read the same repo-root `railway.json`/`nixpacks.toml` — Railway's per-service
"Config-as-code path" override is a dashboard-only setting with no CLI or REST access surfaced in
this session (confirmed via `railway service --help`, `railway service source connect --help`; the
Railway JSON schema itself does support `build.nixpacksConfigPath` per config file, but nothing
exposes assigning a *different* config file per service without dashboard access), and Root
Directory cannot be scoped to `apps/worker` either without hiding the uv workspace root both
`apps/api` and `apps/worker` depend on (the same constraint already documented for the API service
in `DEPLOYMENT_AND_ENV.md` section 11.1).

**Fix**: `nixpacks.toml`'s build phase now runs `uv sync --all-packages` (installs both workspace
members). `railway.json`'s `deploy.startCommand` branches on Railway's own auto-injected
`$RAILWAY_SERVICE_NAME` environment variable — `"worker"` runs
`uv run --package rkpr-worker arq worker.main.WorkerSettings`; anything else (including the API's
actual name, `@rkpr/crm-backend`) falls through to the existing uvicorn command. Verified
`RAILWAY_SERVICE_NAME` is genuinely present and correctly valued via `railway variable list`
against the live API service before relying on it.

**Known, flagged cost of this approach**: `deploy.healthcheckPath` had to be removed from the
shared config entirely — the worker has no HTTP server to probe (by design; see
`docs/phase-16/PERFORMANCE_REPORT.md` and `apps/worker`'s own architecture notes on deliberately
avoiding a second web framework in a background-job service), and a healthcheck path present in a
config read by both services would have made the worker's deployment fail its health probe forever.
Railway's own restart-on-crash policy (`restartPolicyType: ON_FAILURE`) still recovers a genuinely
crashed container for both services; the API's actual readiness is instead verified directly via
the smoke tests below (curling `/health/live`/`/health/ready`), not via Railway's platform-level
gate. **Recommended follow-up**: whoever next has interactive Railway dashboard access should set a
per-service Config-as-code path (or at minimum re-enable `healthcheckPath` on just the `api`
service) to restore full fidelity — this is a two-click dashboard change, not a code change.

### Worker environment variables

Set on the new `worker` service to match the API service's already-correct values:
`ENVIRONMENT=production`, `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL=info` (via
`railway variable set ... --skip-deploys`, then picked up on the next real deploy from the git push
below).

### Deploy verification

After pushing the `railway.json`/`nixpacks.toml`/rate-limiter fix:

- `@rkpr/crm-backend`: build → deploy → `SUCCESS`. `curl https://rkprcrm-backend-production.up.railway.app/health/live` → `200 {"status":"ok"}`.
- `worker`: build → deploy → `SUCCESS`. Logs confirm it started the real ARQ worker (44 registered
  functions, `environment=production`, connected to Redis with 57 existing keys) — not uvicorn —
  and its cron schedule immediately executed real jobs against real data:
  `cron:run_complaint_sla_escalations` found and escalated 2 real complaints on its first run,
  `cron:dispatch_notification_deliveries` and `cron:send_reservation_reminders` ran cleanly with
  no pending work. This is the first time the `$RAILWAY_SERVICE_NAME`-branching startCommand has
  been exercised for real, and it worked correctly on the first deploy.

## Vercel — blocked, awaiting account access

The real dashboard deployment already exists (`crm-system-dashboard`, live at
`https://crm-system-dashboard-drab.vercel.app`, already referenced in the API's own
`CORS_ALLOWED_ORIGINS`), but under a Vercel login this session's CLI is not authenticated as. The
user was asked to re-run `vercel login` with the correct account; this is recorded as an open item,
not silently worked around, since guessing at or reconfiguring an unrelated Vercel project
(`crm-system-rkpr`, also linked in this repo but never deployed) would have been the wrong target.

## Rate-limit threshold tuning and a real test-isolation bug (found via genuine k6 load testing)

Per `tests/load/README.md`'s explicit "never against production," k6 was run against a **local**
instance of `apps/api` (same seeded database), not the live Railway deployment. k6 itself was not
installed in this sandboxed environment; it was installed locally via `scoop install k6` (an
approved locked tool per `docs/TOOLS.md` §12.5) rather than deferred again.

The first real run surfaced a genuine finding, not a fabricated one: `customers: status 200`
failed ~29% of the time under 20 concurrent VUs, all returning `{"code": "rate_limited"}`. This
was the general per-IP auth rate limiter (`app/auth/dependencies.py::get_current_staff_user`,
60 requests/60 seconds) — a check that runs on *every* authenticated request, before the token is
even decoded, correctly designed as an anti-brute-force/anti-flood guard but calibrated far too
low for legitimate concurrent multi-staff office traffic sharing one NAT'd IP (a single dashboard
page load alone fires several API calls). Raised to 1200/60s (20 req/s) after two intermediate
values (600, then a value that landed exactly on the test's own steady-state rate with no margin)
proved insufficient — 1200 gives real headroom above realistic concurrent office usage while
remaining a meaningful bound against actual flooding.

Diagnosing this also surfaced and fixed a real regression, not just a threshold problem:
**`apps/api/tests/conftest.py`'s existing `_reset_auth_rate_limiter` fixture only cleared the
in-process `RateLimiter`'s state between tests — never Redis.** Once the rate limiter started
trying Redis first (this phase's own migration), that per-test isolation silently stopped working:
Redis-backed rate-limit state persisted and accumulated across the *entire* pytest run. A full
`apps/api` suite run (2355s / ~39 minutes) confirmed this concretely: **31 failed, 1 errored**,
every failure an `assert 429 ...` in test files with no relationship to rate limiting
(`test_segments_api.py`, `test_staff_operations_api.py`, `test_tasks_api.py`,
`test_referrals_service.py`) — purely test-suite request volume tripping the shared Redis counter.
Fixed by extending the fixture to also call `app.cache.service.invalidate_prefix` on the
Redis-backed rate-limit key prefix before every test. Re-ran all 4 previously-failing files after
the fix: **39/39 passed.** A full-suite re-run was kicked off to confirm no other regressions;
its result is recorded in `docs/phase-17/VERIFICATION_REPORT.md` once complete.

Also caught and fixed along the way: three separate stray local `uv run python run.py` processes
ended up simultaneously bound to port 8000 (from incomplete process cleanup between manual test
iterations) — Windows allowed multiple listeners in this configuration, and requests were being
non-deterministically routed across old and new code, which is what produced the confusing
intermediate 600-threshold results. All local dev processes were force-cleared and one clean
instance verified (`netstat` showing exactly one listener) before the numbers reported above were
trusted. This was a local dev-environment artifact, not a deployed-service issue.

### Final clean local k6 result (one verified server instance, real seeded data)

```
checks_succeeded: 99.29% (560/564)
crm_errors: 0.47% (2/422)
http_req_duration: avg=439.65ms  p90=713ms  p95=949ms  max=9.56s
customers_list duration: avg=1.13s  p90=1.47s  p95=8.14s
```

p95 exceeds the script's own `<500ms` starting threshold (see the threshold's own comment: "starting
targets, not numbers measured in this environment" — this is the first time they have been). This
is real, unoptimized local-hardware latency, not production hardware; it is reported honestly
rather than adjusted to pass. Recommended follow-up once genuine production/staging infrastructure
performance data exists: investigate the `customers` list endpoint's p95 tail specifically (the gap
between its p90 of 1.47s and worst-case 9.56s suggests occasional slow outliers worth profiling,
not a uniformly slow endpoint).

### Live-deployment smoke verification (Railway, not k6 — read-only checks only, per "never against production")

- `GET /health/live` → `200 {"status":"ok"}`
- `GET /health/ready` → `200 {"status":"ok"}` (includes a live DB connectivity check)
- `GET /metrics` → real Prometheus exposition data, request histogram already populated
- `GET /docs` → `404` (confirmed disabled outside local/test, Phase 16 behavior holding in this deployment)
- Security headers present and correct on every response: `content-security-policy: default-src 'none'`,
  `strict-transport-security` (HSTS, environment-gated to staging/production — confirmed active),
  `x-frame-options: DENY`, `x-content-type-options: nosniff`, `referrer-policy`, `permissions-policy`.
- Worker service logs (see the Railway section above) confirm real DB read+write: `cron:run_complaint_sla_escalations`
  found and escalated 2 real complaints on its very first live run.

## Deferred, explicitly, not silently skipped

- **Sentry**: no `SENTRY_DSN` configured anywhere (API, worker, or dashboard). No CLI/API access to
  Sentry exists in this session and creating an account is outside what this session can do on the
  user's behalf. Exact setup steps (project creation, DSN retrieval, environment tagging) were
  given directly to the user in chat; wiring the resulting DSN values in is a five-minute follow-up
  once provided.
- **A real backup/restore rehearsal, final third-party provider credentials, and an approved
  production domain** remain unmet regardless of how this phase's staging/production labeling was
  resolved — these require external accounts/decisions this session cannot fabricate, per
  CLAUDE.md's explicit prohibition on claiming integration/production-readiness without verified
  configuration.
