# RKPR RESTAURANT CRM — ROADMAP

## Purpose

This file is the **single canonical execution sequence and status tracker** for the RKPR Restaurant CRM. It is the one and only source of phase numbering. No other document may define a different phase sequence; `PROJECT_PLAN.md` maps its detailed business and functional scope onto the phases defined here.

Claude must update each phase after completion by changing its status, adding the completion date, and writing a brief completion note. Detailed implementation requirements remain in the main project documents (see `CLAUDE.md` §2 for the document authority order).

## Status values

Use only these four values:

- `NOT STARTED`
- `IN PROGRESS`
- `BLOCKED`
- `COMPLETED`

A phase must not be marked `COMPLETED` merely because files were created. Completion requires all acceptance criteria and checks for that phase to pass.

## Phase 0 — Project Rules and Documentation Lock

Status: COMPLETED

Scope:

- Review all authoritative project documents
- Confirm module boundaries
- Confirm canonical RKPR dummy data
- Confirm no multi-tenant architecture
- Confirm no RAG, embeddings, vector search, or pgvector
- Confirm deployment and security rules

Completion date: 2026-07-25

Completion notes: Converted all twelve source documents from `.docx` (archived unchanged in `archive/source-docs-docx/`) into canonical UTF-8 Markdown at their required repository paths. Repaired the phase-numbering contradiction between the former 16-phase `PROJECT_PLAN.md` sequence and this file's 20-phase sequence — this file (`ROADMAP.md`, Phase 0–19) is now the single canonical sequence, and `PROJECT_PLAN.md` §15 was restructured to match it exactly with no scope loss. Corrected the dummy active-staff total from 58 to 65 (the category breakdown always summed to 65). Closed the open money-representation decision: integer minor units in `BIGINT` columns, `_minor` suffix, no floating point, decided everywhere. Established one canonical dot-separated permission/capability naming convention and replaced inconsistent examples (`orders.update_status`, generic `orders.refund`, vague `leads.manage`) across documents. Renamed `packages/sdk` to `packages/api-client` everywhere. Locked previously-deferred tooling decisions: pnpm (via Corepack), Python 3.12 via `uv`, psycopg 3 as the Postgres driver, Ruff and mypy for backend quality, ARQ (Redis-backed) as the initial background-job library, openpyxl for XLSX, Playwright/Chromium for HTML-to-PDF rendering, k6 for load testing. Confirmed single-business/non-multi-tenant architecture, and confirmed RAG/embeddings/pgvector/vector-search, n8n, and Temporal remain excluded everywhere they are mentioned (only inside explicit prohibition lists). Docker, communication providers (WhatsApp/email/SMS final accounts), payment provider, production domains, and AI provider credentials remain intentionally deferred — not implemented in this phase.

Deferred items: Docker (explicitly deferred to a later deployment/environment-hardening roadmap item, not missing), final WhatsApp/email/SMS provider accounts, payment provider selection, production domain names, OpenAI/Groq credentials.

## Phase 1 — Repository and Development Foundation

Status: COMPLETED

Scope:

- Create monorepo structure
- Configure dashboard, API, worker, packages, tests, and docs
- Add local environment templates
- Add linting, formatting, type checking, and test foundations
- Docker is intentionally deferred to a later phase — do not treat its absence as a defect

Completion date: 2026-07-25

Completion notes: Scaffolded the pnpm workspace (`apps/dashboard`, `apps/api`, `apps/worker`, `packages/{ui,contracts,api-client,config}`) and the shared uv Python workspace for `apps/api`/`apps/worker`. Dashboard: Next.js 16 App Router, TypeScript strict, Tailwind CSS v4, shadcn/ui + Radix foundation, Lucide, TanStack Query provider, React Hook Form + Zod wiring, permission-aware nav placeholders for all twelve approved sections, global error/loading boundaries, non-sensitive `/health` page. API: FastAPI app factory, Pydantic settings validated at startup, structlog logging, request-ID correlation middleware, environment-scoped CORS, stable error-response shapes, pagination contracts, `/health/live` and `/health/ready` (verified live over HTTP), Sentry wiring (inactive without a DSN). Worker: ARQ entry point with cron scheduler foundation and one non-business heartbeat job proving the wiring. Added GitHub Actions CI (secret scan, dashboard lint/typecheck/test/build, backend ruff/mypy/pytest/startup-validation), root and per-app `.env.example` files, and the repository README. All verification commands were actually run and passed: `ruff check`, `ruff format --check`, `mypy` (both packages, strict), `pytest` (both packages), ESLint, `tsc --noEmit`, Vitest, Playwright e2e (against a real dev server), and `next build`. No database models exist yet — that is Phase 2. Repository initialized, connected to `github.com/rachitsiparia-oss/CRM-SYSTEM` as `origin`, and pushed.

