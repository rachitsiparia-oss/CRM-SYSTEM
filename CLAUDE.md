# RKPR RESTAURANT CRM — MASTER CLAUDE INSTRUCTIONS

## 1. PURPOSE OF THIS FILE

This file is the highest-authority implementation instruction for the RKPR Restaurant CRM project. Claude must read this file before making architectural decisions, generating code, creating migrations, adding dependencies, modifying shared components, changing security behavior, or declaring any task complete.

When another project document provides module-specific detail, that document extends this file. It does not override the non-negotiable rules in this file unless the user explicitly approves the change. When requirements conflict, Claude must stop the conflicting implementation, identify the exact conflict, preserve existing working behavior, and follow the most recent explicit user decision.

The objective is to build a production-grade, private CRM for RKPR Fast-Food Restaurant. This is not a generic CRM template, marketplace product, multi-tenant SaaS, no-code builder, demo dashboard, or temporary prototype. The software must be designed specifically for RKPR and must remain maintainable, secure, fast, reliable, auditable, and extensible.

### 1.1 Document authority order

When documents appear to disagree, resolve the conflict using this exact order, highest first:

1. `/CLAUDE.md` — this file. Highest-authority engineering and implementation rules.
2. The domain-specific document authoritative for the affected area (for example, `docs/DATABASE_AND_API.md` for schema/API questions, `docs/CORE_CRM_MODULES.md` for core-module product behavior).
3. `/docs/PROJECT_PLAN.md` — business scope and detailed functional scope.
4. `/docs/ARCHITECTURE_AND_TECH_STACK.md` — system architecture and repository structure.
5. `/docs/TOOLS.md` — approved technologies and exact tool choices.
6. `/docs/DEPLOYMENT_AND_ENV.md` — environments and deployment behavior.
7. `/ROADMAP.md` — canonical implementation sequence and phase status tracker. `ROADMAP.md` is the **single** source of phase numbering; no other document may define a different phase sequence.

No document may instruct Claude to follow a conflicting phase numbering system or a conflicting technology choice. If a genuine contradiction is found that this order cannot resolve, stop, quote both statements, and ask before proceeding.

## 2. PROJECT IDENTITY AND BOUNDARIES

Project name: RKPR Restaurant CRM.

Business type: Fast-food restaurant serving items such as burgers, pizzas, tacos, burritos, sides, beverages, desserts, combos, add-ons, and future categories.

Primary system purpose: Unify customer management, leads, online order visibility, menu and inventory operations, reservations, communications, staff administration, marketing, loyalty, feedback, reporting, integrations, security, and restaurant settings inside one private operational dashboard.

The CRM contains exactly these twelve user-facing sections:

1. Dashboard
2. Customers
3. Leads
4. Orders & Restaurant Operations
5. Menu, Products & Inventory
6. Reservations & Calendar
7. Communication Hub
8. Lightweight Knowledge Base
9. Staff & HR
10. Marketing, Loyalty & Feedback
11. Reports, Analytics & AI Center
12. Integrations, Security & Settings

Backend automations are not a separate dashboard section. They are implemented as internal services, jobs, event handlers, schedulers, and integration workflows. Users see their results inside the relevant module.

Do not add an Automation Builder, Workflow Builder, Theme Builder, generic Customization section, public plugin marketplace, multi-business tenant selector, generic white-label controls, or unnecessary administration surfaces.

The Knowledge Base is intentionally lightweight. It may support folders, metadata, permissions, versioning, safe uploads, previews, and standard keyword or PostgreSQL full-text search. It must not introduce embeddings, vector search, chunking, semantic retrieval, pgvector, or RAG unless the user later explicitly changes this decision.

Offline order fulfilment remains the responsibility of the restaurant POS. Do not rebuild duplicate offline kitchen or fulfilment logic inside the CRM. Synchronize only useful offline data when a permitted POS API, export, or approved integration is available.

## 3. REQUIRED WORKING BEHAVIOR FOR CLAUDE

Claude must act as a senior software architect and production engineer, not as a code generator that optimizes only for speed of output.

Before modifying code, Claude must:

- Read this file and all directly relevant module documents.
- Inspect the current repository structure and existing implementation.
- Identify existing conventions before creating new patterns.
- Trace affected frontend, backend, database, worker, realtime, integration, and test paths.
- Check whether the requested feature already partially exists.
- Avoid duplicating utilities, models, schemas, components, hooks, services, enums, permissions, or configuration.
- Determine migration, compatibility, security, performance, and rollback effects.
- Preserve unrelated working behavior.

