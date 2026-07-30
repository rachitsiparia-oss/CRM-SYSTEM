"""Template CRUD and a constrained rendering engine — CLAUDE.md section 17
("no arbitrary unsafe template execution — use a constrained renderer") and
this phase's own instruction section 9: only declared, validated variables
may appear in a template body; rendering never evaluates arbitrary
expressions, just `str.format`-style substitution restricted to the
template's own declared `variables` list.
"""

import re
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.schemas import MessageTemplateCreateIn, MessageTemplateUpdateIn
from app.db.models import CommunicationChannel, MessageTemplate, StaffUser

_VARIABLE_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class TemplateRenderError(ValueError):
    pass


def _referenced_variables(body: str) -> set[str]:
    return set(_VARIABLE_PATTERN.findall(body))


def validate_template_variables(*, body: str, subject: str | None, variables: list[str]) -> None:
    referenced = _referenced_variables(body) | (
        _referenced_variables(subject) if subject else set()
    )
    undeclared = referenced - set(variables)
    if undeclared:
        raise TemplateRenderError(f"Template references undeclared variables: {sorted(undeclared)}")


def render_template(
    *, body: str, subject: str | None, declared_variables: list[str], values: dict[str, Any]
) -> tuple[str, str | None]:
    missing = set(declared_variables) - set(values)
    if missing:
        raise TemplateRenderError(f"Missing required template variables: {sorted(missing)}")
    extra = set(values) - set(declared_variables)
    if extra:
        raise TemplateRenderError(f"Unexpected template variables supplied: {sorted(extra)}")
    safe_values = {key: str(value) for key, value in values.items()}
    rendered_body = body.format(**safe_values)
    rendered_subject = subject.format(**safe_values) if subject else None
    return rendered_body, rendered_subject


async def create_template(
    session: AsyncSession, *, actor: StaffUser, payload: MessageTemplateCreateIn
) -> MessageTemplate:
    channel = await session.get(CommunicationChannel, payload.channel_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Communication channel not found.")
    validate_template_variables(
        body=payload.body, subject=payload.subject, variables=payload.variables
    )
    template = MessageTemplate(
        name=payload.name,
        code=payload.code,
        channel_id=payload.channel_id,
        category=payload.category,
        language=payload.language,
        subject=payload.subject,
        body=payload.body,
        variables=payload.variables,
        status="draft",
        is_transactional=payload.is_transactional,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        created_by=actor.id,
    )
    session.add(template)
    await session.flush()
    return template


async def update_template(
    session: AsyncSession,
    *,
    actor: StaffUser,
    template: MessageTemplate,
    payload: MessageTemplateUpdateIn,
) -> MessageTemplate:
    if template.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This template was modified by someone else. Reload and try again.",
        )
    if payload.name is not None:
        template.name = payload.name
    if payload.subject is not None:
        template.subject = payload.subject
    if payload.body is not None:
        template.body = payload.body
    if payload.variables is not None:
        template.variables = payload.variables
    if payload.status is not None:
        template.status = payload.status
    if payload.is_transactional is not None:
        template.is_transactional = payload.is_transactional
    if payload.effective_from is not None:
        template.effective_from = payload.effective_from
    if payload.effective_to is not None:
        template.effective_to = payload.effective_to
    validate_template_variables(
        body=template.body, subject=template.subject, variables=template.variables
    )
    template.updated_by = actor.id
    template.version += 1
    await session.flush()
    return template


async def get_template(session: AsyncSession, template_id: uuid.UUID) -> MessageTemplate | None:
    return await session.get(MessageTemplate, template_id)
