# RKPR RESTAURANT CRM — TOOLS

## 1. DOCUMENT PURPOSE

This document is the authoritative registry of approved technologies, platforms, libraries, services, development tools, testing tools, deployment tools, monitoring tools, and integration categories for the RKPR Restaurant CRM.

Claude Code must use this file to determine which tools are approved, what responsibility each tool owns, which tools are optional, which tools are deferred, and which tools must not be introduced without explicit approval.

This document must remain consistent with `PROJECT_PLAN.md`, `ARCHITECTURE_AND_TECH_STACK.md`, `DATABASE_AND_API.md`, `CORE_CRM_MODULES.md`, `OPERATIONS_MODULES.md`, `GROWTH_AND_INTELLIGENCE.md`, `INTEGRATIONS_AUTOMATIONS_REALTIME.md`, `SECURITY_PERFORMANCE_AND_QUALITY.md`, `DEPLOYMENT_AND_ENV.md`, and `ROADMAP.md`.

Important rule: a tool being technically possible does not make it approved. Any major new platform, provider, infrastructure layer, database, AI framework, workflow engine, search engine, or deployment dependency requires explicit approval and an update to this document before implementation.

This revision closes every previously-open tooling decision. Where earlier drafts of this document said "selected during implementation," "acceptable when," or "must be recorded here," those decisions are now final and locked, as recorded below.

## 2. PRODUCT ARCHITECTURE BOUNDARY

The RKPR Restaurant CRM is a private, single-business system for RKPR Fast-Food Restaurant.

Approved architecture:

- one codebase
- one RKPR deployment
- one primary PostgreSQL database
- one dashboard frontend
- one FastAPI backend
- one separate worker and scheduler service
- one dedicated Supabase project
- one Upstash Redis instance or isolated environment-specific namespaces
- no shared multi-tenant SaaS architecture
- no tenant tables
- no tenant routing
- no tenant-specific RLS model
- no microservice sprawl

The preferred backend structure is a modular monolith. Modules may have strong boundaries, but they remain inside the same backend application unless a future architecture review approves separation.

## 3. APPROVED CORE STACK

### 3.1 Frontend application

#### Next.js

Status: REQUIRED

Version policy: use the latest stable release compatible with the selected React version at the time of Phase 1 implementation. Query the package registry during installation rather than hardcoding a version from memory. Lock the resolved version in `pnpm-lock.yaml`. Major upgrades require review. Never use alpha, beta, canary, or release-candidate builds.

Responsibilities:

- dashboard application
- App Router routing
- server and client component boundaries
- authenticated page shell
- route-level code splitting
- API client integration
- environment-safe frontend builds
- static and dynamic rendering where appropriate

Must not own:

- database access
- authoritative business calculations
- permission enforcement
- payment confirmation
- inventory truth
- order-state truth

#### React

Status: REQUIRED — the stable version required by the selected Next.js release.

Responsibilities:

- interactive UI
- component composition
- stateful forms and workflows
- reusable dashboard components

#### TypeScript

Status: REQUIRED

Configuration: strict mode, latest stable version compatible with the framework.

Rules:

- avoid unjustified `any`
- use typed API contracts
- model important UI states explicitly
- use exhaustive handling for critical status enums
- do not duplicate backend domain logic in the browser

#### Tailwind CSS

Status: REQUIRED — latest stable supported version.

Responsibilities:

- layout
- spacing
- responsive behavior
- visual tokens
- utility-based styling

Rules:

- use a consistent design-token layer
- avoid uncontrolled one-off values
- preserve accessibility and contrast
- avoid giant unmaintainable class strings by extracting reusable components or variants

#### shadcn/ui and Radix UI

Status: REQUIRED DESIGN-SYSTEM FOUNDATION

Responsibilities:

- accessible primitives
- dialogs
- dropdowns
- popovers
- tabs
- tooltips
- menus
- form controls
- command palettes where useful

Rules:

- components remain locally owned and editable
- accessibility behavior must not be removed
- styling must match the RKPR design system
- do not install overlapping component libraries without approval