Claude must not guess repository contents, database columns, environment variables, API contracts, permissions, third-party capabilities, or deployment state. Inspect first. When external credentials or services are unavailable, implement validated placeholders, adapters, mocks, interfaces, and clear configuration errors without pretending the integration is active.

Claude must not silently reduce requirements to finish faster. A feature is incomplete when critical validation, permissions, error states, loading states, audit behavior, tests, migrations, or operational handling are missing.

Do not make broad destructive rewrites unless necessary and explicitly justified. Prefer focused, reviewable changes. Do not delete working functionality merely because a different implementation is easier.

When completing a task, Claude must report:

- What changed.
- Important files created or modified.
- Database migrations added.
- Environment variables added or changed.
- Tests executed and their results.
- Build, type-check, lint, migration, and validation results.
- Known limitations, placeholders, or unresolved integration dependencies.
- Any security or performance implications.

Never claim that a task is complete when verification was skipped or failed.

## 4. NON-NEGOTIABLE QUALITY PRINCIPLES

The following priorities apply to every feature:

1. Correctness.
2. Security.
3. Data integrity.
4. Performance.
5. Reliability.
6. Maintainability.
7. Observability.
8. Accessibility and usability.
9. Visual polish.
10. Delivery speed.

Delivery speed must never be used to justify weak authorization, unsafe data access, missing validation, unbounded queries, duplicated logic, blocking heavy work, insecure file handling, missing error recovery, or untested critical paths.

Do not use temporary hacks in production paths. Temporary implementation scaffolding must be clearly isolated, documented, disabled by default where appropriate, and removable without architectural damage.

## 5. PERFORMANCE IS A FIRST-CLASS REQUIREMENT

The previous dashboard experience was slow. This project must not repeat that failure. Performance must be designed into every module from the first implementation rather than added as an afterthought.

Claude must assume the system will accumulate large and continuously growing datasets, including customers, leads, orders, order items, messages, reservations, stock movements, audit events, notifications, campaign records, staff events, feedback, reports, and uploaded files.

### 5.1 Frontend performance rules

- Never fetch an entire large table to the browser.
- Use server-side pagination, filtering, search, and sorting.
- Use cursor pagination for feeds, messages, activity logs, notifications, and high-volume continuously changing data when offset pagination would become inefficient or inconsistent.
- Use virtualized rendering for long tables, timelines, dropdowns, lists, and message histories where appropriate.
- Use code splitting and route-level lazy loading.
- Keep initial dashboard bundles small.
- Avoid importing large libraries into shared client bundles when smaller or server-side alternatives exist.
- Prefer server components for non-interactive data presentation where appropriate and safe.
- Keep client components narrowly scoped.
- Prevent unnecessary rerenders through stable props, selectors, memoization only where measured or structurally useful, and local state isolation.
- Do not store large server datasets in global client state.
- Use TanStack Query for server-state caching, invalidation, retries, request deduplication, and background refetch behavior.
- Cancel stale requests when filters, searches, pages, or routes change.
- Debounce high-frequency searches and filters.
- Use skeletons for meaningful loading states rather than blocking full-screen spinners.
- Use optimistic updates only when conflicts and rollback behavior are safely handled.
- Keep charts bounded by date ranges and aggregation endpoints. Never send raw massive datasets to the chart library.
- Do not render hidden tabs, modals, or complex panels before they are needed.
- Avoid expensive synchronous transformation of large datasets in render functions.
- Keep images optimized, appropriately sized, lazily loaded, and served through secure storage URLs.

### 5.2 Backend performance rules

- Every collection endpoint must have bounded pagination.
- Enforce maximum page sizes server-side.
- Filter, sort, aggregate, and paginate in the database rather than loading rows into application memory.
- Select only required columns.
- Avoid N+1 queries.
- Use eager loading intentionally and only for bounded relationships.
- Use database-side aggregation for dashboard metrics and reports.
- Use bulk operations for imports, updates, and message or campaign processing.
- Use background workers (ARQ, per `docs/TOOLS.md`) for reports, exports, emails, campaigns, file processing, AI tasks, large imports, and retryable integration work.
- Do not block API requests while generating PDFs, processing large files, sending bulk communications, or waiting on slow third-party APIs.
- Use timeouts for every external network call.
- Use retries only for retryable errors, with exponential backoff, jitter, attempt limits, idempotency, and dead-letter handling.
- Implement request and job idempotency where duplicate execution could create duplicate orders, messages, reservations, stock movements, rewards, notifications, or reports.
- Use connection pooling and do not open uncontrolled database connections.
- Use Redis only for suitable ephemeral state, rate limiting, locks, cache entries, job coordination, and carefully designed counters. PostgreSQL remains the source of truth for durable business data.
- Define cache invalidation explicitly. Never cache sensitive or permission-dependent data without correct key scoping and expiration.
- Use asynchronous I/O correctly. Do not call blocking libraries directly inside async request handlers.
- Apply bounded concurrency when processing batches.
- Use streaming or chunked processing for large exports and imports where appropriate.

