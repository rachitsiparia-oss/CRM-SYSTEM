# RKPR RESTAURANT CRM — DEPLOYMENT AND ENVIRONMENT

## 1. DOCUMENT PURPOSE

This document defines how the RKPR Restaurant CRM is configured, deployed, promoted, validated, monitored, rolled back, and operated across local development, automated testing, staging, and production.

It must remain consistent with `PROJECT_PLAN.md`, `ARCHITECTURE_AND_TECH_STACK.md`, `DATABASE_AND_API.md`, `CORE_CRM_MODULES.md`, `OPERATIONS_MODULES.md`, `GROWTH_AND_INTELLIGENCE.md`, `INTEGRATIONS_AUTOMATIONS_REALTIME.md`, and `SECURITY_PERFORMANCE_AND_QUALITY.md`.

This document is authoritative for:

- repository and service deployment boundaries
- environment separation
- environment-variable ownership
- secret handling
- configuration validation
- database migration execution
- seed-data policy
- deployment order
- CI/CD behavior
- staging and production promotion
- worker and scheduler deployment
- health checks and smoke tests
- release verification
- rollback and recovery
- provider credential activation
- production-readiness requirements

Dummy values are allowed only as clearly marked local or test placeholders. Important values such as real credentials, production URLs, provider identifiers, webhook secrets, recovery objectives, legal requirements, sender identities, domain names, and production account details must never be invented.

**Docker is intentionally deferred** for this build. It is not used in local development, CI, or deployment at this stage. Its absence is a deliberate roadmap decision, not a missing capability — see `ROADMAP.md` Phase 1 notes. It will be introduced later, if needed, during deployment/environment hardening (Phase 16 onward), with an explicit decision recorded in `TOOLS.md` first.

## 2. APPROVED DEPLOYMENT ARCHITECTURE

### 2.1 Service map

The approved deployment model is:

- Dashboard frontend: Vercel
- FastAPI backend API: Railway
- Background worker and scheduler (ARQ): separate Railway service
- PostgreSQL, Supabase Auth, Supabase Storage, and controlled Supabase Realtime: one dedicated Supabase project
- Redis: Upstash Redis for cache, rate limits, locks, counters, idempotency, ARQ queue transport, and short-lived coordination
- Source control and CI: GitHub and GitHub Actions
- Error tracking: Sentry

The product is a single-resort deployment for RKPR. It is not a shared multi-tenant SaaS deployment. No tenant tables, tenant routing, tenant-specific databases inside one installation, or tenant-based RLS should be introduced.

### 2.2 Repository service mapping

The repository retains this structure:

- `apps/dashboard` — Next.js dashboard deployed to Vercel
- `apps/api` — FastAPI API deployed to Railway
- `apps/worker` — ARQ background worker and scheduler deployed separately to Railway
- `packages/{ui,contracts,api-client,config}` — shared contracts, configuration, utilities, and design primitives
- `docs` — project documents
- `tests` — cross-service and end-to-end tests where applicable
- `CLAUDE.md`, `ROADMAP.md` — at repository root

### 2.3 Deployment independence

The dashboard, API, and worker must be independently deployable.

A frontend deployment must not require a worker redeployment unless a shared contract changes.

An API deployment must remain compatible with the currently deployed dashboard during a controlled rollout.

A worker deployment must remain compatible with queued ARQ jobs and current database schema.

### 2.4 State ownership

- PostgreSQL remains the source of truth for domain data, jobs, outbox events, audit history, integration state, and configuration records.
- Redis is never the source of truth.
- Vercel frontend instances remain stateless.
- Railway API instances remain stateless except for approved external state.
- Railway workers remain replaceable and recoverable.
- Supabase Storage holds private file bytes while PostgreSQL stores file metadata.

## 3. ENVIRONMENT MODEL

### 3.1 Required environments

The project must support:

- local development
- automated test
- staging
- production

Each environment must have separate credentials, data, storage, URLs, provider accounts or provider modes where applicable, webhook endpoints, and observability configuration.

### 3.2 Local development

