# RKPR Restaurant CRM

A private, production-grade CRM built specifically for one RKPR fast-food restaurant. This is **not** a generic CRM template, multi-tenant SaaS product, no-code platform, or white-label system — see [`CLAUDE.md`](CLAUDE.md) for the full non-negotiable rules that govern every change in this repository.

## Architecture summary

- **Dashboard**: Next.js (App Router), TypeScript strict, Tailwind CSS, shadcn/ui + Radix, TanStack Query, React Hook Form + Zod. Deployed to Vercel.
- **API**: FastAPI, Pydantic v2, SQLAlchemy 2.x + Alembic, psycopg 3. The single authoritative layer for validation, authorization, business rules, and calculations. Deployed to Railway.
- **Worker**: ARQ (Redis-backed) background jobs and scheduler, deployed as a separate Railway service.
- **Data platform**: dedicated Supabase project (PostgreSQL, Auth, Storage, controlled Realtime), Upstash Redis for ephemeral coordination.
- **Single-business, non-multi-tenant.** No `tenant_id`, no tenant tables, no tenant-based RLS.

Full architecture detail: [`docs/ARCHITECTURE_AND_TECH_STACK.md`](docs/ARCHITECTURE_AND_TECH_STACK.md).

## Repository structure

```text
apps/
├── dashboard/   Next.js CRM dashboard
├── api/         FastAPI backend (rkpr-api)
└── worker/      ARQ background worker and scheduler (rkpr-worker)
packages/
├── ui/          shared design-system primitives (grows once a second app needs them)
├── contracts/   shared API contracts, error shapes, pagination types
├── api-client/  typed API client foundation
└── config/      non-secret shared configuration
docs/            the twelve canonical project specification documents
archive/         original .docx source documents, preserved unchanged
tests/           cross-service integration, e2e, security, and fixture assets
.github/workflows/  CI
```

Docker is intentionally deferred — see [`docs/TOOLS.md`](docs/TOOLS.md) §15. Its absence is a deliberate decision, not a missing capability.

## Documentation authority order

When documents disagree, resolve in this order (see [`CLAUDE.md`](CLAUDE.md) §1.1 for the full rule):

1. `CLAUDE.md`
2. The domain-specific document authoritative for the affected area
3. `docs/PROJECT_PLAN.md`
4. `docs/ARCHITECTURE_AND_TECH_STACK.md`
5. `docs/TOOLS.md`
6. `docs/DEPLOYMENT_AND_ENV.md`
7. `ROADMAP.md` — the single canonical phase sequence and status tracker

## Prerequisites

- Node.js (see [`.node-version`](.node-version)) with [Corepack](https://nodejs.org/api/corepack.html) enabled
- [pnpm](https://pnpm.io/) (workspace package manager, enabled via Corepack)
- Python 3.12.x (see [`.python-version`](.python-version))
- [uv](https://docs.astral.sh/uv/) (Python dependency and environment manager)
- Git

## Local setup

```bash
# JavaScript/TypeScript workspace
corepack enable
pnpm install

# Python workspace (api + worker share one uv workspace and lockfile)
uv sync --all-packages
```

Copy environment templates and fill in local values (never commit real credentials):

```bash
cp .env.example .env
cp apps/dashboard/.env.example apps/dashboard/.env.local
cp apps/api/.env.example apps/api/.env
cp apps/worker/.env.example apps/worker/.env
```

## Approved commands

| Task | Command |
| --- | --- |
| Run the dashboard dev server | `pnpm --filter @rkpr/dashboard dev` |
| Lint the dashboard | `pnpm --filter @rkpr/dashboard lint` |
| Typecheck the dashboard | `pnpm --filter @rkpr/dashboard typecheck` |
| Dashboard unit tests | `pnpm --filter @rkpr/dashboard test` |
| Dashboard e2e tests | `pnpm --filter @rkpr/dashboard test:e2e` |
| Production build | `pnpm --filter @rkpr/dashboard build` |
| Run the API locally | `uv run --package rkpr-api python apps/api/run.py` (do not run `uvicorn` directly on Windows — see note below) |
| Run the worker locally | `uv run --package rkpr-worker arq worker.main.WorkerSettings` (from `apps/worker`) |
| Lint/format the backend | `uv run ruff check apps/api apps/worker` / `uv run ruff format apps/api apps/worker` |
| Type-check the backend | `uv run --package rkpr-api mypy apps/api/app` / `uv run --package rkpr-worker mypy apps/worker/worker` |
| Backend tests | `uv run --package rkpr-api pytest apps/api/tests` / `uv run --package rkpr-worker pytest apps/worker/tests` |
| Run/create database migrations | `uv run --package rkpr-api alembic upgrade head` / `alembic revision --autogenerate -m "..."` (from `apps/api`) |
| Run canonical seed data | `uv run --package rkpr-api python apps/api/app/db/seed.py` |
| Bootstrap the first owner account | `uv run --package rkpr-api python -m app.db.bootstrap_owner --auth-user-id <uuid> --email <email> --first-name <name> --last-name <name>` (from `apps/api`, after creating that user in Supabase Auth) |

> **Windows note:** always start the API via `apps/api/run.py`, not `uvicorn app.main:app` directly. psycopg 3's async mode requires a selector-based event loop; the plain `uvicorn` CLI creates Windows' default `ProactorEventLoop` before our app code ever runs, which is too late to fix. `run.py` sets the correct policy first. This is a no-op (and unnecessary, but harmless) on Linux/macOS/Railway.

## Testing

- **Frontend**: Vitest + React Testing Library for unit/component tests, Playwright for end-to-end journeys.
- **Backend**: Pytest + pytest-asyncio + HTTPX test client. Database-backed tests (`apps/api/tests/test_db_foundation.py`) run against the real configured `DATABASE_URL` inside a SAVEPOINT that is always rolled back, so they never leave data behind; they skip automatically (not fail) when `DATABASE_URL` isn't set, which is why they currently skip in CI — no database credential is configured there yet.
- **Load testing**: k6, run before production launch — never against production itself.

## Production status

**Production deployment and third-party provider integration are deferred.** No production domains, payment provider, communication providers (WhatsApp/email/SMS final accounts), or AI provider credentials exist yet — see [`ROADMAP.md`](ROADMAP.md) for the phase each of these is scheduled in, and [`docs/DEPLOYMENT_AND_ENV.md`](docs/DEPLOYMENT_AND_ENV.md) for the full deployment model. This repository has completed **Phase 3 — Authentication, Users, Roles, and Permissions**; Phase 4 (Dashboard Shell and Shared UI System) has not started.
