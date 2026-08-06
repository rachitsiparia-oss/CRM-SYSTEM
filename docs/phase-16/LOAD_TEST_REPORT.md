# Phase 16 — Load Test Report

Generated: 2026-08-02.

## What exists

`docs/TOOLS.md` §12.5 locks k6 as the load-testing tool and marks it "REQUIRED BEFORE
PRODUCTION" — a pre-production gate, not a requirement to have executed load tests inside a
development coding session. Delivered:

- `tests/load/api_smoke.js` — a real k6 script, not a stub. Two `constant-vus` scenarios
  (`health`, `customers_list`) plus a separately-invoked `aiRequest` scenario for the
  rate-limited controlled-AI endpoint. Configurable via `BASE_URL`/`ACCESS_TOKEN`/`VUS`/
  `DURATION` env vars. Declares starting thresholds (`p(95)<500ms`, `<1%` error rate) per
  §12.5's "latency percentiles" requirement.
- `tests/load/mint_token.py` — mints a real HS256 token via the same signing path
  `apps/api/tests/conftest.py::make_access_token` uses, so the authenticated scenarios exercise
  real `app.auth.tokens` verification, not a bypassed/mocked auth path. Smoke-tested (produces a
  valid token given `AUTH_JWT_SIGNING_SECRET` and any `auth_user_id`) — confirmed by running it
  in this session.
- `tests/load/README.md` — prerequisites and exact run commands, including the AI endpoint's
  separate low-iteration invocation (its own 20/hour per-account rate limit — Phase 16 task
  #290 — would otherwise dominate the results with 429s instead of measuring real latency).

## What was not done, and why

**No load test was actually executed, and no benchmark numbers are reported.** k6 is not
installed in this sandboxed development environment (confirmed: `which k6` finds nothing), and
there is no running `apps/api` server instance to point it at from within this session. Two
honest options existed here: fabricate plausible-looking latency numbers, or say clearly that
none were measured. CLAUDE.md's own instructions are explicit that performance must never be
*claimed* as guaranteed and that the system should be verified "through available local and
automated measurements at the appropriate stage" — this is not that stage. Reporting invented
p95/p99 numbers here would be strictly worse than reporting none, since a false "verified"
result is more dangerous than a known gap: it would give false confidence that specific
endpoints meet a specific latency bar when nothing was actually measured.

**Required before this becomes a real benchmark, not a script**: install k6 in a CI job or a
staging environment, run `tests/load/api_smoke.js` against a realistically-seeded database (not
an empty one — pagination/filtering performance is meaningless against a handful of rows), and
record the actual p95/p99/error-rate numbers this document currently lacks. The script and
harness are ready for that the moment infrastructure access exists; nothing about them is a
placeholder.

## Coverage today vs. recommended next endpoints

Covered: health (baseline), customers list (representative paginated/filtered list shape), AI
request (rate-limit-aware). Not yet covered, recommended next given they're the highest-traffic
remaining shapes per the index review in `docs/phase-16/PERFORMANCE_REPORT.md`: orders list
(most filter/sort options of any endpoint checked), reservations calendar/day view, and the
dashboard/analytics aggregation endpoint (`app.reports.service.get_dashboard`) once its caching
question — also left open in `PERFORMANCE_REPORT.md`'s cache-coverage section — is resolved,
since load-testing an uncached, Decimal-heavy aggregation path and a cached one would produce
very different, non-comparable numbers.