Local development is for implementation and developer testing.

Requirements:

- local frontend URL
- local API URL
- development database or approved isolated Supabase development project
- development Redis or isolated Upstash namespace
- non-production provider credentials or mocked adapters
- development Sentry environment or disabled local reporting
- safe local seed data
- no production customer data
- no production service credentials

Local development may use placeholders in `.env.example`, but placeholders must be unmistakable and must never be treated as valid configuration. Docker is not used for local supporting services in this build; use isolated Supabase/Upstash development projects instead.

### 3.3 Automated test environment

The automated test environment must be deterministic and isolated.

Requirements:

- dedicated test database or transaction-isolated test database
- test storage namespace
- mocked or sandbox provider adapters
- controlled time and randomness where needed
- isolated ARQ queue names or test worker mode
- no production webhooks
- no production recipients
- no production data
- automatic cleanup of test records and files

### 3.4 Staging

Staging should resemble production closely enough to validate deployments safely.

Requirements:

- separate Supabase project or formally isolated staging resources
- separate Railway API and worker services
- separate Vercel environment
- separate Upstash Redis database or namespace
- staging provider credentials or approved test modes
- staging webhook URLs
- staging Sentry environment
- realistic but non-production data
- production-like security headers and cookies
- migration and rollback rehearsal
- smoke and E2E validation

Staging must not use production credentials or real customer contact details unless explicitly approved for a controlled test.

### 3.5 Production

Production is the live RKPR system.

Requirements:

- approved production domains
- production Supabase project
- production Railway API and worker services
- production Vercel deployment
- production Upstash Redis configuration
- production provider credentials
- production webhook registration
- secure cookies
- explicit CORS allowlist
- CSRF protection according to the final session design
- security headers
- backups
- alerting
- Sentry
- health checks
- restore-tested recovery process
- no dummy credentials
- no test bypasses

## 4. ENVIRONMENT VARIABLE PRINCIPLES

### 4.1 General rules

Environment variables must be:

- documented
- validated at startup (Pydantic settings for API/worker)
- scoped to the service that needs them
- separated by environment
- absent from source control
- redacted from logs
- rotated without source-code changes
- represented in `.env.example` only with safe placeholders

### 4.2 Naming conventions

Use clear uppercase names with stable prefixes.

Examples of categories:

- `APP_`
- `ENVIRONMENT`
- `DATABASE_`
- `SUPABASE_`
- `REDIS_`
- `AUTH_`
- `CORS_`
- `STORAGE_`
- `SENTRY_`
- `OPENAI_`
- `GROQ_`
- provider-specific prefixes after formal approval
- `WORKER_`
- `QUEUE_`
- `WEBHOOK_`
- `RATE_LIMIT_`

Do not invent a final provider-specific variable name before the provider is approved in `TOOLS.md`.

### 4.3 Required startup validation

Each service must validate required configuration before accepting traffic or jobs.

Validation must distinguish:

- missing value
- malformed value
- invalid URL
- invalid enum
- impossible numeric range
- missing production-only requirement
- forbidden development value in production
- unsupported provider configuration

Production startup must fail safely when critical configuration is missing.

### 4.4 Public versus private variables

Frontend-exposed variables must be limited to values safe for browser delivery, and must be explicitly prefixed `NEXT_PUBLIC_` in the Next.js dashboard.

Private values include:

- database credentials
- Supabase service-role credentials
- provider API keys
- webhook secrets
- encryption keys
- session secrets
- internal service tokens
- Sentry server-side auth tokens
- deployment credentials

Public variables must never be used as substitutes for server-side authorization. Never expose service-role keys, database credentials, Redis credentials, AI keys, payment secrets, webhook secrets, or Sentry auth tokens through `NEXT_PUBLIC_*` variables.

## 5. SERVICE ENVIRONMENT MATRIX

### 5.1 Dashboard environment categories

The dashboard may require:

- public application name
- public dashboard base URL
- public API base URL
- public Supabase URL where the approved auth flow requires it
- public Supabase anon key where safe and approved
- Sentry public DSN if used in browser reporting
- environment name
- feature flags that are safe for the client