Deferred items: Docker (still deferred, see Phase 0 note), Supabase project linking (exists — project `CRM-SYSTEM` in `ap-south-1` — but not linked to this repo until Phase 2 needs it), Railway/Vercel service creation (accounts authenticated; no services created yet — that is Phase 17/18), all communication/payment/AI provider credentials.

## Phase 2 — Database Foundation and Migrations

Status: COMPLETED

Scope:

- Configure Supabase PostgreSQL
- Implement SQLAlchemy models
- Implement Alembic migrations
- Add constraints, indexes, history, audit, outbox, and job foundations
- Add canonical development seed data (including the corrected 65-person dummy staff set)

Completion date: 2026-07-25

Completion notes: Configured the dedicated Supabase PostgreSQL project (`CRM-SYSTEM`, `ap-south-1`) via the session-mode connection pooler — the direct `db.<ref>.supabase.co` host is IPv6-only and times out on networks without IPv6 egress, now documented in `DEPLOYMENT_AND_ENV.md` §7.1. Built `app/db/base.py` (declarative Base, stable constraint naming convention, UUID-primary-key and timestamp mixins) and `app/db/session.py` (async engine/session management, FastAPI dependency, connectivity check). Implemented the three foundation tables from `DATABASE_AND_API.md` §16.5-16.7 — `audit_events`, `outbox_events`, `job_records` — with check constraints on status enums and unique idempotency keys. Wired up Alembic under `app/db/migrations`; generated, applied, and round-trip tested (upgrade → downgrade → upgrade against the live database) the initial migration. Added an idempotent seed-data runner foundation (`app/db/seed.py`) with no seed data yet, since no business tables exist until Phase 3+. `/health/ready` now performs a real database connectivity check. Database-backed tests run in a SAVEPOINT that is always rolled back against the live database, and skip (not fail) when `DATABASE_URL` is unset, so CI stays green without a database secret configured there.

Two latent bugs were found and fixed while wiring this up, both applicable beyond just the database: (1) `.env` resolution in both `apps/api` and `apps/worker` was relative to the process's working directory rather than the package's own location, silently loading the wrong (or no) `.env` depending on where the process was launched from; (2) Sentry initialization crashed startup on a `replace_me...` placeholder DSN (the normal pre-Sentry state) instead of treating it as unconfigured. Also fixed: psycopg 3's async mode requires a selector-based event loop, incompatible with Windows' default `ProactorEventLoop` — `apps/api/run.py` now sets the correct policy before starting uvicorn (documented in the README as the required way to run the API locally on Windows).

Verified: `ruff check`, `ruff format --check`, `mypy --strict`, and the full Pytest suite (10/10 in `apps/api`, including all 6 database constraint tests against the live Supabase database, plus 1/1 in `apps/worker`) all pass. Migration applies cleanly from empty and is fully reversible.

Deferred items: no business tables yet (staff/roles land in Phase 3, menu/inventory in Phase 6/8, customers/leads in Phase 5) — seed data stays empty until then. CI does not yet run the database-backed tests (no `DATABASE_URL` secret configured in GitHub Actions); they skip gracefully rather than fail.

## Phase 3 — Authentication, Users, Roles, and Permissions

Status: COMPLETED

Scope:

- Configure Supabase Auth
- Implement login, logout, session refresh, recovery, and account states
- Implement the single canonical capability registry (dot-separated permission codes)
- Enforce backend authorization
- Add staff accounts and role views

Completion date: 2026-07-25

Completion notes: Built the full Phase 3 database layer — `departments`, `roles`, `permissions`, `role_permissions`, `staff_roles`, `staff_users`, and `staff_invitations` (the last not explicitly shaped in `DATABASE_AND_API.md`; added and documented in §4.6) — with `AuditedMixin`/`SoftDeleteMixin` added to `db/base.py` for the `created_by`/`updated_by`/`version`/`deleted_at` common columns `DATABASE_AND_API.md` §3.1 describes but Phase 2 had no table needing yet. Two migrations applied and round-trip verified (upgrade → downgrade → upgrade) against the live Supabase database, including enabling the `citext` extension for case-insensitive unique email matching.