#### Lucide Icons

Status: REQUIRED — the only default icon pack.

Responsibilities:

- consistent interface icons

Rules:

- use icons with labels when meaning is not obvious
- do not mix several unrelated icon packs

### 3.2 Frontend data and form tools

#### TanStack Query

Status: REQUIRED

Responsibilities:

- server-state fetching
- caching
- mutation coordination
- stale-data control
- background refetching
- invalidation
- error and retry behavior

Rules:

- PostgreSQL through the backend remains authoritative
- avoid treating cache as durable state
- use optimistic updates only for safe reversible actions
- never show financial or operational success before backend confirmation

#### TanStack Table

Status: REQUIRED

Responsibilities:

- data-heavy tables
- sorting
- filtering
- pagination
- column visibility
- selection
- controlled bulk actions

#### TanStack Virtual

Status: APPROVED WHEN NEEDED

Responsibilities:

- virtualization for long tables or lists

Use only when data volume justifies it (measured, not assumed).

#### React Hook Form

Status: REQUIRED

Responsibilities:

- form state
- field registration
- submission lifecycle
- performant complex forms

#### Zod

Status: REQUIRED ON FRONTEND

Responsibilities:

- frontend form schemas
- client-side validation
- safe parsing of selected external values

Backend Pydantic validation remains authoritative.

#### Zustand

Status: APPROVED, NARROW USE ONLY

Responsibilities:

- small amounts of cross-route client state
- UI preferences
- temporary workflow state where URL, component state, or TanStack Query is not appropriate

Must not become:

- a duplicate database
- a replacement for TanStack Query
- a store for complete customer, order, or inventory datasets
- a permission authority

### 3.3 Charts and visualization

#### Apache ECharts

Status: REQUIRED FOR ANALYTICS

Responsibilities:

- business charts
- operational dashboards
- revenue trends
- customer analysis
- campaign results
- inventory trends
- reservation patterns

Rules:

- charts must remain readable and accessible
- every chart must have data-table or textual context where needed
- avoid decorative charts that do not support decisions
- do not load the full chart library on routes that do not need it

## 4. BACKEND STACK

### 4.1 Python

#### Python 3.12.x

Status: REQUIRED — final, locked runtime version.

**Never use Python 3.14 for this project merely because it is installed globally on the development machine.** Install Python 3.12.x side by side with any other version and configure the project (via `uv`) to use 3.12 exclusively.

Rules:

- type all public functions and important internal boundaries
- use async only where appropriate
- avoid blocking calls inside async request paths
- maintain clear package boundaries

### 4.2 FastAPI

Status: REQUIRED

Responsibilities:

- `/api/v1` HTTP API
- authentication verification
- backend authorization
- input validation
- business workflows
- domain state transitions
- integration adapters
- webhook endpoints
- file authorization
- health endpoints
- OpenAPI generation

FastAPI is the authoritative execution layer for consequential CRM actions.

### 4.3 Pydantic v2 and pydantic-settings

Status: REQUIRED

Responsibilities:

- request schemas
- response schemas
- environment configuration validation (pydantic-settings)
- provider payload parsing
- internal typed contracts where appropriate

Rules:

- reject malformed input early
- avoid leaking internal model fields in public responses
- separate create, update, response, and internal schemas where needed

### 4.4 SQLAlchemy 2.x

Status: REQUIRED

Responsibilities:

- ORM models
- transactions
- repository and query behavior
- relationship mapping
- safe parameter binding

Rules:

- use SQLAlchemy 2.x patterns
- avoid string-built SQL from untrusted input
- inspect generated query behavior
- prevent N+1 queries
- keep transaction boundaries explicit

### 4.5 Alembic

Status: REQUIRED

Responsibilities:

- schema migrations
- migration history
- controlled upgrades and downgrades where safe

Rules:

- migrations are version-controlled
- production migrations run as an explicit release step
- no unsafe migration automatically runs at every API startup
- destructive migrations require review and recovery planning

