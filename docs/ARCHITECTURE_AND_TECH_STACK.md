# RKPR RESTAURANT CRM — ARCHITECTURE AND TECH STACK

## 1. DOCUMENT PURPOSE

This document defines the approved technical architecture, service boundaries, repository structure, infrastructure model, runtime responsibilities, data flow, scaling approach, security posture, deployment topology, observability model, and technology stack for the RKPR Restaurant CRM.

It must be read together with `CLAUDE.md` and `PROJECT_PLAN.md`. `CLAUDE.md` contains the highest-authority engineering rules. `PROJECT_PLAN.md` defines business scope, dummy data, workflows, and implementation phases (mapped onto the canonical sequence in `ROADMAP.md`). This file translates those requirements into a concrete technical system design. Exact tool versions and the definitive approved/forbidden tool registry live in `docs/TOOLS.md`.

The system is a private, single-business CRM built specifically for RKPR Fast-Food Restaurant. It is not a generic SaaS CRM, multi-tenant platform, no-code workflow builder, or white-label product. Architecture decisions must therefore optimize for correctness, security, speed, operational clarity, and maintainability for one restaurant deployment.

## 2. CORE ARCHITECTURAL GOALS

The architecture must support:

- A fast operational dashboard that remains responsive as data grows.
- Large and continuously growing customer, lead, order, reservation, message, inventory, audit, notification, report, and file datasets.
- Thousands of business records created every day without loading full datasets into memory or the browser.
- Multiple staff users working simultaneously with backend-enforced permissions.
- Reliable background processing for heavy, retryable, and scheduled work.
- Controlled realtime updates only where they materially improve restaurant operations.
- Strong data integrity through PostgreSQL constraints, transactions, state machines, and idempotency.
- Secure authentication, authorization, uploads, webhooks, exports, integrations, and sensitive data handling.
- Clear observability across API requests, database pressure, workers, queues, integrations, errors, and realtime behavior.
- Safe local development before all production credentials are available.
- Independent scaling of dashboard, API, background workers, database, cache, and realtime components.

The architecture must not rely on frontend-only permissions, unbounded queries, browser-resident business logic, direct browser access to privileged credentials, synchronous heavy processing, uncontrolled realtime subscriptions, or hardcoded production data.

## 3. HIGH-LEVEL SYSTEM TOPOLOGY

The approved system consists of the following major parts:

1. Web dashboard application.
2. Authoritative backend API.
3. Background worker and scheduler.
4. PostgreSQL database hosted through a dedicated Supabase project.
5. Supabase Auth.
6. Supabase Storage.
7. Controlled realtime delivery through Supabase Realtime or an approved websocket layer.
8. Redis for ephemeral coordination, caching, locks, counters, and queue support where suitable.
9. External integrations behind adapters.
10. Monitoring, logging, error tracking, and deployment automation.

The dashboard communicates only with approved APIs and explicitly authorized realtime channels. The backend remains the authoritative layer for validation, authorization, business rules, calculations, durable writes, integration orchestration, and audit behavior.

### 3.1 Logical request flow

User browser
→ Next.js dashboard
→ FastAPI backend
→ authorization and validation
→ application or domain service
→ PostgreSQL transaction
→ optional outbox event
→ worker or realtime publisher
→ external service or notification delivery

### 3.2 Logical background flow

Business event or scheduled trigger
→ durable job or outbox record
→ ARQ worker claim
→ idempotency check
→ business or integration operation
→ result persistence
→ retry, success, failure, or dead-letter state
→ user-visible status and monitoring metrics

### 3.3 Source-of-truth rules

- PostgreSQL is the source of truth for durable business data.
- Supabase Auth is the source of truth for authentication identities.
- Redis is never the only copy of business-critical data.
- Browser state is never authoritative for permissions, prices, totals, stock, loyalty balances, reservation capacity, order status, or security decisions.
- Realtime events notify clients of changes but do not replace authoritative API reads.
- External providers are authoritative only for provider-owned delivery or payment facts and must be reconciled into internal durable records.

## 4. DEPLOYMENT MODEL

The production deployment is isolated for RKPR.

### 4.1 Primary hosting direction