The dashboard must not receive:

- database URLs
- service-role keys
- provider secrets
- webhook secrets
- worker credentials
- unrestricted storage secrets

### 5.2 API environment categories

The API may require:

- environment name
- public API base URL
- allowed frontend origins
- database connection strings (psycopg 3)
- Supabase project URL
- Supabase server-side credentials required by the approved implementation
- auth audience and issuer settings
- Redis connection information (Upstash)
- storage bucket names
- Sentry configuration
- rate-limit settings
- file-size and upload constraints
- AI provider settings where enabled (Phase 14 only)
- approved integration credentials
- webhook secrets
- internal service authentication values

### 5.3 Worker environment categories

The worker may require:

- environment name
- database connection strings (psycopg 3)
- Redis and ARQ queue configuration
- storage configuration
- Sentry configuration
- provider credentials needed for background delivery
- worker concurrency settings
- job timeout settings
- queue names
- scheduler configuration (ARQ cron)
- maintenance-job settings
- AI provider settings where background AI work is enabled (Phase 14 only)

### 5.4 Shared configuration

Shared values must remain semantically identical across services when they represent the same concept, for example:

- environment name
- API version
- event schema version
- queue names
- storage bucket names
- Sentry release identifier
- application timezone

Business display timezone is `Asia/Kolkata`. Stored timestamps remain UTC unless a provider contract requires otherwise.

## 6. ENVIRONMENT FILES

### 6.1 `.env.example`

The repository should include safe example files such as:

- root `.env.example` where useful
- `apps/dashboard/.env.example`
- `apps/api/.env.example`
- `apps/worker/.env.example`

Each entry should include a short comment describing:

- purpose
- required service
- whether required in local, staging, or production
- whether public or private
- accepted format

Example files must never contain real credentials. All placeholder values must be obviously fake, for example:

```text
SUPABASE_URL=https://example.supabase.co
SUPABASE_ANON_KEY=replace_me
SUPABASE_SERVICE_ROLE_KEY=replace_me_server_only
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
REDIS_URL=rediss://default:password@example.upstash.io:6379
SENTRY_DSN=replace_me
```

### 6.2 Local environment files

Local `.env` files must be ignored by Git (`.gitignore`).

A pre-commit or CI secret scan should detect accidental credential commits.

### 6.3 Configuration documentation

`TOOLS.md` remains the authoritative list of approved providers and libraries. This document describes deployment wiring without inventing tool decisions.

## 7. DATABASE CONNECTIONS

### 7.1 Connection usage

The API and worker use the psycopg 3 driver with SQLAlchemy 2.x, with connection strings appropriate to their runtime and pooling needs.

Migrations (Alembic) may use a direct connection distinct from pooled runtime connections.

**Use the Supabase connection pooler (Session mode, port 5432), not the direct `db.<ref>.supabase.co:5432` host.** The direct host is IPv6-only on most Supabase projects and will time out with a connection timeout on networks without IPv6 egress (confirmed during Phase 2 setup). The pooler host follows the pattern `aws-<n>-<region>.pooler.supabase.com`, with username `postgres.<project-ref>` instead of plain `postgres` — find the exact values under Project Settings → Database → Connection string → Session pooler in the Supabase dashboard. Session mode (not Transaction mode, port 6543) is used for both the application runtime and Alembic migrations, since DDL and long-running transactions behave better outside transaction pooling.

**Windows local development note:** psycopg 3's async mode refuses to run under Windows' default `ProactorEventLoop` — it requires a selector-based event loop. `apps/api/run.py` sets the correct event loop policy before starting uvicorn; do not run `uvicorn app.main:app` directly on Windows, as the plain CLI creates its event loop before the app module (and its policy fix) is ever imported. This is a no-op on Linux/macOS (Railway, CI, production).

### 7.2 Connection rules

- TLS required
- credentials environment-specific
- pool sizes bounded
- connection timeout explicit
- statement timeout where appropriate
- no database URL in frontend code
- no connection string in logs
- database health check does not reveal credentials