### 4.6 PostgreSQL driver — psycopg 3 (final, locked)

Status: REQUIRED — **psycopg 3**, with binary and async support where required, is the final PostgreSQL driver for this project. `asyncpg` is not approved; do not introduce it.

A separate synchronous connection using psycopg 3 may be used only where Alembic, scripts, or operational tooling requires it.

### 4.7 HTTPX

Status: REQUIRED

Responsibilities:

- outbound HTTP calls
- provider integrations
- webhook follow-up calls
- AI-provider requests where the official SDK is not used

Rules:

- explicit connect and total timeouts
- bounded retries only through approved retry behavior
- HTTPS
- safe logging
- provider-specific error mapping

### 4.8 structlog

Status: REQUIRED

Responsibilities:

- structured application logs
- request and correlation IDs
- service and environment context
- safe event logging

Rules:

- redact secrets
- avoid full sensitive payloads
- distinguish logs from audit records

### 4.9 Ruff — final linter and formatter

Status: REQUIRED — **Ruff** is the final, locked choice for Python linting and formatting.

### 4.10 mypy — final static type checker

Status: REQUIRED — **mypy** is the final, locked choice for Python static type checking.

### 4.11 Testing

Status: REQUIRED — Pytest, pytest-asyncio, and HTTPX test clients where appropriate.

## 5. DATABASE, AUTHENTICATION, STORAGE, AND REALTIME

### 5.1 Supabase PostgreSQL

Status: REQUIRED

Responsibilities:

- authoritative CRM data
- customer records
- leads
- orders
- menu
- inventory
- reservations
- communication metadata
- staff records
- loyalty ledger
- campaigns
- feedback and complaints
- reports
- audit history
- outbox
- jobs
- integration configuration metadata

Rules:

- one dedicated production project
- separate staging or isolated staging resources
- UTC timestamps
- Asia/Kolkata display timezone
- money as integer minor units in `BIGINT` columns — final, locked (see `DATABASE_AND_API.md` §3.3); never float, never `NUMERIC(14,2)` as an alternative
- UUID primary identifiers plus human-readable references where needed

### 5.2 Supabase Auth

Status: REQUIRED

Responsibilities:

- staff identity
- login
- logout
- session refresh
- recovery
- verified authentication state

Must not replace:

- backend capability authorization
- staff profile and role records in PostgreSQL
- business-state validation

Backend token verification (added during Phase 3 implementation): **PyJWT**, to verify Supabase-issued HS256 access tokens against `AUTH_JWT_SIGNING_SECRET` locally, without a network round trip per request. This is a small, narrowly-scoped verification library, not a competing identity provider — it does not replace Supabase Auth.

### 5.3 Supabase Storage

Status: REQUIRED

Responsibilities:

- private file bytes
- menu images
- customer and complaint attachments
- staff documents where approved
- knowledge-base attachments
- generated exports

Rules:

- private buckets by default
- short-lived signed URLs
- backend authorization before file access
- metadata stored in PostgreSQL
- file validation and quarantine where required
- no public bucket added for convenience

### 5.4 Supabase Realtime

Status: APPROVED, CONTROLLED USE ONLY

Responsibilities:

- scoped authenticated operational updates
- dashboard refresh signals
- order and reservation update events
- assignment and notification updates

Rules:

- realtime is not the source of truth
- no broad table exposure
- no complete sensitive record broadcast
- clients refetch authoritative data after important events
- reconnect and deduplication behavior is required

## 6. REDIS, CACHE, RATE LIMITS, AND COORDINATION

### Upstash Redis

Status: REQUIRED

Responsibilities:

- cache
- rate limits
- idempotency windows
- locks
- short-lived counters
- ARQ queue transport
- scheduler coordination
- temporary provider state

Rules:

- never the source of truth
- every key family has a prefix and version
- TTLs are explicit
- environment separation is required
- sensitive data is minimized
- failure must degrade safely
- critical order, payment, inventory, and loyalty history remains in PostgreSQL