### 5.3 Database performance rules

- Add indexes based on real query patterns, not indiscriminately.
- Every foreign key used in joins or common filters must be evaluated for indexing.
- Add composite indexes for common filter and sort combinations.
- Add partial indexes where they materially improve active-record queries.
- Avoid functions or transformations on indexed filter columns that prevent index use.
- Use appropriate data types and constraints.
- Avoid unbounded JSON blobs for core searchable or relational business data.
- Keep immutable histories append-oriented where practical.
- Use summary or aggregate tables only when justified and keep them transactionally or asynchronously consistent through explicit mechanisms.
- Prevent table scans on frequently used dashboard, search, status, assignment, date-range, and unread-count queries.
- Review query plans for slow or high-volume queries.
- Avoid offset pagination for very deep pages on high-volume tables when cursor pagination is more suitable.
- Archive or partition very high-volume event data only when evidence requires it; do not prematurely complicate the schema.

### 5.4 Realtime performance rules

- Realtime is for genuinely live business events, not for every database row and every page.
- Subscribe only to scoped channels needed by the current user and active screen.
- Unsubscribe on route, account, permission, and component changes.
- Do not create one database subscription per visible row.
- Prefer domain events or controlled broadcasts for high-level changes.
- Reconcile realtime events with authoritative API data.
- Handle reconnects, missed events, duplicate events, out-of-order delivery, and stale local caches.
- Realtime updates must not bypass authorization.

### 5.5 Performance acceptance behavior

Every module must include realistic loading, empty, error, and large-data states. Slow endpoints must be observable. Expensive endpoints must be measured. Performance regressions must not be hidden by longer timeouts or larger loading spinners.

Claude must not state that performance is guaranteed. Claude must build the system using scalable patterns and verify speed through available local and automated measurements at the appropriate stage.

## 6. SECURITY IS NON-NEGOTIABLE

Security must never be traded for convenience, design speed, or frontend simplicity.

### 6.1 Authentication and session security

- Use Supabase Auth as the approved authentication provider.
- Use secure, HTTP-only, SameSite cookies for web sessions where the architecture supports them.
- Never expose service-role keys, private API keys, database passwords, signing secrets, or backend credentials to the browser.
- Validate tokens server-side.
- Implement session expiration, refresh behavior, logout, revocation, and device or session visibility where specified.
- Require MFA for owner and high-privilege accounts when production configuration is enabled.
- Protect authentication endpoints against brute force, credential stuffing, enumeration, and abuse.
- Do not reveal whether an account exists through inconsistent public error messages.

### 6.2 Authorization

- Authorization must be enforced on the backend for every protected operation.
- Hiding a navigation item or disabling a button is not authorization.
- Use least-privilege role and department permissions.
- Use the single canonical capability registry defined in `docs/DATABASE_AND_API.md` (lowercase, dot-separated, domain first, action or sub-action after — for example `orders.refund.approve`, `customers.merge`). Do not invent synonym permission codes elsewhere.
- Verify both action permission and record scope.
- Recheck permissions for websocket, realtime, background job, export, file, report, integration, and AI operations.
- Prevent insecure direct object reference attacks by validating access to every referenced record.
- Do not trust role names, user IDs, restaurant IDs, record ownership, prices, totals, statuses, or permissions supplied by the browser.
- Use centralized permission helpers or policy services rather than scattered ad hoc checks.
- Record sensitive permission and role changes in immutable audit logs.

### 6.3 Input and output safety

- Validate all request bodies, query parameters, path parameters, headers, uploaded files, webhook payloads, and integration responses.
- Use Pydantic and Zod as approved validation libraries.
- Reject unknown or forbidden fields where appropriate.
- Normalize phone numbers, email addresses, dates, times, currencies, quantities, and identifiers consistently.
- Use parameterized queries and ORM-safe patterns.
- Escape or sanitize untrusted rich text before display.
- Prevent stored and reflected XSS.
- Configure CSRF protection where cookie-based mutation requests require it.
- Configure CORS narrowly by environment.
- Use safe redirect allowlists.
- Do not expose stack traces, SQL errors, secrets, tokens, or internal paths to users.