### 7.3 Migration credentials

Where feasible, migration credentials should be separated from runtime application credentials.

The runtime service should not receive schema-altering permissions it does not need.

## 8. DATABASE MIGRATIONS

### 8.1 Migration tool

Alembic remains the approved migration tool.

### 8.2 Migration requirements

Migrations must be:

- deterministic
- version-controlled
- reviewed
- tested on realistic data
- safe for current production volume
- reversible where practical
- accompanied by recovery instructions where reversal is unsafe
- compatible with deployment order

### 8.3 Migration deployment order

A standard release should follow this pattern where applicable:

1. validate backup and restore readiness
2. deploy backward-compatible database migration
3. verify schema and migration state
4. deploy API compatible with old and new callers
5. deploy workers compatible with existing queued ARQ jobs
6. deploy dashboard
7. enable new behavior or feature flag
8. run post-release checks
9. remove compatibility code only in a later release

### 8.4 Destructive migrations

Destructive changes require explicit review.

Examples:

- dropping columns
- changing money representation (not applicable — money representation is permanently fixed, see `DATABASE_AND_API.md` §3.3)
- rewriting financial history
- changing primary keys
- deleting audit records
- converting status values
- removing event fields
- shrinking text or numeric ranges

Preferred expand-and-contract approach:

1. add new structure
2. backfill
3. dual-read or dual-write if required
4. validate
5. switch readers
6. stop old writes
7. remove old structure in a later release

### 8.5 Migration failure

A failed migration must:

- stop the release
- preserve logs
- identify migration revision
- prevent incompatible application deployment
- trigger the documented recovery or rollback plan

## 9. SEED DATA

### 9.1 Seed-data purpose

Seed data supports local development, automated tests, staging demonstrations, and controlled acceptance testing.

### 9.2 Canonical RKPR dummy data

Use the same established RKPR sample records across all project documents and fixtures, including the same:

- menu items and prices
- customer examples
- staff references (the canonical 65-person set)
- suppliers
- inventory items
- corporate lead references
- statuses
- workflow examples

Do not create competing sample identities or prices without updating the full canonical dataset.

### 9.3 Production seeding

Production seeds should include only required structural data, for example:

- permission registry (the single canonical capability registry)
- system status values where table-driven
- initial approved roles
- required configuration defaults
- approved notification types

Production must not receive dummy customers, dummy orders, dummy payments, dummy provider records, or test staff accounts unless explicitly approved for a controlled launch test and removed afterward.

### 9.4 Seed idempotency

Seed scripts must be safe to rerun and should use stable identifiers or unique keys.

## 10. VERCEL DASHBOARD DEPLOYMENT

### 10.1 Project setup

The Vercel project should point to `apps/dashboard` or the approved monorepo build configuration.

### 10.2 Build requirements

The production build must run:

- dependency installation from `pnpm-lock.yaml`
- formatting or lint validation according to CI
- strict TypeScript checking
- production Next.js build
- environment validation

### 10.3 Vercel environments

Configure separately:

- Development
- Preview
- Production

Preview deployments must not automatically gain production secrets.

### 10.4 Frontend URLs

Approved URLs must be configured explicitly.

The dashboard must use the correct API base URL for each environment.

### 10.5 Security

- no private credentials in browser variables
- production security headers
- secure cookie compatibility
- explicit API CORS configuration
- source maps handled according to Sentry policy
- no development endpoints in production build

### 10.6 Frontend smoke checks

Verify:

- login page loads
- authenticated shell loads
- API requests reach correct environment
- unauthorized state behaves correctly
- key routes render
- no console-level secret leakage
- Sentry release is correct

## 11. RAILWAY API DEPLOYMENT

### 11.1 API service

The API should be deployed as a dedicated Railway service from `apps/api`.