## 7. BACKGROUND JOBS, WORKERS, AND AUTOMATIONS

### 7.1 Separate worker service

Status: REQUIRED

Platform: Railway.

Responsibilities:

- background jobs
- outbox dispatch
- communications
- reports
- exports
- file processing
- campaign batches
- feedback requests
- loyalty tasks
- reconciliation
- scheduled maintenance
- optional background AI work (Phase 14 only)

### 7.2 Scheduler

Status: REQUIRED — implemented via ARQ's built-in cron support, running inside the `apps/worker` service. There is no separate scheduler platform.

Responsibilities:

- recurring jobs
- due reminders
- report schedules
- reservation reminders
- campaign schedules
- inventory checks
- cleanup and retention jobs
- reconciliation

Rules:

- stable schedule IDs
- duplicate prevention
- distributed coordination where needed
- auditable schedule state

### 7.3 Queue implementation — ARQ (final, locked)

Status: REQUIRED — **ARQ is the approved initial Python background-job and scheduling library for this project.**

Reasons and boundaries:

- compatible with async Python
- Redis-backed (Upstash)
- smaller operational surface than Celery for this single-business system
- supports retries, timeouts, scheduled jobs, and worker functions
- aligns with the separate Railway worker process

PostgreSQL still contains the durable business job records (`job_records`), outbox records, idempotency keys, audit history, and final status where required. ARQ and Redis coordinate execution; they are not the sole durable source of business truth. Dead-letter handling and stale-job recovery are implemented at the application layer using documented database state and operational tooling.

Before implementing ARQ against Upstash, verify technical compatibility with the actual Redis connection mode and feature requirements during Phase 1. **If a proven incompatibility is discovered, implementation must stop and report the exact issue before silently choosing a different queue platform.** Do not swap to Celery or another queue without updating this document and obtaining explicit approval.

### 7.4 n8n

Status: NOT APPROVED / NOT REQUIRED

Reason:

- automations are part of the FastAPI and ARQ worker architecture
- business workflows need typed domain rules, transactions, permissions, auditability, and testing
- a separate visual workflow dependency would create a second execution model

Claude must not introduce n8n unless the user explicitly changes this decision.

### 7.5 Temporal

Status: NOT APPROVED FOR CURRENT BUILD

Temporal may be reconsidered only if future workflows prove to require long-running durable orchestration that cannot be handled safely by the approved ARQ job model.

Do not introduce it pre-emptively.

### 7.6 Celery

Status: NOT APPROVED — superseded by ARQ (§7.3). Do not introduce Celery into this project.

## 8. AI TOOLS

### 8.1 OpenAI

Status: APPROVED PRIMARY AI PROVIDER — configured and credentialed only in Phase 14 of `ROADMAP.md`, never during the foundation phase.

Permitted responsibilities:

- internal summaries
- draft replies
- campaign-copy drafts
- explanation of metrics
- structured anomaly review
- optional classification assistance
- controlled staff-facing recommendations

Prohibited behavior:

- direct refunds
- direct payment actions
- autonomous order cancellation
- autonomous inventory adjustment
- autonomous loyalty adjustment
- direct staff-access changes
- automatic campaign sending without approval
- unsupported factual claims

Rules:

- provider adapter required
- prompts versioned
- private data minimized
- timeouts and budgets applied
- output validated before use
- every sensitive action remains deterministic and human-controlled

### 8.2 Groq

Status: OPTIONAL FALLBACK OR ALTERNATE PROVIDER — same Phase 14 timing as OpenAI.

Responsibilities:

- fallback for selected non-sensitive AI tasks
- lower-latency alternate inference where approved

Rules:

- same adapter interface as OpenAI
- same safety boundaries
- no silent change of output behavior
- no fallback for a task unless its model capability has been tested

### 8.3 AI framework libraries

Status: NOT REQUIRED

Do not add LangChain, LlamaIndex, semantic-kernel-style orchestration, or another AI framework unless a concrete requirement justifies it.