### 6.4 File security

- Allow only explicitly approved file types and extensions.
- Verify MIME type and file signatures; do not trust filenames alone.
- Enforce size limits.
- Generate server-controlled storage paths and filenames.
- Scan uploads for malware using the approved scanning pipeline.
- Store files privately by default.
- Use short-lived signed URLs for authorized access.
- Verify permission before generating every signed URL.
- Prevent path traversal, executable upload, HTML upload abuse, decompression bombs, and unsafe document processing.
- Process files in isolated background jobs when appropriate.
- Never expose raw storage service credentials.

### 6.5 Secrets, infrastructure, and logging

- Keep secrets in environment or managed secret stores, never in source control.
- Provide placeholders in examples.
- Validate required environment variables at application startup.
- Separate development, preview, staging if used, and production configuration.
- Redact secrets, tokens, passwords, authorization headers, payment data, and sensitive personal data from logs.
- Use structured logs with correlation IDs.
- Apply rate limits to sensitive, public, integration, export, communication, and AI endpoints.
- Verify webhook signatures and replay protection.
- Use encrypted transport for all production traffic.
- Maintain automated backups and documented restore procedures.
- Do not declare backups valid without restoration verification at the proper operational stage.

### 6.6 Auditability

Sensitive changes must produce audit records with actor, action, target type, target identifier, timestamp, source, request or correlation identifier, relevant safe metadata, and before/after summaries where appropriate. Audit logs must not store secrets or unnecessary sensitive payloads.

At minimum, audit authentication security events, role and permission changes, staff record access where appropriate, customer merges, destructive actions, order status overrides, reservation decisions, inventory adjustments, pricing changes, refunds, campaign launches, integration changes, report-recipient changes, file access or deletion when sensitive, and AI actions that affect business records.

## 7. DATA INTEGRITY AND BUSINESS RULES

PostgreSQL is the source of truth for durable CRM data. Redis, browser state, and realtime messages must not become the only copy of business-critical information.

- Use database constraints for invariants whenever possible.
- Use foreign keys for valid relationships.
- Use transactions for multi-step business operations.
- Lock or serialize operations where concurrent updates could corrupt stock, status transitions, assignments, loyalty balances, reservation capacity, or duplicate processing.
- Use explicit state-transition rules. Do not permit arbitrary status changes.
- Preserve status history for orders, reservations, leads, complaints, jobs, and other operational workflows.
- Use soft deletion for records that require historical retention, auditability, restoration, or relationship preservation.
- Hard deletion requires explicit business justification and permission.
- Every durable table should use consistent identifiers, created timestamps, updated timestamps, and actor or audit fields where meaningful.
- Store timestamps in UTC and convert for display using the configured restaurant timezone (`Asia/Kolkata`).
- **Money is final and non-negotiable: every monetary value is stored as an integer minor unit in a PostgreSQL `BIGINT` column, using field names ending in `_minor`** (for example `price_minor`, `subtotal_minor`, `tax_minor`, `discount_minor`, `total_minor`, `refund_minor`, `amount_minor`). Never use binary floating-point, and never use `NUMERIC(14,2)` as an alternative — that is not an open decision. API payloads use the same integer minor units for authoritative monetary values; the frontend may format rupees and paise for display but is never the calculation authority. Rounding rules are deterministic and backend-owned.
- Compute authoritative totals on the backend.
- Prevent duplicate customers, leads, reservations, orders, messages, stock events, and webhook effects using normalized identifiers, unique constraints, idempotency, or controlled merge workflows.
- Never silently overwrite conflicting data.
- Imports must support validation, preview, rejection reporting, and transactional or resumable processing.

## 8. ARCHITECTURE RULES

Use a clear monorepo architecture unless the approved architecture document specifies otherwise.

Expected high-level shape:

- `apps/dashboard`: Next.js CRM dashboard.
- `apps/api`: FastAPI backend and authoritative business API.
- `apps/worker`: background job and scheduled automation process (ARQ).
- `packages/ui`: shared design-system components.
- `packages/contracts`: shared generated or maintained types and contracts.
- `packages/config`: shared non-secret configuration.
- `packages/api-client`: typed API client where justified. (Do not use the name `packages/sdk` — this package is always named `packages/api-client`.)
- `infrastructure`: deployment, monitoring, and environment support. Docker is intentionally deferred to a later phase; its absence in early phases is expected, not a defect.
- `docs`: project specifications and implementation guidance.
- `tests`: integration, end-to-end, security, and load-related test assets where appropriate.

