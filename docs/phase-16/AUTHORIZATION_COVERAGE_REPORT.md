# Phase 16 — Authorization Coverage Report

Generated: 2026-08-02
Scope: every HTTP endpoint registered in `apps/api/app/main.py` (39 router modules, all 15 completed phases).

## Method

A static scan (`scripts` run ad hoc, not checked in — trivially reproducible: walk every
`app/*/router.py`, regex-match each `@router.<method>("<path>")` decorator, and inspect the
following function signature for an authorization dependency) enumerated every route decorator
and classified it into one of three buckets:

1. **Permission-checked** — signature carries `Depends(require_permission("<code>"))`
   (`apps/api/app/permissions/dependencies.py`), which enforces the single canonical capability
   registry (`app/permissions/registry.py`) via `has_permission()`.
2. **Auth-only** — signature carries `CurrentStaffUser` (the `Depends(get_current_staff_user)`
   alias) but no `require_permission(...)`. Flagged for manual review since a valid JWT alone is
   not authorization.
3. **No dependency detected** — neither pattern found in the signature. Flagged for manual
   review as a potential gap.

The static pass only inspects function *signatures*. Several endpoints enforce authorization in
the function *body* instead (a `_require_self_or_permission()` helper call, or an equivalent
manual `has_permission()` check) — these are legitimate but invisible to the signature-only
regex, so every flagged endpoint was individually read and verified against source, not accepted
on the static classification alone.

## Result

| Bucket | Count |
|---|---|
| Total endpoints scanned | 565 |
| Permission-checked (`require_permission`) | 543 |
| Flagged for manual review (auth-only or no dependency detected) | 22 |
| **Confirmed gap after manual review** | **0** |

Every one of the 22 flagged endpoints was read in full and falls into a documented, intentional
category below. None grant an unauthenticated or under-authorized caller access to a protected
operation.

## Flagged endpoints — manual review outcome

### A. Deliberately unauthenticated (public by design)

| Endpoint | File | Justification |
|---|---|---|
| `GET /health/live` | `app/health/router.py:15` | Liveness probe; must respond before auth infra is confirmed healthy. |
| `GET /health/ready` | `app/health/router.py:22` | Readiness probe; same reasoning. |
| `GET /metrics` | `app/health/router.py:43` | Prometheus scrape target; internal-network-only by infrastructure convention, not app-layer auth. No secrets or PII in exposition format. |
| `POST /auth/login` | `app/auth/router.py:56` | Credential exchange endpoint — the thing that *establishes* auth. Rate-limited (`SECURITY_PERFORMANCE_AND_QUALITY.md` §3.4). |
| `POST /auth/password-reset` | `app/auth/router.py:160` | Unauthenticated by design (caller has forgotten their password); proxies to Supabase Auth recovery, rate-limited by email and IP, returns a constant response to prevent account enumeration. Documented in the endpoint's own docstring. |

### B. Provider-signature authenticated (not staff JWT auth)

| Endpoint | File | Justification |
|---|---|---|
| `POST /communications/webhooks/{provider_name}/inbound` | `app/communications/router.py:709` | Inbound webhook from an external channel provider. Authenticated via `webhooks.process_inbound_webhook()`'s signature verification (raises `WebhookSignatureError` → 401), not a staff bearer token — the caller is the provider, not a staff member. `include_in_schema=False` keeps it out of the public API surface. |
| `POST /communications/webhooks/{provider_name}/status` | `app/communications/router.py:737` | Same pattern for delivery-status callbacks. |

Signature-verification depth for these two is tracked separately under task #292
(webhook signature/replay/idempotency review).

### C. Self-service — authenticated caller acting only on their own record

Every endpoint below resolves the target record via the *caller's own* `actor.id` /
`staff_user.id` (never a client-supplied ID used as the sole scope), so `CurrentStaffUser` alone
is the correct and complete check — there is no "other user's data" case to gate with a
permission code:

| Endpoint | File | Self-scoping mechanism |
|---|---|---|
| `GET /auth/me`, `PATCH /auth/me` | `app/auth/router.py:80,90` | Operates on `staff_user.id` from the token. |
| `POST /auth/logout` | `app/auth/router.py:119` | Revokes the caller's own session. |
| `GET /auth/session` | `app/auth/router.py:140` | Decodes the caller's own token claims. |
| `GET /notifications`, `GET /notifications/unread-count` | `app/notifications/router.py:28,58` | Query filtered by `Notification.recipient_staff_id == actor.id`. |
| `POST /notifications/{id}/read`, `/dismiss`, `/action` | `app/notifications/router.py:70,94,110` | `_get_own_notification_or_404()` 404s if `recipient_staff_id != staff_id` — an IDOR-safe ownership check, not a bare permission gate. |
| `POST /notifications/read-all` | `app/notifications/router.py:86` | Scoped to `recipient_staff_id=actor.id`. |

### D. Self-or-permission — ownership check performed in the function body

These call `_require_self_or_permission()` (`app/staff_operations/router.py`) or an equivalent
inline `has_permission()` check *after* the signature-level `CurrentStaffUser` dependency,
raising `403` unless the caller is either the record's own subject or holds the stated
management permission. The static scan cannot see this (it only inspects signatures), so each
was confirmed by reading the function body:

| Endpoint | File | Enforced via |
|---|---|---|
| `POST /staff-operations/transition-steps/{id}/complete` | `router.py:346` | `_require_self_or_permission(..., "staff.onboarding.manage")` |
| `POST /staff-operations/reviews/{id}/transition` | `router.py:906` | Conditional: self-or-permission for `acknowledged`, else hard `staff.reviews.manage` check |
| `GET /staff-operations/reviews` | `router.py:934` | Result scoped to `actor.id` unless caller holds `staff.reviews.manage` |
| `POST /staff-operations/availability/{staff_user_id}` | `router.py:1000` | `_require_self_or_permission(..., "staff.availability.manage")` |
| `GET /staff-operations/availability/{staff_user_id}` | `router.py:1022` | `_require_self_or_permission(..., "staff.availability.view")` |

## Conclusion

No endpoint in the current API surface is missing an authorization check. The 543
`require_permission`-gated endpoints enforce the canonical capability registry; the remaining 22
are correctly scoped through one of the three documented exception categories above, all of
which pre-date Phase 16 and were re-verified, not newly introduced, by this audit.

## Recommendation carried into later Phase 16 tasks

- Webhook signature/replay/idempotency depth (category B) is audited separately under task
  #292, since "a signature check exists" is a different question from "the signature check is
  correctly implemented, replay-safe, and idempotent."
- No code changes were required as a result of this report. This is a coverage audit, not a
  remediation — it is being recorded so the "generate a report showing endpoints with missing
  permission checks" deliverable (Phase 16 §B) is documented and reproducible, and so the next
  phase does not have to re-derive this from scratch.