Implemented `app/permissions/registry.py` as the single canonical capability registry in code (53 permission codes — the union of the representative lists in `DATABASE_AND_API.md` §4.4 and `SECURITY_PERFORMANCE_AND_QUALITY.md` §4.1, both of which state they draw from one underlying source), plus `app/permissions/role_matrix.py` mapping all 15 system roles to their default grants (a Phase 3 implementation decision — neither document specifies the matrix itself). Both are self-validating at import time (duplicate-code and unknown-code checks raise immediately). Seeded idempotently via `app/db/seed.py`: 10 departments, 15 roles, 53 permissions, 233 role-permission grants, verified against the live database.

Backend: Supabase JWT verification (`app/auth/tokens.py`, PyJWT/HS256 against `AUTH_JWT_SIGNING_SECRET` — added as a new, narrowly-scoped dependency, documented in `TOOLS.md` §5.2), `get_current_staff_user` dependency with account-status enforcement and on-first-login provisioning from a pending `staff_invitations` row, an effective-permission calculation and cache (`app/permissions/service.py`, in-process with a documented multi-instance caveat deferred to Phase 16/17 alongside the same-shaped rate-limit hook in `app/core/rate_limit.py`), and `require_permission()` as the one authorization dependency every protected route uses. 17 endpoints across `app/auth/router.py`, `app/staff/router.py`, and `app/roles/router.py`: current-user/login/logout/session/password-reset/profile-update, staff-user list/detail/update/activate/deactivate/role-assign/role-remove, staff-invitations, roles/permissions/departments listing. Privilege-escalation prevention (`SECURITY_PERFORMANCE_AND_QUALITY.md` §4.4) is enforced as a flat rule in `app/staff/service.py`: nobody, including the owner, may change their own role or account status through these endpoints. All security-sensitive actions reuse the Phase 2 `audit_events` table via `app/audit/service.py` — no second audit mechanism.

Frontend: `@supabase/ssr` browser/server clients, `src/proxy.ts` (this Next.js version renamed `middleware.ts` to `proxy.ts` — confirmed from the bundled docs per `apps/dashboard/AGENTS.md`'s warning) refreshing the session and redirecting unauthenticated requests to `/login`. Login, reset-password (request + set-new-password, via `/auth/callback` exchanging Supabase's PKCE code), unauthorized, forbidden, and session-expired pages. Existing dashboard pages moved into an `(app)` route group with its own auth-shell layout (nav + user menu), separate from the now-minimal root layout the public auth pages render under. `/staff` replaced its Phase 1 placeholder with a real, API-backed directory (TanStack Table, server-side search/filter/pagination), staff detail page with role assign/remove and activate/deactivate, and `/staff/roles` as a permission viewer. Shared request/response types added to `packages/contracts` rather than duplicated in the dashboard. `packages/contracts`' existing `PaginatedResponse` gained the `meta` field the backend's envelope always includes; `pyproject.toml`'s ruff config gained `flake8-bugbear.extend-immutable-calls` for `Depends(...)`/`require_permission(...)`, which is FastAPI's documented dependency-injection pattern, not the mutable-default antipattern B008 targets.

Two documentation bugs found and fixed while implementing this: (1) `DATABASE_AND_API.md` §4.1 listed 5 `account_status` values while `SECURITY_PERFORMANCE_AND_QUALITY.md` §3.6 already listed 6 (missing `archived`) — reconciled to the 6-value list both documents now share; (2) `README.md`'s "Production status" section still said Phase 1 after Phase 2 shipped.

Verified: `ruff check`, `ruff format --check`, `mypy --strict` (61 source files across `app/` and `tests/`), and the full `apps/api` Pytest suite (43/43, including 15 new authorization tests that mint real HS256 tokens and exercise the actual verification and permission-check code paths against the live database — not mocked) all pass; `apps/worker` unaffected and still green. Frontend: ESLint, `tsc --noEmit`, Vitest (3/3, after fixing a pre-existing gap — `@testing-library/react` cleanup was never registered between tests since `vitest.config.ts` doesn't set `test.globals`, which was silently leaking DOM state across every future component test, not just this phase's), `next build`, and Playwright e2e (3/3, against a real dev server: unauthenticated redirect to `/login`, login form rendering, and the pre-existing `/health` check) all pass. Manually verified the redirect in a live browser session as well.