Do not create circular dependencies between applications and packages. Shared packages must remain domain-appropriate and must not become uncontrolled dumping grounds.

Business logic belongs in backend domain or application services, not React components, route handlers, database models, or random utility files.

Keep clear boundaries between:

- Domain models and business rules.
- API schemas and transport contracts.
- Database persistence models.
- Integration adapters.
- Background jobs.
- Realtime event publishing.
- Frontend server state.
- Frontend presentation state.

Third-party services must be accessed through adapters or service interfaces so they can be tested, replaced, disabled, and configured safely.

Do not directly call third-party services from frontend code when doing so requires secrets, authoritative validation, protected business data, or reliable retries.

## 9. APPROVED TECHNOLOGY DIRECTION

The exact locked stack, versions, and tool responsibilities are defined in `docs/TOOLS.md` and `docs/ARCHITECTURE_AND_TECH_STACK.md`. Summary:

Frontend: Next.js, React, TypeScript strict mode, Tailwind CSS, shadcn/ui and Radix primitives, TanStack Query, TanStack Table, TanStack Virtual where needed, React Hook Form with Zod, Zustand only for narrow client state, Apache ECharts, Lucide icons. Package manager: pnpm (via Corepack).

Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, psycopg 3, HTTPX, structlog, Ruff, mypy. Python dependency manager: uv.

Background jobs: ARQ (Redis-backed), running as the separate `apps/worker` Railway service.

Data and infrastructure: PostgreSQL through a dedicated Supabase project for RKPR, Supabase Auth, Supabase Storage, controlled Supabase Realtime, Upstash Redis, Railway for backend and worker deployment, Vercel for dashboard deployment, GitHub and GitHub Actions, Sentry.

Do not add dependencies without checking whether the capability already exists, whether the dependency is maintained, bundle or runtime cost, security history, license suitability, and compatibility with the current stack.

Pin or lock dependencies through the project package managers (`pnpm-lock.yaml`, `uv.lock`). Do not use unreviewed floating production versions.

## 10. FRONTEND ENGINEERING STANDARDS

- TypeScript strict mode must remain enabled.
- Avoid `any`. When unavoidable at an external boundary, isolate and validate it immediately.
- Use typed API contracts.
- Do not duplicate backend enums manually without a controlled synchronization mechanism.
- Build reusable primitives, but do not overabstract one-off UI.
- Keep route components thin.
- Separate data access, state, transformation, permission logic, and presentation.
- Use semantic HTML and accessible components.
- Support keyboard navigation, visible focus, labels, descriptions, screen-reader announcements, and adequate contrast.
- Every action must have clear loading, success, failure, and disabled states.
- Prevent double submission.
- Confirm dangerous or irreversible actions.
- Preserve user filters and table state where useful, but do not persist sensitive data insecurely.
- Use responsive layouts suitable for desktop operational use and usable smaller screens.
- Keep visual language consistent across all twelve modules.
- Avoid excessive animation. Motion must support clarity and must not make operational workflows slower.
- Do not sacrifice performance for decorative effects.
- Use error boundaries and route-level error handling.
- Do not show raw backend error messages directly to users.

## 11. BACKEND ENGINEERING STANDARDS

- Use explicit service and repository boundaries where they improve clarity and testability.
- Keep request handlers focused on authentication, authorization, validation, orchestration, and response construction.
- Keep domain rules outside controllers.
- Use typed Pydantic request and response schemas.
- Use consistent response and error conventions.
- Return appropriate HTTP status codes.
- Implement pagination metadata or cursors consistently.
- Apply authorization before accessing or mutating protected records.
- Use transactions for operations that must succeed or fail together.
- Use explicit timeout and cancellation behavior.
- Design jobs to be idempotent.
- Do not catch broad exceptions without logging and appropriate rethrow or error conversion.
- Do not silently ignore failed writes, integration errors, or background tasks.
- Avoid global mutable state.
- Keep startup and shutdown behavior safe.
- Validate configuration before serving traffic.
- Keep API documentation accurate.
- Version public or integration-facing API contracts when breaking changes are possible.

## 12. DATABASE AND MIGRATION RULES

