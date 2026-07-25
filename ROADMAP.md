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

Status: NOT STARTED

Scope:

- Configure Supabase PostgreSQL
- Implement SQLAlchemy models
- Implement Alembic migrations
- Add constraints, indexes, history, audit, outbox, and job foundations
- Add canonical development seed data (including the corrected 65-person dummy staff set)

Completion date:

Completion notes:

## Phase 3 — Authentication, Users, Roles, and Permissions

Status: NOT STARTED

Scope:

- Configure Supabase Auth
- Implement login, logout, session refresh, recovery, and account states
- Implement the single canonical capability registry (dot-separated permission codes)
- Enforce backend authorization
- Add staff accounts and role views

Completion date:

Completion notes:

## Phase 4 — Dashboard Shell and Shared UI System

Status: NOT STARTED

Scope:

- Build authenticated dashboard shell
- Build navigation for the approved CRM sections
- Add shared tables, filters, forms, dialogs, charts, loading, empty, and error states
- Add permission-aware UI behavior

Completion date:

Completion notes:

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