Deferred items, each a deliberate scope boundary rather than an omission: (1) the 65-person dummy staff roster is not seeded, since every `staff_users` row requires a real `auth_user_id` and no such Supabase Auth identities exist yet — `app/db/bootstrap_owner.py` is the documented one-time CLI to link the first real account to the `owner` role once created in Supabase; (2) multi-device session listing/revocation is not implemented (Supabase Auth has no stable public API for it) — logout is a single global sign-out; (3) `role_permissions` is system-seeded only in this phase, with no API to edit a role's grants beyond assigning/removing whole roles from a staff member; (4) rate limiting and the permission cache are in-process (correct for the current single-instance deployment), with Redis-backed multi-instance correctness deferred to Phase 16/17 per `ARCHITECTURE_AND_TECH_STACK.md`'s own phase assignment for Redis provisioning on `apps/api`. The Railway API service still shows as `@rkpr/dashboard` in the Railway dashboard — the CLI has no rename command; renaming it is a one-field change in Railway's own Settings tab, left for the user to do directly.

## Phase 4 — Dashboard Shell and Shared UI System

Status: COMPLETED

Scope:

- Build authenticated dashboard shell
- Build navigation for the approved CRM sections
- Add shared tables, filters, forms, dialogs, charts, loading, empty, and error states
- Add permission-aware UI behavior

Completion date: 2026-07-25

Completion notes: Established the design-token foundation shadcn/ui components resolve against (`globals.css` — `--background`/`--card`/`--primary`/`--destructive`/`--success`/`--warning`/`--sidebar-*`/`--chart-1..5`, light and dark via the existing `prefers-color-scheme` strategy, no new class-based toggle introduced since none was requested) and installed 31 shadcn/ui primitives (button/input/label were already hand-written from Phase 1 and were preserved, not overwritten).

Rebuilt the authenticated shell: `DashboardShell` (sidebar + header + scrollable content, `TooltipProvider` once for the whole shell) now wraps the `(app)` route group; the root layout is minimal so the public auth pages render without CRM chrome. `Sidebar` replaces Phase 3's `dashboard-nav.tsx` in place (collapsible with a persisted `localStorage` preference, icons, nested navigation demonstrated on Staff & HR's two real sub-routes, active-route highlighting via `aria-current`, keyboard-reachable, permission-aware) with a `MobileNav` off-canvas counterpart for small screens — both read one shared `nav-config.ts` source so they can't drift apart. `Header` composes `Breadcrumbs` (auto-derived from the URL against that same nav config), `GlobalSearch` (⌘K command-palette foundation, UI-only per PROJECT_PLAN.md Phase 4 scope — jumps between the twelve sections, no backend search), `NotificationsMenu` (mock/empty data only, per scope), and an upgraded `UserMenu` (avatar, dropdown, Profile/Settings/Sign out).

Added a real `/profile` page using Phase 3's existing (previously unused from the UI side) `PATCH /api/v1/auth/me` self-service endpoint — the one exception to "shell pages only," justified because the Phase 4 spec explicitly required a working "Profile" menu item and the backend support for it already existed from Phase 3.