- Every schema change must use an Alembic migration and any required Supabase SQL policy migration process.
- Never modify production schema manually as the normal workflow.
- Migrations must be deterministic, reviewable, and safe.
- Avoid destructive migration operations without explicit migration strategy, backup awareness, data conversion, and rollback or forward-recovery plan.
- Backfill data in controlled batches when tables may be large.
- Add non-null constraints safely by backfilling and validating first.
- Review lock impact for indexes and schema changes.
- Use unique constraints for real uniqueness guarantees.
- Use check constraints for valid values when appropriate.
- Keep enum and status changes backward-compatible during rolling deployments where relevant.
- Seed data must be explicit, idempotent, environment-aware, and must not create fake production records.
- Test migrations from a clean database and from the latest previous schema state.
- Do not squash meaningful production migration history without an approved plan.

## 13. API CONTRACT RULES

Every endpoint must define:

- Authentication requirement.
- Authorization and record scope.
- Request schema.
- Response schema.
- Validation rules.
- Pagination and maximum limits.
- Filter and sort allowlists.
- Error behavior.
- Audit behavior where applicable.
- Idempotency requirements where applicable.
- Rate-limit classification.
- Performance expectations.

Do not accept arbitrary sort columns, raw SQL filters, unrestricted include parameters, or unbounded date ranges.

Search endpoints must normalize inputs, use indexed strategies where possible, enforce minimum or maximum lengths where appropriate, and prevent expensive wildcard abuse.

Exports must be permission checked, bounded or background generated, securely stored, expiring, and audited when sensitive.

## 14. BACKGROUND JOB AND AUTOMATION RULES

Backend automations must be implemented as explicit jobs, events, and services using ARQ, running in the separate `apps/worker` process. They must not depend on a user keeping a browser open.

Every job must define:

- Trigger.
- Inputs.
- Permission or system authority.
- Idempotency key strategy.
- Retry classification.
- Maximum attempts.
- Timeout.
- Failure state.
- Dead-letter or manual recovery path.
- Audit and structured logs.
- User-visible status where useful.
- Metrics.

Expected automations include order notifications, order status messages, late-order alerts, reservation notifications, human-approved reservation confirmations, reminders, lead assignment or follow-up scheduling, customer conversion merging, stock alerts, controlled menu availability changes, feedback requests, loyalty updates, complaint creation, scheduled reports, and integration failure alerts.

Do not send external communication inside an uncommitted database transaction. Use an outbox or equivalent reliable event pattern for critical side effects where necessary.

## 15. REALTIME AND NOTIFICATION RULES

Realtime events must use stable event names, versions, identifiers, timestamps, actor information where safe, and minimal payloads. Sensitive records should be refetched through authorized APIs rather than broadcast in full.

Notifications must be durable when they represent operational work. Support read, unread, seen, actioned, dismissed, or archived states as appropriate. Avoid generating duplicate notifications for repeated events.

Critical notifications must have escalation or fallback behavior where specified. Notification delivery failure must not corrupt the underlying business action.

## 16. INTEGRATION RULES

Integrations may include the restaurant website, POS data, WhatsApp Cloud API, email, SMS, Google Calendar, payment status, delivery platforms, printer or kitchen display systems, webhooks, and future approved services.

- Use official, permitted APIs or approved imports only.
- Do not scrape or reverse-engineer restricted platforms.
- Do not claim Zomato, Swiggy, POS, or any service integration is available without verified API or export capability.
- Implement integrations behind adapters.
- Store external identifiers and synchronization metadata safely.
- Verify webhook signatures.
- Deduplicate webhook events.
- Support retry, reconciliation, and failure visibility.
- Avoid making the availability of a third-party service a requirement for core dashboard navigation.
- Provide clear disabled, disconnected, degraded, and error states.
- Never hardcode external credentials.

## 17. AI FEATURE RULES

AI is optional and controlled. It may summarize structured CRM data, draft replies, explain trends, flag anomalies, and prepare management summaries.

AI must not:

- Bypass permissions.
- Access records the requesting user cannot access.
- Directly perform sensitive actions without validation and required confirmation.
- Invent business facts.
- Generate authoritative financial, inventory, reservation, staff, or customer decisions without deterministic verification.
- Replace database queries with guessed answers.
- Introduce RAG into the lightweight Knowledge Base.

Use provider abstraction, structured outputs, validation, usage tracking, cost controls, timeouts, retries where safe, audit logs, and redaction of unnecessary sensitive data.

Sensitive actions proposed by AI require human confirmation unless the user explicitly approves a deterministic automation.

AI credentials and integration are not created during the foundation phase; they are introduced only when the roadmap explicitly reaches the controlled-AI phase (Phase 14).

## 18. TESTING REQUIREMENTS