The current AI needs are small enough for direct typed provider adapters.

### 8.4 RAG and vector tools

Status: EXPLICITLY NOT PART OF THIS PROJECT

Do not use:

- embeddings
- pgvector
- vector databases
- semantic retrieval
- RAG pipelines
- document chunking systems

The Knowledge Base uses ordinary structured content and PostgreSQL full-text search only.

## 9. KNOWLEDGE BASE AND SEARCH

### PostgreSQL full-text search

Status: REQUIRED FOR KNOWLEDGE BASE SEARCH

Responsibilities:

- document title search
- body search
- keyword ranking
- filters by folder, status, and type

Rules:

- use PostgreSQL indexes
- no Elasticsearch or vector search for the current scope
- preserve version history and publication status

### Elasticsearch / OpenSearch / Meilisearch / Typesense

Status: NOT APPROVED

May be reviewed only after real search-volume or feature requirements exceed PostgreSQL capabilities.

## 10. COMMUNICATION AND EXTERNAL INTEGRATION PROVIDERS

The CRM supports provider adapters, but final production providers for every channel must be explicitly approved before credentials or final environment-variable names are added.

### 10.1 WhatsApp

Status: INTEGRATION CATEGORY APPROVED; FINAL ACCOUNT CONFIGURATION REQUIRED — WhatsApp Cloud API is the approved API.

Permitted use:

- customer communication
- reservation confirmation and reminders
- order updates where approved
- feedback requests
- campaigns with consent and template compliance

Requirements:

- official provider/API
- verified business account
- approved templates where required
- webhook verification
- opt-in and suppression enforcement
- rate limits
- delivery-status tracking

Do not use unofficial browser automation or personal WhatsApp scraping.

### 10.2 Email

Status: INTEGRATION CATEGORY APPROVED; FINAL PROVIDER APPROVAL REQUIRED

Permitted use:

- transactional emails
- reservations
- reports
- staff notifications
- campaigns with consent

Requirements:

- verified sender domain
- SPF, DKIM, and DMARC where applicable
- bounce and complaint processing
- suppression list
- provider webhook verification

### 10.3 SMS

Status: OPTIONAL / DEFERRED UNTIL REQUIRED

Use only after provider, sender, regulatory, and cost approval.

### 10.4 Payment provider

Status: INTEGRATION CATEGORY APPROVED; FINAL PROVIDER NOT ASSUMED

Responsibilities:

- payment initiation or links
- signed callbacks
- payment-status reconciliation
- refunds only through authorized deterministic workflows

Rules:

- backend verifies provider callbacks
- frontend success pages are not proof of payment
- provider event IDs are deduplicated
- secrets remain server-side
- financial history remains append-only and auditable

### 10.5 Website forms

Status: APPROVED

Responsibilities:

- lead forms
- reservation requests
- customer inquiries
- feedback submissions

Requirements:

- validation
- rate limiting
- abuse protection
- consent capture where needed
- idempotency or duplicate detection

### 10.6 Google integrations

Status: OPTIONAL, NOT REQUIRED FOR CORE LAUNCH

Possible future uses:

- Google Calendar synchronization
- Google Business Profile review links
- Google Drive export destinations

Any implementation requires explicit approval, scoped OAuth, and an update to this file.

## 11. REPORTS, DOCUMENTS, AND EXPORTS

### 11.1 CSV export

Status: REQUIRED

Use for:

- tabular business exports
- customer lists
- order summaries
- inventory reports
- campaign recipient results

Rules:

- permission-controlled
- formula-injection protection
- streaming or background generation for large exports (ARQ)
- audit history

### 11.2 Spreadsheet export — openpyxl (final, locked)

Status: REQUIRED — **openpyxl** is the final, locked library for XLSX generation.

Rules:

- safe generated files
- must not execute macros

### 11.3 PDF generation — Playwright/Chromium (final, locked)

Status: REQUIRED WHEN NEEDED — **Playwright with Chromium** is the final, locked approach for controlled backend HTML-to-PDF rendering.

