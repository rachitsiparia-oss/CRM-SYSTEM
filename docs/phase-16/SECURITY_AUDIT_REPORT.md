# Phase 16 — Security Audit Report

Status: in progress — appended to as each Phase 16 security task completes. Finalized at Phase
16 completion (task #304).

## Findings and fixes

### 1. No security response headers (CSP, HSTS, X-Frame-Options, etc.)

- **Severity**: Medium (defense-in-depth — this API is pure JSON, so browser enforcement against
  the API's own responses is limited, but the interactive docs surface and general baseline
  hygiene both benefit).
- **Found**: no middleware set any of CSP, `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy`, or `Strict-Transport-Security` anywhere in the stack.
- **Fix**: `app/core/security_headers.py` (`SecurityHeadersMiddleware`), wired in
  `app/main.py::create_app()`. Strict `default-src 'none'` CSP on every response except the
  three interactive-docs paths (which get a CDN-scoped CSP and are themselves disabled outside
  `local`/`test`, so the relaxed policy never reaches staging/production). HSTS sent only when
  `environment` is `staging`/`production`.
- **Tests**: `apps/api/tests/test_health.py` — header presence/values, HSTS absence outside
  staging/production, docs-disabled-in-production.
- **Task**: #284.

### 2. Webhook provider fallback could accept unsigned requests (fail-open)

- **Severity**: High — a latent gap, not yet exploitable in the current deployed state (see
  below), but would silently accept forged inbound messages once triggered.
- **Found**: `app/communications/providers.py::get_provider()` falls back to
  `InternalMockProvider` for any provider name with no registered adapter —
  intentional and correct for *outbound sends* (CLAUDE.md §21: optional integrations degrade
  rather than crash). The webhook router entry points
  (`POST /communications/webhooks/{provider_name}/inbound` and `.../status`,
  `app/communications/router.py`) reused the same `get_provider()` call. `CommunicationChannel
  .provider` is free text with no allowlist (`schemas.py`'s `CommunicationChannelUpdateIn
  .provider: str | None`). `InternalMockProvider.validate_webhook_signature()` unconditionally
  returns `True` (correct for the mock — there is no real external signature to check for a
  provider that makes no network calls). Chained together: a channel created with e.g.
  `provider="whatsapp"` before a real WhatsApp adapter is registered would resolve its inbound
  webhook to the mock adapter, whose signature check always passes — any unauthenticated caller
  could then post arbitrary payloads and have them accepted as genuine messages on that channel.
  Not currently exploitable: every seeded `CommunicationChannel` row has `provider=
  "internal_mock"` regardless of its `code` (`app/communications/seed.py`), so today's only
  reachable webhook path is `/webhooks/internal_mock/inbound`, which is the mock provider
  legitimately. The gap would only activate the first time a channel is repointed at an
  unregistered provider name — exactly the state the system will be in the moment a real
  provider integration starts being configured, before its adapter code ships.
- **Fix**: added `get_registered_provider(name) -> ProviderAdapter | None` (strict lookup, no
  mock fallback) in `providers.py`. Both webhook router entry points now use it and return `503
  Service Unavailable` when the channel's declared provider has no registered adapter, instead of
  silently degrading to the always-accepting mock. `get_provider()` (with its fallback) is
  unchanged and still used for outbound sends, where "degrade to mock" remains correct.
- **Tests**: `apps/api/tests/test_communications_webhooks.py` —
  `test_get_registered_provider_has_no_mock_fallback`,
  `test_inbound_webhook_rejects_channel_with_unregistered_provider`.
- **Task**: #292.

### 3. Webhook idempotency and replay — reviewed, no gap found

- `process_inbound_webhook` / `process_status_webhook` (`app/communications/webhooks.py`) dedupe
  on a unique `(provider, provider_event_id)` constraint via `INSERT ... ON CONFLICT DO NOTHING`,
  returning the existing row on a duplicate delivery rather than reprocessing — correct
  at-least-once-delivery handling (CLAUDE.md §7/§14).
  `test_status_webhook_is_deduplicated_and_progresses_forward` additionally confirms an
  out-of-order stale status event (`sent` arriving after `delivered`) is ignored rather than
  regressing message state.
- Timestamp-window replay protection (rejecting a validly-signed but old/replayed request) is
  provider-signature-scheme-specific (Meta's `X-Hub-Signature-256` carries no timestamp; Twilio's
  `X-Twilio-Signature` scheme is different again) and cannot be meaningfully implemented against
  an abstract `ProviderAdapter` before a real provider is registered — deferred to whichever
  phase adds the first real provider adapter, consistent with CLAUDE.md §16 ("do not claim...
  integration is available without verified API").
- **Task**: #292.

### 4. No account lockout or progressive rate limiting for suspicious activity

- **Severity**: Medium — the API had a flat, per-window rate limiter (`app/core/rate_limit.py`)
  applied only to `POST /auth/*` and the general authenticated-request path, and no mechanism
  ever locked an account based on its own behavior.
- **Context**: this backend never receives a password — the browser talks to Supabase Auth
  directly (`app/core/rate_limit.py`'s own docstring), so classic failed-login brute-force
  lockout does not apply here; Supabase Auth is the credential-guessing control. What this layer
  *can* observe and act on is repeated authorization failures against its own permission system
  — a real signal of a compromised session or a script probing for access it doesn't have.
- **Fix, two parts**:
  1. **Progressive backoff** (`app/core/rate_limit.py::RateLimiter`) — a key that keeps
     violating its limit is now blocked for an exponentially growing penalty window
     (`window_seconds * 2**consecutive_violations`, capped at 1 hour) instead of getting a fresh
     attempt the instant the fixed window rolls over. The streak decays once a key completes a
     full window with no violation. Applies automatically to every existing `check_rate_limit()`
     call site (`auth:` per-IP limiter, `pwreset:` limiters) with no call-site changes.
  2. **Automatic account lock on repeated permission denials**
     (`app/permissions/dependencies.py::require_permission`) — 10 permission denials for the
     same staff account within 5 minutes flips `account_status` to `"locked"` (an existing,
     already-enforced status — `app.auth.dependencies.get_current_staff_user` already rejects
     it) and records an `auth.account_locked` audit event with the denied permission code and
     threshold. Reuses the same `check_rate_limit()` counter rather than a second bespoke one.
     Reversal is an existing admin capability (`PATCH /staff/{id}/status`,
     `app.staff.service.set_account_status`) — no new unlock mechanism was needed.
  3. A note on transaction semantics: the lock commits immediately inside the dependency
     (`await session.commit()`) rather than waiting for the request's normal commit, because the
     403 raised right after it would otherwise roll the whole request transaction back —
     silently undoing the very lock it was supposed to enact.
- **Tests**: `apps/api/tests/test_rate_limit.py` (backoff/decay unit tests),
  `apps/api/tests/test_permission_lockout.py` (end-to-end: 11 denials over HTTP lock the
  account, audit event recorded, 12th request rejected for being locked rather than merely
  denied).
- **Task**: #286.

### 5. Session/auth hardening — login history added; refresh rotation and device tracking intentionally not rebuilt

- **Context**: `app/auth/tokens.py` and `app/auth/router.py` already document a deliberate
  architectural choice — the browser talks to Supabase Auth directly for sign-in and token
  refresh; this backend only ever verifies short-lived access tokens statelessly
  (`ARCHITECTURE_AND_TECH_STACK.md` section 9.2/10.2, cited in `GET /auth/session`'s and
  `POST /auth/logout`'s own docstrings: "no separate sessions table is maintained; Supabase Auth
  owns session storage").
- **Refresh token rotation**: owned entirely by Supabase Auth's own refresh-token flow, which the
  frontend SDK calls directly. Nothing to add here without building a second, competing session
  store that duplicates a settled architectural decision — not done, consistent with CLAUDE.md
  §27 ("do not reopen settled decisions... without new evidence or an explicit user request").
- **JWT replay**: `app/auth/tokens.py::decode_access_token` already enforces signature validity,
  audience (`authenticated`), and required `exp`/`iat`/`sub` claims via PyJWT, which verifies
  `exp` by default — an expired or forged token is already rejected. A `jti`-based replay cache
  (rejecting a *valid, unexpired* token that's already been used once) would require durable
  server-side state that contradicts the stateless-verification design and would need Redis
  infrastructure — same category of change `app/core/rate_limit.py` already defers to Phase 17.
  Not built here; flagged as a Phase 17 candidate if full replay protection becomes a
  requirement.
- **Device/session tracking**: a "list of active devices/sessions" view would require a durable
  sessions table this backend deliberately does not maintain (see above) — building one now would
  silently reopen that decision rather than extend it. Not built.
- **Login history — built**: this *is* buildable without new session state, since
  `auth.login`/`auth.logout`/`auth.access_denied`/`auth.account_locked` are already recorded to
  `audit_events` with actor, timestamp, IP, and user agent. Added `GET /api/v1/auth/login-history`
  (`app/auth/router.py`, self-service — no permission code, scoped to the caller's own
  `target_id`, paginated via the existing offset-pagination primitive
  `app.core.pagination.PageParams`/`PaginatedResponse`, following the same precedent
  `app/notifications/router.py` already established for a per-user bounded list).
  `auth.password_reset_requested` is excluded — it's recorded with `target_id=None` by design
  (unauthenticated, enumeration-avoidance), so it can never be attributed to one account.
- **Tests**: `apps/api/tests/test_auth_api.py` —
  `test_login_history_lists_own_login_and_logout_events`,
  `test_login_history_never_returns_another_accounts_events`.
- **Task**: #285.

### 6. File-upload hardening — MIME/signature validation was already solid; the malware-scan hook was schema-only, now wired

- **Context, existing state (Phase 6/10/11)**: `app/storage/validation.py` (product images) and
  `app/knowledge/attachments.py::validate_attachment_upload` (PDF/DOCX/CSV/images, reused as-is
  by `app/staff_operations/documents.py`) already do real extension + declared-MIME +
  decoded-file-signature triple-checks (Pillow decode for images, `%PDF-` / `PK\x03\x04` magic
  bytes for PDF/DOCX, UTF-8 + no-null-byte check for CSV), a decompression-bomb guard on image
  pixel count, and — for images specifically — a full re-encode from decoded pixel data that
  strips EXIF/XMP/any non-pixel payload. Storage is private-by-default with signed URLs issued
  only after a backend permission check, and object paths are server-generated (no
  client-controlled path traversal). This was all already correct; nothing here needed fixing.
- **Found**: every `*_attachment`/`staff_document` DB model (`KnowledgeAttachment`,
  `StaffDocument`, and, for future upload flows that don't exist yet, `MessageAttachment`,
  `ComplaintAttachment`, `FeedbackAttachment`) already has a `scan_status` column
  (`pending`/`clean`/`infected`/`skipped`) — but no upload path ever set it. Every upload left it
  at its DB default of `"pending"` forever, which silently implies "a scan is in progress"
  indefinitely rather than being honest that no scan ever ran.
- **Fix**: added `app/storage/scanning.py` — a `MalwareScanner` adapter interface (mirroring the
  `ProviderAdapter` pattern from `app.communications.providers`) with one registered
  implementation, `NoOpScanner`, which honestly reports `scan_status="skipped"` rather than a
  fabricated `"clean"` (no scanning provider is approved anywhere in `docs/TOOLS.md` — CLAUDE.md
  §16). Wired into the two upload paths that currently exist end-to-end
  (`app.knowledge.attachments.upload_attachment`, reused by
  `app.staff_operations.documents.upload_document`): every upload now calls `scan_upload()`,
  persists whatever `scan_status` comes back, and — already future-proofed for when a real
  provider is registered — an `"infected"` result blocks the upload before it ever reaches
  storage. `ProductImage` (Phase 6) has no `scan_status` column at all and was left alone; adding
  one would require a new migration touching a settled Phase 6 schema, out of scope for a
  hardening pass, and its Pillow re-encode already strips the most common image-based payload
  vector.
  `MessageAttachment`/`ComplaintAttachment`/`FeedbackAttachment` have no upload service yet
  (only the DB models exist) — building those upload flows is new functionality, not hardening,
  so they were left as-is; `scan_upload()` is ready for whichever future task wires them up.
- **Tests**: `apps/api/tests/test_attachment_scanning.py` — a clean upload persists
  `scan_status="skipped"`; a forced `"infected"` result (monkeypatched scanner) returns 400 and
  no attachment row is created.
- **Task**: #287.

### 7. Secret redaction, audit-log enrichment, sensitive-field masking

- **Secret redaction — found**: `app/core/logging.py` enforced redaction purely through
  discipline ("only ever log explicit, named fields") with zero automated enforcement — no
  processor scrubbed values by key name, and a targeted grep confirmed no call site currently
  logs headers/tokens/passwords/secrets directly, but nothing would have caught it if one did.
  **Fix**: added `_redact_sensitive_fields`, a structlog processor run just before
  `JSONRenderer`, that replaces the value of any event-dict key whose name matches a marker list
  (`password`, `secret`, `token`, `authorization`, `api_key`, `credential`, `signing_key`,
  `service_role_key`, `signature`, `otp`, `card_number`, `cvv`, `ssn` — case-insensitive
  substring match) with `"[REDACTED]"`. This is defense-in-depth beneath the existing
  discipline, not a replacement for it.
- **Audit-log enrichment — found**: `GET /staff-operations/documents/{id}/signed-url` (grants
  read access to HR identity/employment documents — `StaffDocument`, explicitly sensitive PII)
  was permission-checked (`staff.documents.view`) but produced no audit trail, unlike every other
  action on that record (upload, verify). CLAUDE.md §6.6 explicitly requires auditing "file
  access... when sensitive." **Fix**: the endpoint now records a `staff.document_accessed` audit
  event (actor, target document, `staff_user_id` + `document_type` in `safe_metadata`) every time
  a signed URL is issued. The audit-event *shape* itself
  (`app/audit/service.py::record_audit_event` — actor, action, target type/id, timestamp, source,
  request/correlation id, safe metadata, before/after summaries) already covers every field
  §6.6 requires; the gap was a missing call site, not a missing field.
- **Sensitive-field masking — reviewed, already solid**: `StaffUser.phone_e164` is already
  withheld from API responses unless the viewer holds `staff.hr_sensitive.read` (pre-existing,
  confirmed by `tests/test_auth_api.py::test_hr_sensitive_field_hidden_without_permission`/
  `..._visible_with_permission`). Gift card codes (`app/gift_cards/security.py`) are never
  persisted in plaintext — only `code_hash` (Argon2/bcrypt via `app.core.hashing`) and
  `code_last4` are stored, with a `masked_display()` helper (`****-****-****-<last4>`) for
  anywhere the code needs to be shown after issuance. Both were reviewed and found correct;
  no changes made.
- **Tests**: `apps/api/tests/test_logging_redaction.py` (key-name matching, case-insensitivity,
  non-sensitive fields untouched), `apps/api/tests/test_staff_document_access_audit.py`
  (signed-url access is audited with the right actor/target/metadata; permission gate still
  enforced).
- **Task**: #288.

### 8. SQL injection, SSRF, command injection, HTML/Markdown sanitization — reviewed, no gaps found

A targeted static review, not a rebuild — every candidate site was read, not assumed clean.

- **SQL injection**: no application code builds SQL by string-formatting user input. Every
  query goes through SQLAlchemy ORM/Core (parameterized by construction). The only raw
  `text(...)` SQL in the codebase is either fully static (`SELECT 1` in the readiness check,
  `pg_try_advisory_lock`/`pg_advisory_unlock` in `app/jobs/locks.py`, both using `:bind`
  parameters for the one dynamic value) or a static partial-index predicate
  (`index_where=text("dedup_key IS NOT NULL")` in `app/notifications/service.py` and
  `app/tasks/service.py`) — none interpolate request data. Alembic migrations' `op.execute(f"ALTER
  TABLE {table_name} ...")` calls use `table_name` from a hardcoded Python list defined in the
  migration itself, never user input, which is the standard safe pattern for DDL (bind parameters
  aren't valid there regardless). No SQLi gap found.
- **SSRF**: every outbound `httpx` call in the codebase targets a URL built from server
  configuration or a hardcoded vendor constant — `settings.supabase_url` (auth invite,
  password-reset proxy, Supabase Storage adapter), or literal `"https://api.openai.com/v1"` /
  `"https://api.groq.com/openai/v1"` in `app/controlled_ai/providers.py`. No endpoint accepts a
  client-supplied URL and fetches it. `app.communications.providers.InternalMockProvider` (the
  only registered communication provider) makes no network calls at all. No SSRF gap found.
- **Command injection**: no `subprocess`, `os.system`, `os.popen`, `shell=True`, `eval`, or
  `exec` usage anywhere in `apps/api/app`. No gap found (nothing to find — there is no shell
  surface).
- **HTML/Markdown sanitization**: `apps/dashboard` has zero uses of `dangerouslySetInnerHTML`
  anywhere in the codebase — knowledge article content, notes, and every other free-text field
  render as plain JSX text children (e.g. `<p>{article.content}</p>` in
  `apps/dashboard/src/app/(app)/knowledge-base/articles/[articleId]/article-detail.tsx`), which
  React escapes by construction. No markdown-to-HTML rendering pipeline exists, so there is no
  raw-HTML surface to sanitize in the first place. The one place the backend *does* generate
  HTML — `app/report_exports/templates.py::build_report_html`, the PDF-export template — already
  runs every dynamic value through `html.escape()` before interpolation; confirmed by reading the
  full template, not assumed. No XSS/HTML-injection gap found.
- **Adjacent checks also covered while reviewing this area**: no open-redirect surface exists
  (no `RedirectResponse` anywhere — the API is pure JSON); every generated storage object path
  (`app.storage.service.build_object_path`, and the equivalent inline logic in
  `app.knowledge.attachments`/`app.staff_operations.documents`) is built from a server-generated
  UUID and the already-validated extension, never the raw client-supplied filename — no path
  traversal.
- **Outcome**: no code changes required. This section exists to record that these categories
  were checked, not skipped, per the Phase 16 verification requirement.
- **Task**: #289.

### 9. Prompt-injection and AI safety hardening

- **Context, existing state (Phase 14) — already strong**: `app/controlled_ai` was built with
  most of this section's requirements already in place, confirmed by reading every module before
  changing anything:
  - System prompts are server-defined constants (`app/controlled_ai/prompts.py`) — no caller can
    set or influence the system prompt, which is the primary prompt-injection vector in most AI
    integrations.
  - Grounding evidence (`app/controlled_ai/grounding.py`) comes only from structured,
    permission-filtered database queries for four of the five wired capabilities — the model
    never sees raw free text for `dashboard_summary`, `metric_change_explanation`,
    `anomaly_evidence_summary`, or `report_narrative`.
  - Every output is schema-validated (`app/controlled_ai/safety.py::validate_structured_output`)
    before being trusted, and a validation failure never mutates a business record.
  - There is no tool-execution capability wired to any model call — the model only ever returns
    text/structured JSON that the backend interprets, so "unsafe tool execution" and "recursive
    tool loops" have no surface to exploit; nothing was needed there.
  - Full audit trail per request (`AiRequest`: permission scope, grounding summary, source
    references, provider, tokens, latency, status), a 20-second provider timeout
    (`app/controlled_ai/providers.py::_REQUEST_TIMEOUT_SECONDS`), and graceful failure handling
    that never blocks core CRM workflows were all already correct.
- **Found — oversized prompts**: `nl_question_query_plan` is the one capability where user free
  text (`question`) does flow into the model's prompt (the server never trusts the model's
  proposed `metric_code` — it validates that against the real metric registry before running
  anything, so the existing design already blocks the *dangerous* outcome of injection; the
  remaining gap was resource/cost abuse via an unbounded prompt). `AiCompletionRequestIn.params:
  dict[str, object]` has no length limit, so a very long `question` could be sent to a real
  provider once one is configured — a cost/quota exhaustion vector and the literal "oversized
  prompts" case this phase's own instruction section G names. **Fix**: `ground_nl_question_query_plan`
  now rejects a `question` longer than `_MAX_QUESTION_LENGTH` (2000 characters, matching that
  template's own `max_context_tokens=2000`) via the existing `ControlledAiError` path — recorded
  on the `AiRequest` row as a `grounding_error` failure like any other grounding failure, not a
  new failure mode.
- **Found — no AI-specific rate limit**: `POST /api/v1/ai/requests` only inherited the generic
  60-requests/60-seconds-per-IP limiter every authenticated endpoint gets
  (`app.auth.dependencies.get_current_staff_user`) — CLAUDE.md §6.5 explicitly calls out AI
  endpoints as their own rate-limit classification, distinct from the generic one, since a
  generation has a real per-call cost once a live provider is configured. **Fix**: added a
  per-staff-account limit (20 requests/hour) on `create_ai_request`, using the same
  `check_rate_limit()` (with its Phase 16 progressive backoff — see finding 4) rather than a
  new mechanism.
- **Found — HR-sensitive block left no audit trail**: `AiRequest.safety_blocked`/
  `safety_block_reason` columns and the `"blocked"` status already existed in the schema
  (Phase 14), but `request_completion()` raised `HrSensitiveDataBlockedError` *before* creating
  the `AiRequest` row when a caller lacked `ai.analytics.hr_sensitive` — so a blocked attempt
  left no record at all, unlike every other outcome (pending/completed/failed), and the
  `safety_blocked` field was write-only-never-written. Not currently reachable
  (`HR_SENSITIVE_FEATURE_CODES` is still the empty set — no Phase-14-wired capability touches HR
  data yet), but the schema was clearly designed for this to be recorded, not just rejected.
  **Fix**: the HR-sensitivity check now runs *after* the request row is created, sets
  `status="blocked"`, `safety_blocked=True`, and a `safety_block_reason`, and returns the row
  normally instead of raising — completing an already-designed safety mechanism rather than
  building a new one. Removed `HrSensitiveDataBlockedError`, which became unused once nothing
  raised it.
- **Tests**: `apps/api/tests/test_controlled_ai.py` — oversized question rejected at both the
  grounding-function and `request_completion` level; HR-sensitive block (forced via monkeypatch,
  since the real trigger set is empty today) is recorded on the request row with the right
  status/reason/timestamps and never reaches grounding or the provider.
  `apps/api/tests/test_phase14_api.py` — the 21st AI request from the same staff account within
  an hour returns 429.
- **Task**: #290.

## Authorization coverage

See [`AUTHORIZATION_COVERAGE_REPORT.md`](AUTHORIZATION_COVERAGE_REPORT.md) — 565 endpoints
audited, 0 confirmed gaps. Task #291.