Design system: `PageHeader`, `SectionCard`, `StatCard`, `MetricCard`, `StatusBadge` (icon-paired per tone, never color-only), `EmptyState`, `ErrorState` (404/403/500/offline/generic — now used by `not-found.tsx`, `error.tsx`, and `/forbidden`, replacing three previously-inconsistent hand-rolled versions). Forms: `PhoneInput`/`EmailInput`/`PasswordInput`/`SearchInput`/`NumberInput`/`CurrencyInput`/`TimeInput`, `DatePicker`, `MultiSelect`, `FileUpload`/`ImageUpload` (presentation only — no Storage transport wiring, that belongs to whichever business form uses them), and a `FormField` wrapper for label/error/description/required. `DataTable`: the one generic enterprise table (server-driven sorting and pagination only — it never assumes it holds a full dataset to sort or paginate client-side), with column resize/visibility, row/bulk selection, sticky header, loading/empty states. `FilterBar`, `Modal` (sm/md/lg/fullscreen), `ConfirmDialog` (AlertDialog-based — cannot be dismissed by an outside click, with an optional typed-confirmation safeguard for the highest-risk deletes), `Drawer` (left/right), `ActionMenu`. Charts: `LineChart`/`BarChart`/`AreaChart`/`PieChart` (with a `donut` variant) wrapping Apache ECharts, colored from the design tokens via a `useChartColors` hook (resolves `--chart-1..5` to concrete values since ECharts can't read CSS custom properties itself, re-reads on an OS color-scheme flip). Skeletons: page/card/table/form/chart.

All twelve placeholder pages (`ModulePlaceholder`, plus the Dashboard home page) now render through `PageHeader` + `EmptyState` instead of ad hoc markup — deliberately still just "title, breadcrumb, placeholder, nothing more," per this phase's explicit instruction. This is a conscious, explicit deviation from `PROJECT_PLAN.md`'s Phase 4 section, which describes dummy KPI widgets (`Revenue today: ₹84,620`, etc.) on the dashboard home page — the most recent explicit user instruction for this phase repeatedly said "nothing business-specific" and listed Dashboard under "placeholder pages only," which CLAUDE.md section 1.1 makes the controlling instruction when it conflicts with a document. The KPI/metric-card and chart *components* PROJECT_PLAN.md and this phase both wanted now exist either way; only wiring them into the actual dashboard page with dummy data was skipped, deferred to whichever phase populates the dashboard with real aggregates.

Two real bugs found and fixed while building this, both from React Compiler's `react-hooks/set-state-in-effect` rule (new since Phase 1's ESLint config was last exercised against non-trivial client components): `ImageUpload` stored a derived object-URL in state and set it from inside an effect (restructured to compute it via `useMemo` instead, with the effect doing only cleanup); `useChartColors` re-set state unconditionally on every mount even though its lazy `useState` initializer already produces the correct value on the client's first render (removed the redundant call, keeping the effect only for the *future* OS color-scheme-change subscription). `Sidebar`'s mount-only localStorage read triggered the same rule but is the correct, standard pattern for avoiding a hydration mismatch (reading `localStorage` during SSR isn't possible) — scoped `eslint-disable-next-line` with a comment explaining why, rather than restructured away.

Verified: `ruff check`, `ruff format --check`, `mypy --strict` (63 files), and the full `apps/api` Pytest suite (47/47) all still pass, confirming the "do not touch auth/authorization/database/API contracts" constraint held — nothing in `apps/api` changed this phase. Frontend: ESLint (0 errors after the fixes above; the two remaining warnings are TanStack Table's own known, benign React Compiler incompatibility note, pre-existing since Phase 3), `tsc --noEmit`, Vitest (4/4 — `sidebar.test.tsx` replaces Phase 3's `dashboard-nav.test.tsx`, covering the same permission-visibility behavior against the new component), `next build`, and Playwright e2e (3/3) all pass. Manually verified in a live browser: `/login`, `/health`, `/forbidden` (new `ErrorState` rendering), and that `/staff` still redirects unauthenticated visitors to `/login` — no regression in Phase 3's auth flow.

Deferred, deliberately: dummy dashboard KPI widgets (see the PROJECT_PLAN.md deviation note above), any business-specific table/form/filter usage (every module in Phase 5 onward composes the primitives built here, none were pre-wired to real data), Redis-backed anything (still Phase 16/17, unrelated to this phase), and real cross-module search/notifications backends (both stay UI-only until their owning phases).

## Phase 5 — Customer and Lead CRM

Status: NOT STARTED

Scope:

- Customer profiles and timeline
- Tags, segments, preferences, dietary data, allergies, notes, and communication history
- Lead pipeline, qualification, assignment, follow-ups, conversion, and win/loss tracking
- Duplicate detection and customer merge controls

Completion date:

Completion notes:

## Phase 6 — Menu and Product Management

Status: NOT STARTED

Scope:

- Categories, menu items, variants, add-ons, combos, availability, images, allergens, and nutrition
- Recipes, costing, margins, pricing, and visibility rules
- Canonical RKPR menu and prices

Completion date:

Completion notes:

## Phase 7 — Orders and Restaurant Operations

Status: NOT STARTED

Scope:

- Dine-in, takeaway, delivery, online, QR, and table ordering foundations
- Order state machine
- Kitchen and preparation workflow
- Taxes, discounts, payments, refunds, cancellations, and audit history
- Realtime operational updates

Completion date:

Completion notes:

## Phase 8 — Inventory and Supplier Management

Status: NOT STARTED

Scope:

- Ingredients, units, batches, expiry, FIFO, movements, waste, and counts
- Recipe-based deductions
- Suppliers, purchase orders, receiving, valuation, alerts, and vendor performance

Completion date:

Completion notes:

## Phase 9 — Reservations and Calendar

Status: NOT STARTED

Scope:

- Reservation calendar
- Availability and table assignment
- Waitlist, confirmations, reminders, cancellations, no-shows, and special requests
- Group and event reservations

Completion date:

Completion notes:

## Phase 10 — Communication Hub and Operational Tasks

Status: NOT STARTED

Scope:

- Unified customer communication history
- Email and WhatsApp integration boundaries
- Human handoff and assignment
- Operational tasks, reminders, escalations, notifications, and SLAs

Completion date:

Completion notes:

## Phase 11 — Knowledge Base and Staff Operations

Status: NOT STARTED

Scope:

- Lightweight knowledge base
- Staff directory
- Shifts, attendance references, leave, performance notes, and HR permissions
- No RAG or vector search

Completion date:

Completion notes:

## Phase 12 — Loyalty, Offers, and Campaigns

Status: NOT STARTED

Scope:

- Loyalty accounts and immutable point ledger
- Rewards, offers, coupons, eligibility, and redemption
- Segments, campaigns, consent, suppression, approval, scheduling, delivery, and attribution

Completion date:

Completion notes:

## Phase 13 — Feedback, Complaints, and Service Recovery

Status: NOT STARTED

Scope:

- Feedback requests and reviews
- Complaint lifecycle
- Severity, assignment, escalation, SLA, compensation approval, resolution, and follow-up
- Customer recovery history

Completion date:

Completion notes:

## Phase 14 — Reports, Analytics, and Controlled AI

Status: NOT STARTED

Scope:

- Operational and growth dashboards
- Revenue, customer, order, inventory, reservation, campaign, loyalty, feedback, and staff reporting
- Exports and scheduled reports
- Controlled advisory AI for summaries, drafting, metric explanation, and anomaly review
- No autonomous sensitive mutations

Completion date:

Completion notes:

## Phase 15 — Integrations, Automations, Jobs, and Realtime

Status: NOT STARTED

Scope:

- Integration management
- Webhooks
- Transactional outbox
- Worker queues and scheduler (ARQ)
- Retries and dead-letter recovery
- Controlled backend automations
- Authenticated realtime channels
- Integration health and reconciliation

Completion date:

Completion notes:

## Phase 16 — Security, Performance, and Quality Hardening

Status: NOT STARTED

Scope:

- Security review
- Permission and abuse testing
- File and webhook security
- Performance optimization and load testing (k6)
- Accessibility and UX quality
- Observability, alerts, backups, restore tests, and incident readiness

Completion date:

Completion notes:

## Phase 17 — Staging Deployment and Acceptance Testing

Status: NOT STARTED

Scope:

- Deploy dashboard, API, worker, Supabase, Redis, and Sentry staging configuration
- Run migrations and canonical staging seeds
- Validate critical workflows
- Run smoke, E2E, security, and performance tests
- Resolve release blockers

Completion date:

Completion notes:

## Phase 18 — Production Deployment and Launch

Status: NOT STARTED

Scope:

- Configure approved production domains and credentials
- Run production migrations
- Deploy API, worker, and dashboard in controlled order
- Validate webhooks, integrations, queues, realtime, monitoring, backups, and alerts
- Execute production smoke tests
- Confirm rollback readiness

Completion date:

Completion notes:

## Phase 19 — Post-Launch Stabilization

Status: NOT STARTED

Scope:

- Monitor errors, latency, queue backlog, integration health, and user feedback
- Fix launch defects
- Tune performance and alerts
- Validate backup and recovery operations
- Close launch-related incidents and document lessons

Completion date:

Completion notes:

## Phase Update Rule

After completing a phase, Claude must:

1. change `Status` to `COMPLETED`
2. add the completion date
3. add a concise factual completion note
4. mention any deliberately deferred items
5. update the next phase to `IN PROGRESS` only when work on it has actually begun
6. never mark a phase complete when required tests or acceptance criteria remain unfinished
