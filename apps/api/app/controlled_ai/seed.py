"""Idempotent development seed data — syncs `AiPromptTemplate` rows from
the code-defined `PROMPT_TEMPLATES` registry, the same
registry-is-source/table-is-synced-copy pattern
`app.permissions.seed.seed_permissions` already established."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controlled_ai.prompts import PROMPT_TEMPLATES
from app.db.models import AiPromptTemplate, StaffUser


async def seed_ai_prompt_templates(session: AsyncSession) -> None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return

    for template in PROMPT_TEMPLATES:
        existing = await session.scalar(
            select(AiPromptTemplate).where(
                AiPromptTemplate.feature_code == template.feature_code,
                AiPromptTemplate.version == template.version,
            )
        )
        if existing is not None:
            continue
        session.add(
            AiPromptTemplate(
                feature_code=template.feature_code,
                version=template.version,
                purpose=template.purpose,
                allowed_input_fields=list(template.allowed_input_fields),
                prohibited_data=list(template.prohibited_data),
                output_schema=template.output_schema,
                max_context_tokens=template.max_context_tokens,
                safety_constraints=template.safety_constraints,
                model_config_reference=template.model_config_reference,
                is_active=True,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
    await session.flush()