Testing is part of implementation, not optional cleanup.

Use appropriate layers:

- Unit tests for domain rules, validation, transformation, permission helpers, and utilities.
- Database tests for constraints, migrations, queries, transactions, and concurrency-sensitive operations.
- API integration tests for authentication, authorization, validation, pagination, filters, state transitions, idempotency, and errors.
- Worker tests for retries, duplicate execution, failures, timeouts, and side effects.
- Frontend component tests for critical interaction and permission behavior.
- End-to-end tests for the most important owner, manager, kitchen, reservation, support, marketing, and inventory workflows.
- Security tests for broken access control, unsafe input, file uploads, webhook validation, rate limits, and sensitive-data exposure.
- Performance-oriented tests for critical queries, tables, feeds, dashboard aggregation, and high-volume paths when appropriate (k6 for load testing).

Every bug fix should include a regression test when technically practical.

Do not weaken or delete tests merely to make a build pass. Fix the product or update tests only when requirements intentionally changed.

## 19. OBSERVABILITY AND ERROR HANDLING

- Use structured logs (structlog).
- Include correlation or request IDs.
- Track background job IDs.
- Use consistent severity levels.
- Report exceptions to Sentry with sensitive data removed.
- Add metrics for request latency, error rate, job duration, queue depth, retry count, integration health, database pressure, cache behavior, and realtime failures where supported.
- Use health and readiness endpoints.
- Health endpoints must not expose secrets or sensitive internal details.
- Distinguish expected user errors, validation errors, permission failures, conflicts, dependency failures, and unexpected internal errors.
- Provide actionable operator information without exposing internals to end users.
- Integration and worker failures must be visible in the relevant admin or system-health surfaces.

## 20. CODE STYLE AND REPOSITORY HYGIENE

- Follow existing formatter, linter, and import rules (Ruff and mypy for Python; ESLint and strict TypeScript for the frontend).
- Use descriptive names.
- Avoid ambiguous abbreviations.
- Keep functions and modules focused.
- Remove dead code and unused imports created by the change.
- Do not leave commented-out implementation blocks.
- Do not commit secrets, generated credentials, local database files, build outputs, or temporary exports.
- Keep `.env.example` complete with placeholders and descriptions, but never real values.
- Update documentation with architecture or contract changes.
- Use conventional, focused commits when requested.
- Do not reformat unrelated files without reason.
- Do not introduce a second framework or competing architecture for the same concern.

Comments should explain why, constraints, invariants, or unusual behavior. Do not write comments that merely restate obvious code.

## 21. ENVIRONMENT AND PLACEHOLDER RULES

Development must be possible before all production credentials are available.

- Use clearly named placeholders.
- Provide startup validation with helpful errors.
- Allow optional integrations to remain disabled without crashing unrelated modules.
- Do not generate fake success for disconnected services.
- Use local or test adapters where useful.
- Separate required core variables from optional integration variables.
- Keep client-exposed environment variables explicitly allowlisted and free of secrets.
- Document purpose, format, required status, environment scope, and rotation considerations for every variable.

## 22. UI AND PRODUCT BEHAVIOR

The CRM must feel fast, professional, and operationally clear.

- Prefer information density with strong hierarchy over oversized decorative layouts.
- Keep common actions visible and predictable.
- Preserve filters and context when users inspect a record and return.
- Provide searchable, filterable, sortable tables with sensible defaults.
- Display timestamps, statuses, assignment, source, and ownership consistently.
- Show status histories for operational records.
- Use badges and colors consistently, but never rely on color alone.
- Prevent users from performing invalid state transitions.
- Explain why an action is unavailable when appropriate.
- Ensure notifications link to the correct record and context.
- Avoid hidden destructive actions.
- Keep role-specific dashboards useful without creating separate applications.
- Use real data and APIs in production paths; do not leave hardcoded dashboard metrics.

## 23. MODULE-SPECIFIC PERMANENT DECISIONS

- Leads are a dedicated section.
- Lead sources include website, offline, Zomato, Swiggy, and marketing campaigns.
- Conversion from lead to customer must preserve complete lead history and merge duplicates safely.
- Online orders require detailed status tracking.
- Offline POS fulfilment must not be duplicated.
- Menu availability may react to required ingredient availability through controlled rules.
- Inventory changes require history and auditability.
- Reservations require staff approval before WhatsApp confirmation.
- Every new reservation should create an operational notification.
- Human handoff is not presented as a separate Communication Hub feature; assigned staff work directly in conversations.
- Knowledge Base remains lightweight and does not use RAG.
- Marketing campaigns may use WhatsApp, email, or SMS where consent and integrations allow.
- Meta and Google advertising remain managed in their native platforms; CRM receives or attributes approved lead and campaign data.
- Reports must support attractive visual summaries and daily, weekly, and monthly delivery.
- Report-recipient addresses belong in Settings and must not be hardcoded.
- The canonical dummy active-staff total is 65 (see `docs/PROJECT_PLAN.md` §4).
- Security and performance requirements apply to every phase.

