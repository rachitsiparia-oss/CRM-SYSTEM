# Load tests (k6)

`docs/TOOLS.md` section 12.5 — k6 is the locked load-testing tool, **required before
production**, run in CI or staging, never against production.

## What's here

- `api_smoke.js` — the k6 script itself. Covers three endpoint shapes: unauthenticated health
  (`/health/live`), an authenticated paginated list (`GET /api/v1/customers`), and the
  controlled-AI request endpoint (`POST /api/v1/ai/requests`, run separately given its 20/hour
  per-account rate limit — see below).
- `mint_token.py` — mints a real HS256 access token for the authenticated scenarios, using the
  same signing path `apps/api/tests/conftest.py::make_access_token` uses for the pytest suite.

## Prerequisites

1. [Install k6](https://k6.io/docs/getting-started/installation/) — not installed in this
   sandboxed development environment, so no benchmark numbers were recorded here; see
   `docs/phase-16/LOAD_TEST_REPORT.md` for what that means and what to run before production.
2. A running `apps/api` instance pointed at a seeded database (`uv run uvicorn app.main:app` from
   `apps/api`, or the deployed staging URL).
3. A real `StaffUser.auth_user_id` from that environment's database, for minting a token:
   `SELECT auth_user_id FROM staff_users WHERE email = '<a seeded staff email>';`

## Running

```bash
cd apps/api
TOKEN=$(uv run python ../../tests/load/mint_token.py --auth-user-id <uuid>)
k6 run -e BASE_URL=http://localhost:8000 -e ACCESS_TOKEN="$TOKEN" ../../tests/load/api_smoke.js
```

Override `VUS` (virtual users, default 10) and `DURATION` (default 30s) as needed:

```bash
k6 run -e VUS=50 -e DURATION=2m -e ACCESS_TOKEN="$TOKEN" tests/load/api_smoke.js
```

### AI endpoint (rate-limited — run separately, in small numbers)

`POST /api/v1/ai/requests` has its own per-staff-account limit (20/hour —
`app/controlled_ai/router.py`). Running it inside the main `constant-vus` scenarios above would
mostly measure 429s, not real latency. Exercise it explicitly, in low iteration counts:

```bash
k6 run --iterations 5 -e ACCESS_TOKEN="$TOKEN" -e SCENARIO=ai tests/load/api_smoke.js
```

(`aiRequest` is exported from `api_smoke.js` for exactly this — see the script's own comments.)

## Extending

Add a new `exec` function plus a matching `scenarios` entry in `options` for any other endpoint
worth benchmarking — orders, reservations, inventory, reports are the next-highest-value
additions once this baseline is running in CI/staging (`docs/TOOLS.md` 12.5's required
capabilities: HTTP load testing, controlled concurrency, latency percentiles, scenario
scripting, CI or staging execution — all four already apply to this script's structure).