Use for:

- invoices
- receipts
- management reports
- printable summaries

Rules:

- run asynchronously (ARQ worker) for heavy documents
- sanitize user content
- use controlled templates
- store generated files privately

### 11.4 File parsing

Status: LIMITED AND MODULE-SPECIFIC

Do not install broad document-ingestion frameworks. Use narrow libraries only for explicitly supported imports.

## 12. TESTING TOOLS

### 12.1 Pytest

Status: REQUIRED

Responsibilities:

- backend unit tests
- domain tests
- API tests
- database tests
- worker tests
- integration adapter tests
- security tests

### 12.2 Vitest

Status: REQUIRED

Responsibilities:

- frontend unit tests
- utility tests
- hooks
- state behavior

### 12.3 React Testing Library

Status: REQUIRED

Responsibilities:

- user-focused component behavior
- forms
- loading and error states
- accessibility behavior

### 12.4 Playwright

Status: REQUIRED

Responsibilities:

- critical end-to-end journeys
- authentication
- customers and leads
- orders
- reservations
- inventory
- campaigns
- complaints
- exports
- permission boundaries

(Playwright is also the PDF-rendering engine per §11.3 — the same dependency serves both purposes.)

### 12.5 Load and performance testing — k6 (final, locked)

Status: REQUIRED BEFORE PRODUCTION — **k6** is the final, locked load-testing tool.

Must support, and does support:

- HTTP load testing
- controlled concurrency
- latency percentiles
- scenario scripting
- CI or staging execution

Do not run destructive load tests against production.

### 12.6 Security testing

Status: REQUIRED AS A PRACTICE

Approved categories:

- dependency scanning
- secret scanning
- static analysis
- authorization tests
- webhook replay tests
- file-upload abuse tests
- manual OWASP-style review

Any dynamic scanner must be scoped carefully and must not target production without explicit approval.

## 13. CODE QUALITY TOOLS

### Frontend

Required capabilities:

- ESLint
- Prettier (or the formatter bundled with the chosen ESLint config) for formatting
- strict TypeScript checking
- `pnpm-lock.yaml` dependency lockfile

### Backend

Required capabilities:

- Ruff (linting and formatting — see §4.9)
- mypy (static type checking — see §4.10)
- `uv.lock` dependency lockfile

Do not use several overlapping tools without a clear reason.

## 14. SOURCE CONTROL AND CI/CD

### GitHub

Status: REQUIRED

Responsibilities:

- source control
- pull requests
- review history
- branch protection
- release references
- issue tracking where used

### GitHub Actions

Status: REQUIRED

Responsibilities:

- formatting checks
- linting
- type checks
- unit tests
- integration tests where feasible
- migration validation
- frontend build
- backend startup validation
- dependency scanning
- secret scanning
- controlled deployment workflow where configured

Rules:

- untrusted pull requests do not receive production secrets
- CI failures block release
- production deployments use approved branches or explicit release workflows

## 15. DEPLOYMENT PLATFORMS

### Vercel

Status: REQUIRED FOR DASHBOARD

Responsibilities:

- Next.js dashboard deployment
- preview deployments
- production frontend hosting
- frontend environment variables
- domain and TLS management for the dashboard

Rules:

- preview deployments do not automatically receive production secrets
- only safe public values are exposed to the browser
- API base URL is environment-specific

### Railway

Status: REQUIRED FOR API AND WORKER

Services:

- FastAPI API service
- separate ARQ worker and scheduler service

Responsibilities:

- Python runtime
- service logs
- health checks
- environment variables
- deploy and rollback

Rules:

- API and worker remain separate
- migrations are an explicit release step
- health checks do not reveal secrets
- resource settings are based on observed need

### Docker

Status: **DEFERRED** — not used in this build's local development, CI, or deployment. This is a deliberate decision recorded in `ROADMAP.md` Phase 1 and `DEPLOYMENT_AND_ENV.md` §1, not a missing capability. Docker may be introduced later, during Phase 16 (Security, Performance, and Quality Hardening) or beyond, only with an explicit decision recorded here first.