## 24. FORBIDDEN SHORTCUTS

Claude must not:

- Use frontend-only permissions.
- Use hardcoded production secrets.
- Use service-role credentials in the browser.
- Fetch whole large tables.
- Add endpoints without pagination for growing datasets.
- Use unbounded realtime subscriptions.
- Run heavy reports in normal request handlers.
- Store authoritative business data only in Redis or browser state.
- Use floating point for money, or use `NUMERIC(14,2)` as an alternative to integer minor units.
- Trust client-calculated totals or permissions.
- Allow arbitrary status transitions.
- Skip audit logs for sensitive operations.
- Allow public file buckets by default.
- Trust upload extensions or MIME headers alone.
- Swallow errors silently.
- Add broad `except Exception` blocks without correct handling.
- Disable strict typing to avoid fixing errors.
- Add `any` across major code paths.
- Duplicate models, enums, schemas, or components.
- Invent permission codes outside the single canonical registry.
- Use the package name `packages/sdk` (always `packages/api-client`).
- Create fake integrations or placeholder data that appears production-ready.
- Scrape restricted delivery platforms.
- Introduce RAG, embeddings, or vector search into the Knowledge Base.
- Introduce multi-tenancy, `tenant_id` fields, or generic CRM customization without explicit approval.
- Introduce n8n or Temporal.
- Redesign unrelated modules during a focused task.
- Mark incomplete features as complete.
- Mark a roadmap phase `COMPLETED` when required tests or acceptance criteria remain unfinished.

## 25. REQUIRED VERIFICATION BEFORE COMPLETION

Before declaring a coding task complete, Claude must run the checks relevant to the change, including:

- Formatter (Ruff / ESLint-Prettier equivalent).
- Linter.
- Type checker (mypy / strict TypeScript).
- Unit tests.
- Integration tests.
- Frontend tests.
- End-to-end tests when the workflow is critical.
- Production build.
- Database migration upgrade and downgrade or forward-recovery validation where applicable.
- Clean-database migration validation.
- API schema or client-generation checks where applicable.
- Permission checks for every affected role.
- Query and pagination review for data-heavy changes.
- Security review for authentication, authorization, uploads, webhooks, exports, integrations, and sensitive data.
- Error, empty, loading, disconnected, and retry-state review.

When a check cannot run because of missing credentials or unavailable infrastructure, Claude must state exactly what was not tested, why, what substitute validation was completed, and what remains required.

## 26. DEFINITION OF A COMPLETE FEATURE

A feature is complete only when all applicable parts exist and work together:

- Database model and constraints.
- Migration.
- Backend domain rules.
- API schemas and endpoints.
- Authentication and authorization.
- Validation.
- Audit behavior.
- Error and conflict behavior.
- Background jobs or realtime events where needed.
- Frontend interface.
- Loading, empty, error, success, and permission states.
- Responsive and accessible behavior.
- Tests.
- Logging and monitoring hooks.
- Documentation and environment updates.
- Verification results.

A visually complete page backed by mock data is not a completed CRM module.

## 27. CHANGE CONTROL

Record significant decisions in the project decisions document when created. Significant decisions include stack changes, schema strategy, permission model changes, status workflow changes, integration assumptions, deployment changes, security changes, performance tradeoffs, and removed or deferred scope.

Do not reopen settled decisions (phase numbering, money representation, permission naming convention, `packages/api-client` naming, or the locked tooling choices in `docs/TOOLS.md`) without new evidence or an explicit user request.

When a change affects multiple documents, update all affected documentation so Claude does not receive conflicting instructions later.

## 28. FINAL COMMAND TO CLAUDE

Build RKPR Restaurant CRM as a secure, high-speed, production-grade operational system. Preserve data integrity. Enforce backend authorization. Keep large datasets bounded and indexed. Move heavy work to reliable background jobs. Use realtime only where it creates real operational value. Do not compromise security or performance for rapid output. Do not invent integrations. Do not hide incomplete work. Verify every meaningful change before declaring completion.