**Do not rely on Railway/Nixpacks auto-detection in this repository, and do not rely on `railway.json`'s `build.buildCommand` alone.** The repo root contains both `package.json` (pnpm workspace) and `pyproject.toml` (uv workspace). Nixpacks' auto-detect picks a Node/pnpm provider from the presence of `package.json`, and — critically — a custom `build.buildCommand` in `railway.json` only overrides Nixpacks' **build** phase; the auto-detected Node **setup** and **install** phases (installing Node, corepack, and running `pnpm i`) still run first regardless, and have been observed failing on an unrelated Node/corepack bug before the Python build command ever executes.

The fix is the committed root `nixpacks.toml`, which replaces Nixpacks' phase auto-detection entirely (`[phases.setup]`, `[phases.install]`, `[phases.build]`) so only Python 3.12 and `curl` are ever installed — Node and pnpm are never invoked for this service. `uv` itself is installed via the official installer script (not `pip install uv`, since Nixpacks does not reliably provision `pip` for a mixed-language repo). `railway.json` then only owns the **deploy**-phase settings: `deploy.startCommand`, `healthcheckPath`, and restart policy.

**Root Directory must stay unset (repository root) in the Railway service settings — do not set it to `apps/api`.** `apps/api` is a `uv` workspace member: its dependency resolution needs the workspace root `pyproject.toml` and `uv.lock` (and the sibling `apps/worker` member) to be present, which a scoped root directory would hide.

**Watch Paths must also stay empty/unset** in the Railway service settings. A non-empty Watch Paths left over from Railway's initial auto-detection (scoped to dashboard files) has been observed silently skipping rebuilds entirely — including on `railway up` — with "no changes detected in watch paths," even when `nixpacks.toml`/`railway.json` changed.

When a second Railway service is created for `apps/worker` (Phase 17/18), it needs its own phase plan and start command (`uv sync --package rkpr-worker` / `uv run --package rkpr-worker arq worker.main.WorkerSettings`) — either via that service's own Railway-dashboard "Config File Path" pointing at separate `nixpacks.toml`/`railway.json` files, or via manual dashboard overrides, since the root-level files described here only cover the API service.

### 11.2 Runtime requirements

- Python 3.12.x
- production ASGI server configuration
- bounded worker count appropriate to Railway resources
- startup environment validation
- database connectivity (psycopg 3)
- Redis connectivity where required (Upstash)
- Sentry initialization
- health endpoints
- graceful shutdown

### 11.3 Health endpoints

At minimum:

- liveness endpoint (`/health/live`): process is alive
- readiness endpoint (`/health/ready`): service can accept traffic

Readiness may include critical dependencies such as database availability. Optional provider failures should not necessarily mark the whole API unready.