- Dashboard: Vercel.
- Backend API: Railway.
- Background worker: Railway as a separate service.
- Scheduler: part of the Railway worker service (ARQ's cron support), not a separate platform.
- PostgreSQL, Auth, Storage, and optional Realtime: dedicated Supabase project.
- Redis: Upstash Redis.
- Source control and CI: GitHub and GitHub Actions.
- Error tracking: Sentry.
- Additional metrics and uptime monitoring: platform-native telemetry plus Sentry, per `docs/TOOLS.md` §16.

### 4.2 Environment separation

Use distinct configuration for:

- Local development.
- Automated testing.
- Preview deployments.
- Staging when introduced.
- Production.

Each environment must use separate secrets. Production database credentials, service-role keys, signing secrets, webhook secrets, messaging credentials, and external API keys must never be reused in local or preview environments.

### 4.3 Service isolation

The API and worker must be separate deployable processes. A worker crash, queue delay, campaign send, file parse, report generation, or third-party timeout must not block normal dashboard navigation or ordinary API traffic.

The scheduler must not depend on a browser session. Scheduled reports, reservation reminders, follow-up reminders, loyalty expiries, training reminders, inventory alerts, and reconciliation jobs must continue when no user is logged in.

## 5. REPOSITORY ARCHITECTURE

Use a monorepo unless a later explicit decision changes it.

Expected structure:

```text
rkpr-crm/
├── apps/
│   ├── dashboard/
│   ├── api/
│   └── worker/
├── packages/
│   ├── ui/
│   ├── contracts/
│   ├── api-client/
│   └── config/
├── infrastructure/
│   ├── railway/
│   ├── vercel/
│   ├── monitoring/
│   └── scripts/
├── docs/
├── tests/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   └── fixtures/
├── .github/
│   └── workflows/
├── CLAUDE.md
├── ROADMAP.md
├── README.md
├── .env.example
├── package.json
├── pnpm-workspace.yaml
├── pyproject.toml
└── .gitignore
```

Docker is intentionally deferred to a later deployment/environment-hardening roadmap item. Its absence from the structure above is expected, not a defect.

### 5.1 `apps/dashboard`

Contains the Next.js CRM dashboard, route layouts, server components, client components, feature modules, typed API calls, server-state hooks, forms, tables, charts, authorization-aware presentation, and realtime client handling.

It must not contain authoritative business rules, direct privileged database access, service-role credentials, external provider secrets, or final permission decisions.

### 5.2 `apps/api`

Contains the FastAPI application, authentication and authorization dependencies, API routers, domain or application services, persistence models, repositories where useful, transaction orchestration, business state machines, integration adapters, audit logic, outbox creation, and validation schemas.

### 5.3 `apps/worker`

Contains ARQ background jobs, queue consumers, scheduled tasks (ARQ cron), integration retries, report generation, campaign processing, file processing, AI tasks, notification delivery, reconciliation, and dead-letter handling.

The worker may share backend packages or application services but must not duplicate business rules.

### 5.4 `packages/ui`

Contains shared design-system primitives and reusable operational components such as buttons, inputs, dialogs, tables, badges, skeletons, accessible menus, date controls, pagination controls, and chart wrappers.

It must not become a place for feature-specific business logic.

### 5.5 `packages/contracts`

Contains shared API contracts, generated types, status enums, error shapes, pagination definitions, and event contracts when a controlled synchronization mechanism is used.

Backend types remain authoritative. Generated or shared client types must be refreshed through a documented process.

### 5.6 `packages/api-client`

Contains the typed API client, request cancellation, authentication handling, error mapping, pagination helpers, and API response parsing. This package is always named `packages/api-client` — never `packages/sdk`.

### 5.7 `packages/config`

Contains non-secret shared constants, build configuration, feature flags, environment type definitions, and common tooling configuration. Secrets must never be committed here.

### 5.8 Dependency rules

- Applications may depend on shared packages.
- Shared packages must not depend on applications.
- Avoid circular imports.
- Domain-specific code should stay near the owning backend feature.
- Avoid giant generic `utils` directories.
- Do not create duplicate API clients, enum definitions, permission maps, or validation schemas.

## 6. FRONTEND ARCHITECTURE

### 6.1 Core frontend stack

- Next.js with the App Router (latest stable release compatible with the selected React version).
- React (stable version required by the selected Next.js release).
- TypeScript with strict mode enabled (latest stable version compatible with the framework).
- Tailwind CSS (latest stable supported version).
- shadcn/ui components built on Radix primitives.
- TanStack Query for server state.
- TanStack Table for data grids.
- TanStack Virtual for long tables, lists, timelines, and message histories only when measurements show it is needed.
- React Hook Form for form state.
- Zod for client-side schema validation and safe parsing.
- Zustand only for narrowly scoped client state that is not server state.
- Apache ECharts for analytical visualizations.
- Lucide for iconography — the only default icon pack.
- Playwright for end-to-end testing.
- Vitest and React Testing Library for component and frontend unit tests.

Do not hardcode framework version numbers from memory. Query the package registry or official release sources during installation, select current stable compatible versions, and lock them in `pnpm-lock.yaml`.

### 6.2 App Router usage

Use server components by default for non-interactive and safely server-rendered content. Use client components only where interaction, browser APIs, local state, forms, realtime subscriptions, or client-side caching require them.

Keep client boundaries small. Do not convert entire sections into client components merely for convenience.

### 6.3 Route organization

Recommended high-level routes:

```text
/dashboard
/customers
/customers/[customerId]
/leads
/leads/[leadId]
/orders
/orders/[orderId]
/menu
/inventory
/suppliers
/reservations
/communications
/knowledge-base
/staff
/marketing
/loyalty
/feedback
/reports
/settings
```

Routes may be grouped by layout, but the twelve approved user-facing sections must remain clear and consistent.

### 6.4 Feature organization

Each feature should contain only what it owns:

```text
features/customers/
├── api/
├── components/
├── hooks/
├── schemas/
├── types/
├── utils/
└── tests/
```

Do not create broad cross-feature coupling. Shared operational UI belongs in `packages/ui`; feature-specific behavior stays within the feature.

### 6.5 Server state

TanStack Query is the default client-side server-state layer.

Required behavior:

- Query keys must be structured and stable.
- Permission-dependent data must include appropriate scope in query keys.
- Stale and cache times must be chosen by data volatility.
- Mutations must invalidate or update only the affected queries.
- Requests must be cancelled when searches, filters, pages, or routes change.
- Retry rules must distinguish temporary network failures from validation or permission errors.
- Sensitive data must not be persisted in insecure browser storage.
- Large server datasets must not be copied into global state.

### 6.6 Table architecture

Every growing table must use server-side:

- Pagination.
- Search.
- Filter allowlists.
- Sort allowlists.
- Date-range limits.
- Maximum page size.

Use cursor pagination for conversations, activity feeds, audit events, notifications, and high-volume changing records. Offset pagination may be used for stable administrative lists when query performance remains acceptable.

Virtualization is used when rendering many visible rows, but virtualization does not replace server-side pagination.

### 6.7 Frontend performance

- Use route-level code splitting.
- Lazy-load heavy charts, editors, previews, and secondary panels.
- Do not render hidden tabs or dialogs before needed.
- Avoid massive client-side transformations.
- Use bounded chart data returned by aggregation endpoints.
- Use skeletons rather than full-page blocking spinners.
- Load dashboard widgets independently where useful.
- Use image optimization, correct sizing, and lazy loading.
- Avoid broad context providers that rerender the entire application.
- Keep state local unless genuine cross-route sharing is required.

### 6.8 Form architecture

Use React Hook Form and Zod.

Forms must support:

- Client validation for usability.
- Server validation as the authority.
- Field-level errors.
- Form-level conflict errors.
- Loading and disabled states.
- Prevention of duplicate submission.
- Dirty-state warnings where relevant.
- Safe handling of server conflicts and stale records.
- Accessible labels, descriptions, focus behavior, and error announcements.

### 6.9 Frontend authorization behavior

The frontend may hide unavailable routes and actions for usability, but the backend must enforce every permission.

Frontend permission data should come from an authoritative current-user or permissions endpoint. Do not hardcode role assumptions across components.

### 6.10 Accessibility

The dashboard must support:

- Keyboard navigation.
- Visible focus states.
- Semantic HTML.
- Accessible names and descriptions.
- Screen-reader-friendly validation and notifications.
- Sufficient contrast.
- Non-color status indicators.
- Reduced-motion preference.
- Responsive layout for operational desktop use and practical smaller-screen access.

## 7. BACKEND ARCHITECTURE

### 7.1 Core backend stack

- Python 3.12.x (never Python 3.14 for this project, even if it is installed globally).
- FastAPI.
- Pydantic v2 and pydantic-settings.
- SQLAlchemy 2.x.
- Alembic.
- **psycopg 3** with binary and async support — the final, locked PostgreSQL driver for this project.
- HTTPX for external HTTP calls.
- structlog for structured logging.
- Ruff for linting and formatting.
- mypy for static type checking.
- Pytest, pytest-asyncio, and HTTPX test clients.
- Sentry SDK.

### 7.2 Layering

Recommended backend layers:

1. API transport layer.
2. Authentication and authorization layer.
3. Application service layer.
4. Domain rules and state machines.
5. Persistence and repository layer.
6. Integration adapter layer.
7. Event and outbox layer.
8. Background job layer (ARQ).

API routers must remain thin. They should authenticate, authorize, validate, invoke application services, and construct responses. They must not contain large business workflows.

### 7.3 Suggested backend feature layout

```text
apps/api/app/
├── main.py
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── security.py
│   ├── errors.py
│   ├── pagination.py
│   └── observability.py
├── db/
│   ├── base.py
│   ├── session.py
│   ├── models/
│   └── migrations/
├── auth/
├── permissions/
├── audit/
├── customers/
├── leads/
├── orders/
├── menu/
├── inventory/
├── reservations/
├── communications/
├── knowledge_base/
├── staff/
├── marketing/
├── loyalty/
├── feedback/
├── reports/
├── notifications/
├── integrations/
└── shared/
```

Each feature may contain:

```text
models.py
schemas.py
repository.py
service.py
router.py
permissions.py
states.py
errors.py
events.py
tests/
```

Not every feature requires every file. Avoid empty abstraction layers.

### 7.4 API design

Use RESTful JSON APIs unless a later approved requirement justifies another protocol.

Requirements:

- Version the API path where breaking changes may occur, for example `/api/v1`.
- Use Pydantic request and response schemas.
- Do not return raw ORM objects.
- Use consistent error codes and response shapes.
- Enforce maximum list limits.
- Allow only approved filters and sorts.
- Validate date ranges.
- Use idempotency keys for duplicate-sensitive operations.
- Use HTTP status codes consistently.
- Do not expose stack traces or SQL details.
- Generate accurate OpenAPI documentation.

### 7.5 Application services

Application services orchestrate business operations such as:

- Converting a lead into a customer.
- Transitioning an order state.
- Approving a reservation.
- Reserving or consuming inventory.
- Merging duplicate customers.
- Issuing loyalty points.
- Recording a refund request.
- Creating a campaign job.
- Generating an export request.

They are responsible for transaction boundaries, domain validation, audit creation, event creation, and consistent failure behavior.

### 7.6 Domain state machines

Use explicit allowed transitions for:

- Leads.
- Orders.
- Payment states.
- Refunds.
- Reservations.
- Complaints.
- Campaigns.
- Background jobs.
- Integration connections.
- Staff employment status where appropriate.

Invalid transitions must be rejected by the backend even if a client manually constructs a request.

### 7.7 Error model

Define stable error categories:

- Validation error.
- Authentication required.
- Permission denied.
- Record not found.
- Conflict.
- Invalid state transition.
- Rate limited.
- External dependency unavailable.
- Integration configuration error.
- Retryable processing failure.
- Internal error.

Every error response should include a safe machine-readable code, user-safe message, correlation identifier, and field errors where relevant.

## 8. DATABASE ARCHITECTURE

### 8.1 Core data platform

Use PostgreSQL hosted in a dedicated Supabase project.

PostgreSQL stores durable CRM data including:

- Staff and roles.
- Customers and identities.
- Leads and activities.
- Orders, items, payments, and status history.
- Products, variants, recipes, and modifiers.
- Inventory items, batches, stock movements, and suppliers.
- Reservations and table assignments.
- Conversations and messages.
- Documents and metadata.
- Loyalty ledger.
- Campaigns and audience snapshots.
- Feedback and complaints.
- Notifications.
- Audit logs.
- Outbox events.
- Jobs or job references where appropriate.
- Integration metadata and webhook deduplication records.
- Report definitions and generated-report records.

### 8.2 Identifier strategy

Use UUIDs or UUIDv7-compatible identifiers where operationally supported and approved. Public-facing human-readable references such as `ORD-2026-000123` or `LEAD-000123` are separate display identifiers and must not replace secure primary keys.

### 8.3 Timestamp strategy

- Store timestamps in UTC.
- Use timezone-aware timestamp types.
- Convert to the configured restaurant timezone (`Asia/Kolkata`) for display.
- Store business-local dates separately only where calendar logic requires it.

### 8.4 Financial data

Money representation is final and locked: use integer minor units in `BIGINT` columns, with field names ending in `_minor` (for example `price_minor`, `subtotal_minor`, `tax_minor`, `discount_minor`, `total_minor`, `refund_minor`, `amount_minor`).

Never use floating-point values, and never use `NUMERIC(14,2)` as an alternative, for:

- Prices.
- Taxes.
- Discounts.
- Refunds.
- Supplier costs.
- Inventory valuation.
- Loyalty value.

Authoritative totals are computed on the backend and stored with enough detail to explain the calculation. Currency code is stored where the domain requires it; the default dummy currency is INR.

### 8.5 Constraint strategy

Use database constraints for durable invariants:

- Foreign keys.
- Unique constraints.
- Check constraints.
- Non-null constraints.
- Valid numeric ranges.
- Valid date relationships where practical.
- Deduplication keys.
- Idempotency keys.

Application validation complements but does not replace database constraints.

### 8.6 Index strategy

Indexes must follow query patterns.

Evaluate indexes for:

- Foreign keys used in joins and filters.
- Customer phone and normalized email.
- Lead source, status, assignee, next-follow-up time, and created time.
- Order source, status, customer, payment state, fulfilment state, and created time.
- Reservation date, start time, status, approval status, and customer.
- Message conversation, channel, created time, provider message ID, and unread queries.
- Inventory item, storage zone, stock status, expiry time, and movement time.
- Notification user, read state, type, and created time.
- Audit actor, action, target, and created time.
- Campaign status, scheduled time, and audience references.

Use composite indexes for common combined filters and sorts. Use partial indexes for active, unread, pending, or non-deleted records where they materially improve queries.

Do not add indexes indiscriminately because every index increases write cost and storage.

### 8.7 Soft deletion

Use soft deletion for customers, leads, suppliers, staff, documents, menu records, and other entities requiring history or restoration.

Use `deleted_at`, `deleted_by`, and optional deletion reason where appropriate. Unique constraints must account for active versus deleted records through partial indexes or controlled restore rules.

### 8.8 History tables and ledgers

Append-oriented history is required for:

- Order status changes.
- Reservation status changes.
- Lead status and assignment changes.
- Inventory stock movements.
- Loyalty entries.
- Audit events.
- Message delivery states where needed.
- Integration sync attempts.

Do not replace historical records with a single mutable summary when traceability is required.

### 8.9 Transactions and concurrency

Use database transactions for multi-step operations.

Use row-level locks, advisory locks, optimistic version columns, or serializable patterns where concurrency can corrupt:

- Inventory reservation and consumption.
- Loyalty balances.
- Reservation capacity.
- Order transitions.
- Customer merges.
- Duplicate webhook processing.
- Sequential human-readable references.

The chosen locking approach must remain bounded and avoid long transactions.

### 8.10 Migration tooling

Use Alembic for backend schema migrations. Supabase-specific policies, extensions, or functions may use reviewed SQL migration files where required.

Migrations must be:

- Deterministic.
- Idempotent where applicable.
- Tested from a clean database.
- Tested from the previous schema state.
- Safe for existing data.
- Reviewed for lock impact.
- Accompanied by backfills where needed.

## 9. SUPABASE RESPONSIBILITIES

### 9.1 Dedicated project

Use one dedicated Supabase project for RKPR. Do not introduce tenant tables, tenant selectors, or multi-tenant RLS architecture unless explicitly approved later.

### 9.2 Supabase Auth

Supabase Auth handles staff authentication identities, password reset, invitation support where appropriate, session issuance, and MFA capability.

The FastAPI backend validates authentication tokens and maps authenticated identities to internal staff profiles and permissions.

### 9.3 Supabase Storage

Use private buckets for:

- Knowledge Base files.
- Customer or communication attachments where approved.
- Staff documents.
- Menu images.
- Generated reports.
- Secure exports.

All access must be permission checked before signed URLs are generated.

### 9.4 Supabase Realtime

Use only for scoped, operationally useful events. Realtime subscriptions must not be attached to every table or row.

Possible realtime uses:

- Order status changes on active order screens.
- New reservation requests.
- Reservation decisions.
- Conversation message and unread updates.
- Inventory critical alerts.
- User notifications.

Prefer minimal domain-event payloads. Re-fetch sensitive data through authorized APIs.

## 10. AUTHENTICATION AND AUTHORIZATION ARCHITECTURE

### 10.1 Authentication flow

1. User signs in through the approved dashboard flow.
2. Supabase Auth verifies credentials.
3. Session is established using the approved secure web-session model.
4. Dashboard requests protected data.
5. FastAPI validates the token or server-managed session.
6. Internal staff profile and account status are loaded.
7. Permission and record scope are evaluated.
8. Request proceeds or is rejected.

### 10.2 Session handling

Prefer secure HTTP-only cookies where compatible with the final architecture. Avoid storing long-lived sensitive tokens in localStorage.

Support:

- Login.
- Logout.
- Refresh.
- Expiration.
- Revocation.
- Disabled-account enforcement.
- Password reset.
- Invitation acceptance.
- MFA readiness for privileged accounts.

### 10.3 Authorization model

Use backend-enforced role and permission checks.

Permissions use the single canonical capability registry defined in `DATABASE_AND_API.md` §4.4: lowercase, dot-separated, domain first, action or sub-action after the domain. For example:

- `customers.view`
- `customers.update`
- `customers.merge`
- `orders.transition`
- `orders.refund.request`
- `orders.refund.approve`
- `inventory.adjust`
- `inventory.receive`
- `reservations.approve`
- `campaigns.approve`
- `reports.export`
- `staff.hr_sensitive.read`
- `settings.integrations.update`

The exact complete registry is represented in code from a single source and tested for uniqueness. Do not invent synonym permission codes in any other document or module.

Permissions may include record scope, department scope, assigned-record scope, or self-only scope.

### 10.4 RLS strategy

Because the system is single-business and all access flows through the authoritative API, PostgreSQL application-level authorization is primary. Supabase RLS may still be used for direct browser-accessed services such as Storage or explicitly approved realtime access.

Do not create a false sense of security by relying on frontend route hiding or incomplete RLS policies while privileged backend credentials bypass them.

## 11. REDIS ARCHITECTURE

Redis is used only for suitable ephemeral workloads.

Approved uses may include:

- Rate limiting.
- Short-lived cache entries.
- Distributed locks.
- Idempotency coordination.
- ARQ queue transport and coordination.
- Realtime presence or ephemeral connection state where needed.
- Request deduplication.
- Temporary counters.
- Cache stampede protection.

Redis must not be the only source of truth for orders, customers, stock, reservations, loyalty, permissions, or messages.

### 11.1 Cache rules

Every cache requires:

- Explicit key structure.
- Permission or user scope where needed.
- TTL.
- Invalidation behavior.
- Safe fallback to the source of truth.
- Protection against serving one user's sensitive data to another.

Use cache only where measured value justifies complexity.

## 12. BACKGROUND JOB ARCHITECTURE

### 12.1 Approved queue system

**ARQ is the approved initial Python background-job and scheduling library for this project.** It is Redis-backed, compatible with async Python, has a smaller operational surface than Celery for a single-business system of this size, and supports retries, timeouts, scheduled jobs, and worker functions, aligning cleanly with the separate Railway worker process.

PostgreSQL still contains the durable business job records, outbox records, idempotency keys, audit history, and final status where required. ARQ and Redis coordinate execution; they are not the sole durable source of business truth. Dead-letter handling and stale-job recovery are implemented at the application layer using documented database state and operational tooling.

If a proven technical incompatibility between ARQ and the selected Upstash Redis connection mode is discovered, implementation must stop and report the exact issue before silently choosing a different queue platform — see `docs/TOOLS.md` §7.3.

### 12.2 Background workloads

- Email, WhatsApp, and SMS delivery.
- Campaign processing.
- Reservation reminders.
- Lead follow-up reminders.
- Scheduled reports.
- PDF and spreadsheet generation.
- Large imports and exports.
- File scanning and document processing.
- AI summaries.
- Integration synchronization.
- Reconciliation.
- Expiry and training reminders.
- Inventory alerts.
- Feedback requests.
- Dead-letter recovery operations.

### 12.3 Job requirements

Every job must define:

- Job type.
- Trigger.
- Input schema.
- Idempotency key.
- Timeout.
- Retry policy.
- Maximum attempts.
- Backoff and jitter.
- Failure classification.
- Dead-letter state.
- Audit behavior.
- Correlation identifier.
- User-visible status where useful.
- Metrics.

### 12.4 Outbox pattern

Use a transactional outbox or equivalent reliable event mechanism for critical side effects.

Example:

1. Approve reservation inside a database transaction.
2. Store approved status and outbox event in the same transaction.
3. Commit transaction.
4. Worker reads outbox event.
5. Send WhatsApp confirmation.
6. Record provider result.
7. Retry safely if delivery fails.

Never send external communication inside an uncommitted database transaction.

## 13. REALTIME ARCHITECTURE

### 13.1 Purpose

Realtime improves active operational workflows. It must not become a replacement for APIs or a subscription to the entire database.

### 13.2 Event contract

Realtime events should contain:

- Stable event name.
- Version.
- Event ID.
- Record type and record ID.
- Timestamp.
- Minimal safe change summary.
- Actor metadata when safe.
- Correlation ID.

### 13.3 Subscription rules

- Subscribe only for the active user and screen.
- Use scoped channels.
- Unsubscribe on route, identity, and permission changes.
- Do not create one subscription per visible row.
- Handle reconnects.
- Deduplicate events.
- Handle out-of-order events.
- Reconcile with APIs after reconnect or uncertainty.
- Recheck authorization for every delivered record.

### 13.4 Suggested domains

- Orders.
- Reservations.
- Communications.
- Notifications.
- Critical inventory alerts.

Historical tables, reports, customer lists, suppliers, and large audit datasets should normally use APIs rather than persistent realtime subscriptions.

## 14. FILE STORAGE AND PROCESSING ARCHITECTURE

### 14.1 Storage model

Use private Supabase Storage buckets with server-generated paths.

Recommended logical paths:

```text
knowledge-base/{folder-id}/{document-id}/{version-id}/file.ext
staff/{staff-id}/{document-id}/file.ext
customers/{customer-id}/attachments/{attachment-id}/file.ext
communications/{conversation-id}/{message-id}/file.ext
menu/{product-id}/images/{image-id}.ext
reports/{report-id}/output.ext
exports/{export-id}/output.ext
```

Do not rely on user-supplied filenames for storage paths.

### 14.2 Upload pipeline

1. Validate authentication and permission.
2. Validate declared type, extension, MIME type, and file signature.
3. Enforce size limit.
4. Generate safe storage key.
5. Upload to quarantine or private staging area.
6. Scan for malware.
7. Process metadata or preview in a worker.
8. Mark ready or rejected.
9. Create an audit record.
10. Generate short-lived signed URLs only after authorization.

### 14.3 File processing tools

Approved libraries (see `docs/TOOLS.md` §11 for the complete registry):

- openpyxl for XLSX generation.
- Playwright with Chromium for controlled HTML-to-PDF rendering (invoices, receipts, management reports), run in the worker.
- Pillow for image validation and optimization.
- An approved MIME-signature library (libmagic or equivalent).
- An approved malware-scanning service or ClamAV.

The lightweight Knowledge Base must not introduce embeddings, pgvector, chunking, semantic search, or RAG.

## 15. INTEGRATION ARCHITECTURE

All external services must be behind adapters.

### 15.1 Adapter contract

Each adapter should expose stable internal operations and hide provider-specific details.

Example:

```text
MessagingProvider
- send_template_message(...)
- send_freeform_message(...)
- get_delivery_status(...)
- verify_webhook(...)

EmailProvider
- send_email(...)
- send_report(...)
- verify_event(...)

CalendarProvider
- create_event(...)
- update_event(...)
- delete_event(...)
- check_connection(...)
```

### 15.2 Candidate integrations

- Restaurant website.
- POS, only when an official API or approved export exists.
- WhatsApp Cloud API.
- Email provider.
- SMS provider.
- Google Calendar.
- Payment provider.
- Zomato and Swiggy, only through approved and available capabilities.
- Meta and Google advertising lead or attribution data where supported.

### 15.3 Webhook architecture

Every webhook endpoint must:

- Verify signature.
- Apply replay protection.
- Enforce size limits.
- Parse through strict schemas.
- Store provider event ID.
- Deduplicate processing.
- Return quickly.
- Move heavy work to the worker.
- Preserve raw payload only when legally and operationally justified.
- Redact secrets from logs.
- Reconcile missing or conflicting events.

### 15.4 Degraded operation

Optional integrations must fail independently. A disconnected WhatsApp provider must not stop order viewing, customer search, inventory management, or dashboard login.

The UI must show connected, disconnected, degraded, pending, and failed states honestly.

## 16. COMMUNICATION ARCHITECTURE

### 16.1 Channels

- WhatsApp.
- Email.
- SMS.
- Website messages.
- Phone call notes.

### 16.2 Message model

Store:

- Conversation ID.
- Message ID.
- Channel.
- Direction.
- Sender and recipient references.
- Provider message ID.
- Message type.
- Sanitized content.
- Attachment references.
- Created, sent, delivered, read, and failed times where available.
- Failure code.
- Template reference.
- Assigned staff.
- Customer or lead link.

### 16.3 Delivery rules

- Deduplicate provider events.
- Do not report a message as delivered without provider confirmation.
- Store failures visibly.
- Respect consent and provider policy.
- Keep internal notes separate from customer-visible messages.
- Paginate message history with cursors.

## 17. REPORTING AND ANALYTICS ARCHITECTURE

### 17.1 Operational dashboard queries

Use PostgreSQL aggregation queries or maintained summary tables where evidence justifies them.

Do not send raw order, customer, message, or inventory history to the browser for chart calculations.

### 17.2 Scheduled reports

Daily, weekly, and monthly reports are created by background jobs.

Flow:

1. Scheduler creates report job.
2. Worker loads approved metrics.
3. Worker generates report output (openpyxl for XLSX, Playwright/Chromium for PDF).
4. Output is stored privately.
5. Recipient configuration is loaded from Settings.
6. Email delivery is attempted.
7. Delivery result is recorded.
8. Failure is retried or surfaced.

### 17.3 Export architecture

Large exports must be asynchronous.

- User requests export.
- Permission is checked.
- Export job is created.
- Worker generates file in chunks.
- File is stored privately.
- User receives a notification.
- Signed URL expires.
- Sensitive exports are audited.

### 17.4 Charting

Apache ECharts is the approved library for rich analytical dashboards because it supports large datasets, multiple chart types, responsive rendering, and advanced interactions. Data must still be bounded and pre-aggregated.

## 18. AI ARCHITECTURE

### 18.1 Approved AI use cases

- Summarizing customer history.
- Drafting a reply for staff review.
- Explaining changes in metrics.
- Summarizing daily or weekly activity.
- Flagging potential anomalies for human review.
- Producing management narrative from verified structured data.

### 18.2 Provider abstraction

Use an internal provider interface so OpenAI (primary) or Groq (optional fallback) can be configured, tested, replaced, or disabled. AI credentials and integration are introduced only when the roadmap reaches Phase 14 — Reports, Analytics, and Controlled AI, not during the foundation phase.

### 18.3 AI safety rules

- AI must receive only data the requesting user is authorized to access.
- Sensitive data must be minimized.
- Outputs must use structured schemas where actions depend on them.
- AI cannot directly change stock, refunds, payments, permissions, reservations, staff records, or customer records without deterministic validation and required confirmation.
- AI-generated facts must not override database facts.
- AI usage, cost, latency, and failures must be tracked.
- Timeouts and provider failures must degrade safely.
- Knowledge Base RAG is explicitly excluded.
- No LangChain, LlamaIndex, or similar AI framework — direct typed provider adapters are sufficient for the current AI needs.

## 19. SECURITY ARCHITECTURE

### 19.1 Security layers

- Authentication.
- Backend authorization.
- Record-scope checks.
- Strict input validation.
- Database constraints.
- Rate limiting.
- Secure file processing.
- Webhook verification.
- Secret management.
- Audit logging.
- Monitoring and alerting.
- Backup and recovery.

### 19.2 Secret management

Secrets live only in managed environment variables or secret stores.

Never expose:

- Supabase service-role keys.
- Database passwords.
- JWT signing secrets.
- Messaging provider credentials.
- Payment secrets.
- Webhook secrets.
- AI provider keys.
- Storage credentials.

Client-exposed environment variables must be explicitly allowlisted.

### 19.3 Network security

- HTTPS only in production.
- Narrow CORS allowlists.
- Secure cookies.
- Safe security headers.
- External request timeouts.
- No unrestricted internal admin endpoints.
- Optional IP or additional controls for highly sensitive administration if later required.

### 19.4 Input security

Validate:

- JSON bodies.
- Query parameters.
- Path identifiers.
- Headers.
- Webhook payloads.
- File uploads.
- Integration responses.
- Import files.

Prevent SQL injection, XSS, CSRF where applicable, path traversal, unsafe redirects, mass assignment, IDOR, and oversized request abuse.

### 19.5 Audit architecture

Audit records should include:

- Actor.
- Action.
- Target type.
- Target ID.
- Timestamp.
- Request or correlation ID.
- Source.
- Safe metadata.
- Before and after summaries when useful.

Audit logs must be append-oriented, access controlled, paginated, indexed, and protected from ordinary editing.

## 20. PERFORMANCE ARCHITECTURE

Performance is an architectural requirement, not a final optimization phase.

### 20.1 Browser and dashboard

- Small initial bundles.
- Route-level code splitting.
- Bounded server-state queries.
- Independent widget loading.
- Virtualized rendering where needed.
- Request cancellation.
- Debounced search.
- Lazy-loaded heavy panels.
- No full-table downloads.

### 20.2 API

- Bounded pagination.
- Maximum page sizes.
- Select only required columns.
- Avoid N+1 queries.
- Database-side filtering and aggregation.
- Connection pooling.
- Timeouts.
- Background processing for heavy work.
- Streaming or chunking for large data movement.

### 20.3 Database

- Query-pattern indexes.
- Query-plan review.
- Short transactions.
- Bounded locks.
- Cursor pagination for deep high-volume feeds.
- Partial and composite indexes where justified.
- Archiving or partitioning only when evidence requires it.

### 20.4 Cache

- Cache only expensive, repeated, safe queries.
- Keep TTLs explicit.
- Scope sensitive caches.
- Invalidate correctly.
- Do not hide stale critical operational state behind long cache lifetimes.

### 20.5 Realtime

- Few scoped channels.
- Minimal payloads.
- Reconciliation after reconnect.
- No row-per-subscription patterns.

## 21. OBSERVABILITY ARCHITECTURE

### 21.1 Logging

Use structured JSON logs in production (structlog).

Include:

- Timestamp.
- Service.
- Environment.
- Severity.
- Request ID.
- Correlation ID.
- User or actor ID where safe.
- Route or job type.
- Duration.
- Result.
- Error classification.

Redact secrets, tokens, passwords, payment details, authorization headers, and unnecessary personal data.

### 21.2 Error tracking

Use Sentry for dashboard, API, and worker errors.

Configure:

- Environment tags.
- Release versions.
- Source maps.
- Server stack traces.
- Sensitive data scrubbing.
- Performance traces at controlled sampling rates.

### 21.3 Metrics

Track where supported:

- Request latency.
- Error rate.
- Database query time.
- Connection usage.
- Queue depth.
- Job duration.
- Retry count.
- Dead-letter count.
- Integration health.
- Cache hit rate.
- Realtime reconnects.
- Notification delivery success.
- Export and report generation time.

### 21.4 Health endpoints

- Liveness endpoint: process is running.
- Readiness endpoint: required dependencies are usable.
- Detailed internal health: restricted to authorized operators.

Do not expose secrets or unnecessary infrastructure details publicly.

## 22. TESTING STACK AND ARCHITECTURE

### 22.1 Backend testing

- Pytest.
- pytest-asyncio.
- HTTPX test client.
- Disposable PostgreSQL test environment where practical.
- Factory or fixture utilities.
- Migration tests.
- Permission tests.
- Concurrency tests for critical operations.

### 22.2 Frontend testing

- Vitest.
- React Testing Library.
- Mock Service Worker where appropriate.
- Playwright for end-to-end flows.

### 22.3 Required test layers

- Unit tests.
- API integration tests.
- Database constraint tests.
- Migration tests.
- Worker and retry tests.
- Permission and security tests.
- Component tests.
- End-to-end tests.
- Performance-oriented query and rendering checks for critical paths (k6 for load testing).

### 22.4 Test data

Use the dummy restaurant, menu, customer, supplier, inventory, order, and lead data from `PROJECT_PLAN.md` as controlled fixtures or seeds, including the canonical 65-person dummy staff set.

Test fixtures must be deterministic and clearly separated from production data.

## 23. CI/CD ARCHITECTURE

Use GitHub Actions.

### 23.1 Pull request checks

- Dependency installation using lockfiles (`pnpm-lock.yaml`, `uv.lock`).
- Formatting.
- Linting (Ruff, ESLint).
- Type checking (mypy, strict TypeScript).
- Backend unit and integration tests.
- Frontend tests.
- Migration validation.
- Production builds.
- Security or dependency scanning.

### 23.2 Deployment flow

Recommended flow:

1. Merge approved code.
2. CI passes.
3. Preview or staging deployment.
4. Migration safety check.
5. Apply production migration through controlled process.
6. Deploy API and worker.
7. Deploy dashboard.
8. Verify health and error monitoring.
9. Run smoke tests.

Do not auto-apply destructive migrations without an explicit controlled strategy.

### 23.3 Rollback

Rollback planning must include:

- Application rollback.
- Forward-compatible database migrations.
- Feature flags where justified.
- Worker compatibility.
- Safe handling of in-flight jobs.
- Monitoring of post-deployment errors.

## 24. LOCAL DEVELOPMENT STACK

Recommended local tools:

- Node.js current active LTS.
- pnpm, enabled through Corepack.
- Python 3.12.x.
- **uv** for fast, locked Python dependency management — the single, final choice for this project. Do not use Poetry.
- PostgreSQL container or Supabase local stack where appropriate.
- Redis container where local queue behavior is required.
- Git.
- GitHub CLI where useful.
- VS Code.
- Claude Code.

Docker is intentionally deferred for this build; local Postgres/Redis containers are a later convenience item, not a current requirement — local development may use isolated Supabase/Upstash development projects instead.

### 24.1 Package management

Use pnpm workspaces for JavaScript and TypeScript packages, enabled through Corepack.

For Python, use `uv` for locked dependency management. Do not use multiple Python dependency managers simultaneously.

### 24.2 Local integration placeholders

External providers must support disabled or sandbox adapters so development can proceed without real credentials.

Disabled integrations must return explicit configuration states, not fake success.

## 25. APPROVED TECHNOLOGY MATRIX

The complete, authoritative tool registry — including exact status (required, optional, deferred, forbidden) for every technology — lives in `docs/TOOLS.md`. Summary:

### Frontend

Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Radix UI, TanStack Query, TanStack Table, TanStack Virtual, React Hook Form, Zod, Zustand (narrow use), Apache ECharts, Lucide, Playwright, Vitest, React Testing Library.

### Backend

Python 3.12, FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2.x, Alembic, psycopg 3, HTTPX, structlog, Ruff, mypy, Pytest.

### Background jobs

ARQ (Redis-backed), running in the separate `apps/worker` Railway service.

### Data and infrastructure

PostgreSQL, Supabase (managed PostgreSQL, Auth, Storage, controlled Realtime), Upstash Redis, Railway, Vercel, GitHub, GitHub Actions, Sentry.

### Documents and files

openpyxl (XLSX), Playwright/Chromium (PDF), Pillow (images), an approved MIME-signature library, an approved malware scanner.

### AI

OpenAI (primary, Phase 14 only), Groq (optional fallback, Phase 14 only).

### Communications

WhatsApp Cloud API, an approved email provider, an approved SMS provider (deferred), Google Calendar API (optional).

### Load testing

k6.

## 26. TECHNOLOGIES EXPLICITLY NOT APPROVED BY DEFAULT

Do not add these without explicit architectural approval:

- A second frontend framework.
- A second backend framework.
- GraphQL merely for fashion or convenience.
- MongoDB for core CRM data.
- Elasticsearch, OpenSearch, Meilisearch, or Typesense for ordinary CRM search before PostgreSQL search is proven insufficient.
- Kafka for initial deployment without evidence of need.
- Kubernetes for initial deployment without evidence of need.
- Microservices splitting each module into separate services.
- RAG, embeddings, pgvector, or vector databases for the Knowledge Base.
- Generic workflow builders.
- Customer-facing theme builders.
- Multi-tenant infrastructure (no `tenant_id`, tenant tables, or tenant-based RLS).
- Direct browser access to privileged database operations.
- n8n.
- Temporal (not approved for the current build).
- Celery (ARQ is the locked choice; see §12.1).
- Poetry (uv is the locked choice; see §24.1).
- asyncpg (psycopg 3 is the locked driver; see §7.1).
- `packages/sdk` (always `packages/api-client`; see §5.6).

## 27. SCALING STRATEGY

### 27.1 Initial scale

Use a modular monolith with separate dashboard, API, worker, database, cache, and provider services.

This gives clear boundaries without premature distributed-system complexity.

### 27.2 Horizontal scaling

The API should remain stateless except for external stores and may run multiple instances when required.

Workers may scale independently by queue type or workload.

### 27.3 Database scaling

Before considering architectural replacement:

- Improve indexes.
- Review query plans.
- Remove N+1 queries.
- Use aggregation endpoints.
- Use connection pooling.
- Add caching where justified.
- Move heavy work to workers.
- Archive high-volume history if evidence requires it.
- Increase managed database resources when required.

### 27.4 Future service extraction

Extract a separate service only when there is measured need, independent operational scaling, a clear domain boundary, and acceptable complexity.

Possible future candidates could include high-volume communications or reporting, but they remain modules in the initial architecture.

## 28. FAILURE AND RECOVERY DESIGN

The system must tolerate partial failures.

Examples:

- If WhatsApp fails, reservation approval remains stored and delivery failure is visible.
- If report email fails, the generated report remains available and the job retries.
- If realtime disconnects, the dashboard re-fetches authoritative API data.
- If Redis is temporarily unavailable, core durable reads and writes should fail safely or use defined fallback behavior rather than corrupt data.
- If an integration webhook is duplicated, idempotency prevents duplicate effects.
- If a worker crashes, claimed jobs are retried or recovered.
- If a file scan fails, the file remains quarantined and unavailable.

Every critical failure path must be observable and recoverable.

## 29. BACKUP AND RECOVERY ARCHITECTURE

- Use managed PostgreSQL backups.
- Document point-in-time recovery availability based on the selected Supabase plan.
- Back up critical configuration and storage metadata.
- Preserve generated reports or exports only according to retention policy.
- Document restore procedures.
- Validate restoration at the appropriate operational stage.
- Store secrets outside backups where appropriate and maintain rotation procedures.

## 30. DATA RETENTION AND PRIVACY

Define retention policies for:

- Audit logs.
- Messages.
- Customer records.
- Leads.
- Staff documents.
- Generated reports.
- Exports.
- Failed jobs.
- Webhook payloads.
- Provider delivery logs.

Collect only necessary personal data. Restrict HR-sensitive and customer-sensitive information. Support controlled deletion, anonymization, or retention exceptions according to final legal and business requirements.

## 31. ARCHITECTURAL DECISION PROCESS

Significant changes require documentation in the project decisions file when created.

Examples:

- Changing the queue system away from ARQ.
- Replacing Supabase Realtime.
- Introducing a search engine.
- Changing the permission model or naming convention.
- Adding a microservice.
- Changing deployment providers.
- Adding a new public integration.
- Changing monetary representation away from integer minor units.
- Changing the identifier strategy.

Do not introduce major technologies inside feature work without updating architecture documentation and explaining the tradeoff. Phase numbering, money representation, permission naming, `packages/api-client` naming, and the tooling choices locked in §7, §12, and §24 of this document are settled decisions and must not be silently reopened.

## 32. ARCHITECTURE ACCEPTANCE CHECKLIST

The architecture is correctly implemented only when:

- Dashboard, API, and worker are separate deployable units.
- PostgreSQL remains the durable source of truth.
- Authentication and backend authorization are working.
- No privileged secret reaches the browser.
- All large collections are bounded and indexed.
- Heavy work uses ARQ workers.
- Realtime is scoped and optional.
- External services use adapters.
- Webhooks are verified and deduplicated.
- Files are private, scanned, and permission checked.
- Logs are structured and redacted.
- Errors and jobs are observable.
- Migrations are deterministic and tested.
- Dummy seed data is isolated from production data.
- Optional integrations can be disconnected without breaking core CRM functions.
- Security, performance, and reliability rules in `CLAUDE.md` remain intact.

## 33. FINAL ARCHITECTURAL COMMAND

Build RKPR Restaurant CRM as a secure, high-speed modular monolith with a Next.js dashboard, FastAPI backend, independent ARQ worker, PostgreSQL source of truth (via psycopg 3), Supabase Auth and Storage, controlled realtime, Upstash Redis for appropriate ephemeral workloads, and provider adapters for external services. Keep business rules in the backend, large datasets bounded, heavy work asynchronous, permissions enforced server-side using the single canonical capability registry, files private, integrations honest, money stored as integer minor units, and every critical operation observable, auditable, and recoverable.
