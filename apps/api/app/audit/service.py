"""Thin helper around the Phase 2 `audit_events` table —
DATABASE_AND_API.md section 16.5, CLAUDE.md section 6.6. Every Phase 3
security-sensitive action is recorded here; no separate/duplicate audit
mechanism is introduced.
"""

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def record_audit_event(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action_code: str,
    target_type: str,
    target_id: uuid.UUID | None,
    source: str = "api",
    request: Request | None = None,
    safe_metadata: dict[str, Any] | None = None,
    before_summary: dict[str, Any] | None = None,
    after_summary: dict[str, Any] | None = None,
) -> None:
    request_id = getattr(request.state, "request_id", None) if request else None
    event = AuditEvent(
        actor_id=actor_id,
        action_code=action_code,
        target_type=target_type,
        target_id=target_id,
        source=source,
        request_id=request_id,
        correlation_id=request_id,
        safe_metadata=safe_metadata,
        before_summary=before_summary,
        after_summary=after_summary,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent") if request else None,
    )
    session.add(event)
    await session.flush()