### Kubernetes

Status: NOT APPROVED

The current deployment does not require Kubernetes.

## 16. OBSERVABILITY AND MONITORING

### Sentry

Status: REQUIRED

Responsibilities:

- frontend errors
- backend exceptions
- worker failures
- release tracking
- performance traces where configured

Rules:

- redact secrets and sensitive content
- environment and release tags required
- include request and correlation IDs where safe

### Platform logs

Status: REQUIRED

Sources:

- Vercel
- Railway
- Supabase
- Upstash
- approved providers

Logs must be structured where controlled and must not become the sole audit system.

### Metrics and alerting

Status: REQUIRED CAPABILITY

Initial metrics use platform-native telemetry plus Sentry and application health data.

Do not add a full observability stack such as Prometheus, Grafana, Datadog, or New Relic without demonstrated need and approval.

## 17. DEVELOPMENT ASSISTANTS

### Claude Code

Status: PRIMARY IMPLEMENTATION ASSISTANT

Responsibilities:

- implement phases from `ROADMAP.md`
- obey authoritative documents
- update `ROADMAP.md` after verified phase completion
- run tests and checks
- preserve consistency
- document deferred items

Rules:

- do not invent business facts or providers
- do not mark a phase complete before acceptance criteria pass
- do not introduce unapproved tools
- do not silently change architecture

### Codex

Status: APPROVED SECONDARY DEVELOPMENT ASSISTANT

Use for:

- focused implementation
- code review
- debugging
- repository tasks

It must follow the same project documents and tool restrictions.

### Antigravity or local IDE

Status: APPROVED DEVELOPMENT ENVIRONMENT

The IDE does not change production architecture or become a runtime dependency.

## 18. PACKAGE AND DEPENDENCY MANAGEMENT

### JavaScript package manager — pnpm (final, locked)

Status: REQUIRED — **pnpm, enabled through Corepack**, is the final, locked JavaScript/TypeScript package manager. Do not maintain conflicting npm or Yarn lockfiles.

### Python dependency manager — uv (final, locked)

Status: REQUIRED — **uv** is the final, locked Python dependency and environment manager. Do not use Poetry, or any other Python dependency manager, in this project.

### Dependency rules

- each dependency must have a clear purpose
- avoid abandoned libraries
- avoid duplicate libraries for the same responsibility
- pin or lock versions (`pnpm-lock.yaml`, `uv.lock`)
- review major upgrades
- scan vulnerabilities
- remove unused packages
- do not install packages merely because generated code referenced them
- use current stable, maintained, production-ready releases; never alpha, beta, canary, release-candidate, or nightly versions unless explicitly approved
- prefer active LTS runtimes (Node.js, Python)
- verify compatibility between related packages before locking
- never hardcode a version number from model memory when the registry or official CLI can provide the current stable release
- record exact installed versions after installation (in the Phase 1 completion report and in lockfiles)

## 19. TOOLS EXPLICITLY NOT APPROVED FOR THE CURRENT BUILD

Do not introduce the following without explicit architecture approval:

- n8n
- Temporal
- Celery (ARQ is the locked choice)
- Kafka
- RabbitMQ as a separate broker without demonstrated need
- Kubernetes
- Docker (deferred, not forbidden — see §15)
- Elasticsearch
- OpenSearch
- Meilisearch
- Typesense
- LangChain
- LlamaIndex
- vector databases
- pgvector
- embeddings
- RAG pipelines
- Firebase as a second backend
- MongoDB as a second primary database
- Prisma in the Python backend
- asyncpg (psycopg 3 is the locked driver)
- Poetry (uv is the locked choice)
- direct frontend database access
- public Supabase buckets for private files
- unofficial WhatsApp automation
- web scraping of private customer accounts
- multiple overlapping component libraries
- microservices without demonstrated need
- custom authentication replacing Supabase Auth without approval
- `packages/sdk` as a package name (always `packages/api-client`)
- `NUMERIC(14,2)` as an alternative money representation (integer minor units in `BIGINT` is final)