Phase 15 adds `GET /metrics` (Prometheus exposition format, unauthenticated) alongside these — aggregate request latency/count, cache hit/miss, and derived job-queue/dead-letter/integration-health gauges computed at scrape time from PostgreSQL. This is instrumentation only: no Prometheus server, Grafana, or hosted monitoring SaaS is deployed as part of this project (`TOOLS.md`'s restriction on adding a full observability stack). `apps/worker` has no HTTP server of its own and therefore no `/metrics` or `/health/*` endpoints — its liveness is observed indirectly through the `heartbeat` cron job's `JobRecord` history and through the scrape-time job-queue gauges `apps/api`'s `/metrics` already exposes, deliberately avoiding a second web framework in a background-job service (`CLAUDE.md` §20).

### 11.4 Startup behavior

The API must not automatically run unsafe migrations on every process start.

Migration execution must be an explicit release step or controlled Railway job.

### 11.5 Logging

Railway logs must be structured (structlog) and redact secrets.

## 12. RAILWAY WORKER AND SCHEDULER DEPLOYMENT

### 12.1 Separate service

The ARQ worker and scheduler must run separately from the API.

This prevents long jobs, campaigns, exports, file processing, AI work, or provider retries from consuming API capacity.

### 12.2 Worker responsibilities

- consume background jobs (ARQ)
- publish outbox events
- execute communications
- run reports and exports
- process files
- refresh segments
- run loyalty and feedback tasks
- execute integration reconciliation
- perform scheduled maintenance (ARQ cron)

### 12.3 Worker configuration

- explicit queue names
- bounded concurrency
- job timeouts
- graceful shutdown
- stale-lock recovery
- retry limits
- dead-letter behavior
- health reporting
- Sentry

### 12.4 Scheduler

The ARQ cron scheduler must avoid duplicate recurring jobs after restart or horizontal scaling.

Use stable schedule identifiers and distributed coordination where required.

### 12.5 Worker deployment checks

Verify:

- worker connects to the ARQ/Redis queue
- worker connects to database
- scheduler owns expected schedules
- test job succeeds
- retry behavior works
- dead-letter path is visible
- no production-recipient test message is sent

## 13. SUPABASE CONFIGURATION

### 13.1 Dedicated project

Use one dedicated Supabase project for the RKPR production deployment.

### 13.2 Supabase components

- PostgreSQL
- Supabase Auth
- private Supabase Storage
- controlled Supabase Realtime

### 13.3 Auth configuration

Configure:

- approved site URL
- approved redirect URLs
- email verification rules
- recovery flow
- token settings
- session behavior
- MFA readiness where supported

### 13.4 Storage configuration

- private buckets
- approved file categories
- size limits
- MIME and signature validation in backend
- short-lived signed URLs
- quarantine and malware-scan flow where required

### 13.5 Realtime configuration

Realtime must remain scoped and authenticated.

Do not enable broad table exposure.

Backend-published events or explicitly controlled change streams should be used according to the architecture.

### 13.6 Backups

Enable the approved backup strategy and monitor backup success.

Final retention, RPO, and RTO require formal approval and must not be invented.

## 14. UPSTASH REDIS CONFIGURATION

### 14.1 Uses

- caching
- rate limits
- bounded locks
- idempotency windows
- short-lived counters
- ARQ queue transport and coordination
- pub/sub or coordination where approved

### 14.2 Environment separation

Use separate Upstash databases or namespaces for local, staging, and production.

### 14.3 Key rules

- versioned prefixes
- explicit TTLs
- no source-of-truth records
- no unbounded key growth
- no secrets in keys
- safe fallback when Redis is unavailable

Before implementing ARQ against Upstash, verify technical compatibility with the actual Redis connection mode and feature requirements. If a proven incompatibility is found, stop and report the exact issue before replacing either tool (see `TOOLS.md` §7.3).

## 15. SENTRY CONFIGURATION

### 15.1 Environments

Use distinct Sentry environment names for:

- development
- staging
- production

### 15.2 Release tracking

Dashboard, API, and worker should report a shared release identifier when deployed from the same release.

### 15.3 Data safety

Before sending events to Sentry:

- redact secrets
- minimize customer content
- avoid full tokens
- avoid full request bodies by default
- include request and correlation IDs

### 15.4 Alerts

Configure alerts for critical production errors, regressions, worker failures, and release health according to `SECURITY_PERFORMANCE_AND_QUALITY.md`.

## 16. GITHUB AND CI/CD

### 16.1 Source control

GitHub is the source-control platform.

### 16.2 Branch strategy

The exact branch naming may remain lightweight, but production-bound changes should use pull requests and protected branches.

### 16.3 Pull-request CI

Run:

- formatting checks (Ruff, Prettier/ESLint)
- frontend linting
- backend linting (Ruff)
- strict TypeScript checks
- Python type checks (mypy)
- unit tests (Pytest, Vitest)
- integration tests where feasible
- migration validation
- frontend production build
- backend startup/import validation
- dependency vulnerability scans
- secret scan

### 16.4 Deployment permissions

Untrusted pull-request jobs must not receive production secrets.

Production deployment should require approved branch and successful CI.

### 16.5 Deployment triggers

Deployments may be triggered by merges to the approved production branch or explicit release workflow.

Database migrations must remain an explicit controlled step.

## 17. RELEASE VERSIONING

### 17.1 Release identifier

Each release should have a stable identifier, for example a semantic version, date-based version, or Git commit SHA.

The selected strategy should be consistent across:

- dashboard
- API
- worker
- Sentry
- release notes
- migration records

### 17.2 API versioning

Public API remains under `/api/v1` until a breaking version is formally introduced.

### 17.3 Event versioning

Domain and realtime event payloads retain explicit versions as defined in `INTEGRATIONS_AUTOMATIONS_REALTIME.md`.

## 18. DEPLOYMENT WORKFLOW

### 18.1 Pre-deployment

Confirm:

- pull request approved
- CI green
- environment variables complete
- migration reviewed
- backup and rollback readiness
- staging validated
- provider changes reviewed
- release notes prepared
- monitoring ready

### 18.2 Standard deployment sequence

1. freeze the intended release commit
2. validate environment configuration
3. verify backup status
4. run approved database migrations
5. verify migration revision
6. deploy API
7. verify API readiness
8. deploy worker and scheduler
9. verify queues and schedules
10. deploy dashboard
11. run smoke tests
12. verify Sentry release health
13. monitor errors, latency, and backlog
14. mark release complete
15. update `ROADMAP.md` when a phase is completed

### 18.3 Feature flags

Feature flags may be used for high-risk or incomplete features.

Rules:

- flags are documented
- production default is safe
- backend enforcement remains present
- stale flags are removed
- flags do not replace migrations or permissions

## 19. SMOKE TESTS

After deployment verify:

- dashboard loads
- login works
- logout works
- session refresh works
- API liveness and readiness
- authenticated API call
- database read and write
- ARQ worker test job
- outbox dispatch
- queue health
- realtime connection where enabled
- storage signed URL flow
- Sentry event capture
- critical module route load
- no unexpected migration drift

For production, smoke tests must avoid destructive actions and real customer communication unless explicitly planned.

## 20. POST-DEPLOYMENT VALIDATION

Monitor:

- API error rate
- p95 latency
- authentication failures
- authorization denials
- database connections
- slow queries
- worker failures
- queue latency
- dead-letter count
- webhook failures
- integration health
- realtime failures
- frontend errors
- deployment health

## 21. ROLLBACK

### 21.1 Application rollback

Vercel, Railway API, and Railway worker should support rollback to the last known good release.

### 21.2 Configuration rollback

Environment-variable changes must be documented and reversible.

### 21.3 Integration rollback

A failing integration may be paused or disabled without disabling unrelated CRM modules.

### 21.4 Database rollback

Database rollback is migration-specific and must never be assumed safe.

Preferred recovery may include:

- forward-fix migration
- application rollback while preserving expanded schema
- restore from backup only when necessary and approved

### 21.5 Rollback trigger examples

- critical security regression
- failed migration
- high error rate
- broken login
- data corruption
- severe latency regression
- worker processing failure
- incompatible API contract

## 22. BACKUP AND RESTORE OPERATIONS

### 22.1 Backup scope

- PostgreSQL
- storage objects or recoverable storage strategy
- migration history
- critical configuration
- infrastructure configuration where practical

### 22.2 Restore validation

Periodic restore tests must verify:

- database integrity
- application compatibility
- authentication linkage
- permissions
- file references
- audit history
- critical workflows

### 22.3 Production launch requirement

Production launch requires an approved backup strategy and at least one successful restore test.

## 23. WEBHOOK DEPLOYMENT

### 23.1 Environment-specific endpoints

Each environment uses separate webhook URLs and secrets.

### 23.2 Registration

Provider webhook registration must occur only after:

- endpoint is deployed
- HTTPS works
- signature verification is configured
- secret is stored securely
- test event is validated

### 23.3 Rotation

Webhook-secret rotation requires overlap or coordinated cutover where supported.

## 24. PROVIDER ACTIVATION

An integration is not active merely because credentials exist.

Activation requires:

- approved provider in `TOOLS.md`
- valid credentials
- successful health check
- webhook registration where required
- correct environment
- correct sender or account identity
- rate limits configured
- test operation successful
- audit record

No dummy provider account may be shown as production-ready.

## 25. DOMAIN AND DNS

Production domains and subdomains must be formally approved.

Configuration may include:

- dashboard domain
- API domain
- webhook domain or API paths
- email authentication records where applicable

Do not invent final domains in documentation or code.

TLS must be enforced.

## 26. CORS, COOKIES, AND SESSION DEPLOYMENT

Production must configure:

- explicit frontend origin allowlist
- secure cookies
- appropriate SameSite policy
- CSRF protection
- trusted proxy settings where required
- correct redirect URLs

Preview deployments must not automatically become trusted production origins.

## 27. JOB AND QUEUE DEPLOYMENT SAFETY

- ARQ queue names environment-specific
- no shared staging and production queue
- bounded concurrency
- graceful worker shutdown
- jobs recover after restart
- retries preserve idempotency
- stale locks recover
- scheduled jobs do not duplicate
- dead-letter queue visible
- bulk queues isolated from critical queues

## 28. FILE AND STORAGE DEPLOYMENT SAFETY

- private buckets
- environment-specific bucket names or projects
- quarantine flow where required
- malware scanner configuration where implemented
- signed URL expiry
- upload size limits
- file retention jobs
- no public bucket introduced for convenience

## 29. AI ENVIRONMENT CONFIGURATION

AI remains optional and advisory, and is configured only in Phase 14 — not during the foundation phase.

Configuration may include:

- OpenAI primary provider settings
- Groq optional fallback settings
- approved model identifiers
- timeouts
- budgets
- rate limits
- prompt versions

No RAG, embeddings, vector search, or pgvector are part of this project.

Core CRM workflows must remain operational when AI is unavailable.

## 30. ENVIRONMENT VALIDATION CHECKLIST

For each environment verify:

- correct environment name
- correct frontend URL
- correct API URL
- correct database
- correct Supabase project
- correct Upstash Redis namespace
- correct storage bucket
- correct Sentry environment
- correct CORS origins
- correct redirect URLs
- correct webhook URLs
- no production secret in development
- no test value in production
- required variables present
- optional integrations disabled when unconfigured

## 31. PRODUCTION READINESS CHECKLIST

Before production deployment:

- production domains approved
- Vercel production project configured
- Railway API configured
- Railway worker configured
- Supabase production project configured
- Upstash Redis production configuration ready
- Sentry configured
- GitHub branch protection enabled
- CI green
- environment validation passes
- migrations tested
- backups enabled
- restore test completed
- secure cookies configured
- CORS allowlist configured
- CSRF strategy configured
- security headers configured
- provider credentials validated
- webhooks verified
- queue health verified
- Sentry alerts configured
- smoke-test plan ready
- rollback plan ready
- no dummy credentials
- no dummy production URLs
- no test bypasses

## 32. DEFINITION OF DONE

Deployment and environment setup is complete only when:

- all services are in the approved platforms
- environment separation is real
- required variables are documented and validated
- secrets are not exposed
- migrations are controlled
- seed data follows canonical RKPR fixtures (including the 65-person staff set)
- production has no dummy business records unless explicitly approved
- API and worker health checks exist
- CI passes
- staging validation passes
- smoke tests pass
- monitoring and alerting are active
- backups and restore testing are complete
- rollback procedures are documented
- provider activation is verified
- `ROADMAP.md` is updated after phase completion

## 33. FINAL IMPLEMENTATION COMMAND

Deploy the RKPR Restaurant CRM as three coordinated but independently deployable services: the Next.js dashboard on Vercel, the FastAPI backend on Railway, and the ARQ background worker and scheduler as a separate Railway service. Use one dedicated Supabase project for PostgreSQL, Auth, private Storage, and controlled Realtime; use Upstash Redis for temporary coordination; use GitHub Actions for quality gates; and use Sentry for error tracking. Keep local, test, staging, and production fully separated. Validate configuration at startup, protect every secret, run Alembic migrations as an explicit controlled release step, preserve backward compatibility during deployment, verify health and smoke tests after release, and maintain documented rollback and restore procedures. Docker remains deliberately deferred until a later phase. Never invent provider credentials, production URLs, domains, recovery objectives, or critical environment decisions.