## 20. TOOL-SELECTION PROCESS

When a requirement needs a tool not already fixed:

1. identify the exact problem
2. confirm existing approved tools cannot solve it cleanly
3. compare a small number of maintained options
4. evaluate security, reliability, cost, lock-in, testability, and operational burden
5. choose the smallest adequate solution
6. obtain explicit approval for major infrastructure or providers
7. add the decision to `TOOLS.md`
8. add required environment variables to `DEPLOYMENT_AND_ENV.md`
9. update architecture or integration documents if boundaries change
10. add tests and operational monitoring

Claude must not treat an undecided tool as approved merely by writing a placeholder package name into code. As of this revision, the tools listed in §§3–15 with a "final, locked" annotation are no longer undecided — implement them directly without re-litigating the choice.

## 21. TOOL OWNERSHIP SUMMARY

Frontend application:

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Radix UI
- Lucide

Frontend data and forms:

- TanStack Query
- TanStack Table
- TanStack Virtual when justified
- React Hook Form
- Zod
- narrow Zustand

Analytics:

- Apache ECharts

Backend:

- Python 3.12
- FastAPI
- Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x
- Alembic
- psycopg 3
- HTTPX
- structlog
- Ruff
- mypy

Background jobs:

- ARQ (Redis-backed), in the separate `apps/worker` Railway service

Data platform:

- Supabase PostgreSQL
- Supabase Auth
- private Supabase Storage
- controlled Supabase Realtime

Temporary infrastructure:

- Upstash Redis

AI (Phase 14 only):

- OpenAI primary
- Groq optional fallback

Documents and exports:

- openpyxl (XLSX)
- Playwright/Chromium (PDF)
- Pillow (images)

Testing:

- Pytest
- Vitest
- React Testing Library
- Playwright
- k6 (load testing)

Source control and delivery:

- GitHub
- GitHub Actions
- Vercel
- Railway
- (Docker deferred)

Observability:

- Sentry
- platform logs and health signals

Package management:

- pnpm (via Corepack)
- uv

## 22. DEFINITION OF DONE FOR TOOLING

Tooling is considered correctly established only when:

- every installed dependency has an identified responsibility
- required tools are configured, not merely installed
- versions are locked
- environment variables are documented
- secrets remain outside source control
- CI validates the toolchain
- production builds are reproducible
- tests execute through the approved tools
- observability is active
- no prohibited tool has been introduced
- no duplicate architecture has been created
- `TOOLS.md` reflects every important tool decision
- `DEPLOYMENT_AND_ENV.md` reflects environment requirements
- `ROADMAP.md` is updated when tooling phases complete

## 23. FINAL IMPLEMENTATION COMMAND

Build the RKPR Restaurant CRM using the smallest reliable approved stack. Use Next.js, React, strict TypeScript, Tailwind CSS, shadcn/ui and Radix, TanStack Query and Table, React Hook Form, Zod, narrow Zustand, ECharts, Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, psycopg 3, PostgreSQL in Supabase, Supabase Auth, private Supabase Storage, controlled Supabase Realtime, Upstash Redis, ARQ for background jobs, separate Railway API and worker services, Vercel, GitHub Actions, Ruff and mypy for backend quality, k6 for load testing, openpyxl and Playwright/Chromium for documents, Sentry, OpenAI as primary AI provider (Phase 14 only), and Groq only as an optional tested fallback (Phase 14 only). Keep business rules, authorization, financial state, order state, inventory state, and auditability in the backend and PostgreSQL. Do not add n8n, Temporal, Celery, Docker (until explicitly reconsidered), microservices, Kubernetes, Kafka, Elasticsearch, vector search, embeddings, RAG frameworks, unofficial communication automation, Poetry, asyncpg, or any major unapproved provider. Every decision that was previously open in this document is now closed and locked; do not reopen phase numbering, money representation, permission naming, package naming, or the tooling choices in this file without an explicit new user decision.
