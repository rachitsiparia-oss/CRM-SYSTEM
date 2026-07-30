"""Visibility rule CRUD and the enforcement predicate every list/detail/
search/attachment endpoint calls — this phase's own instruction section 5:
"Ensure search, list, detail and attachment endpoints all enforce the same
visibility rules."

`kitchen_only`/`front_of_house_only` are resolved by staff *role* membership,
not department — `app.permissions.seed.DEPARTMENTS` has no dedicated
front-of-house department code (front-of-house staff are not canonically
assigned to any single department), so role membership is the only
reliable signal. This is a Phase 11 design decision, documented in
`docs/DATABASE_AND_API.md` section 12.6.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeArticle, KnowledgeVisibilityRule, Role, StaffRole, StaffUser
from app.knowledge.schemas import VisibilityRuleCreateIn
from app.permissions.service import has_permission

_KITCHEN_ROLE_CODES = frozenset({"owner", "general_manager", "kitchen_manager", "kitchen_staff"})
_FRONT_OF_HOUSE_ROLE_CODES = frozenset(
    {"owner", "general_manager", "front_of_house_staff", "shift_supervisor", "reservation_manager"}
)


async def _viewer_role_codes(session: AsyncSession, staff_id: uuid.UUID) -> set[str]:
    result = await session.execute(
        select(Role.code)
        .join(StaffRole, StaffRole.role_id == Role.id)
        .where(StaffRole.staff_user_id == staff_id)
    )
    return {row[0] for row in result.all()}


async def is_article_visible_to(
    session: AsyncSession, *, article: KnowledgeArticle, viewer: StaffUser
) -> bool:
    scope = article.visibility_scope
    if scope == "all_staff":
        return True
    if scope == "management_only":
        return viewer.is_privileged
    if scope == "hr_only":
        return await has_permission(session, viewer.id, "staff.hr_sensitive.read")
    if scope in ("kitchen_only", "front_of_house_only"):
        role_codes = await _viewer_role_codes(session, viewer.id)
        allowed = _KITCHEN_ROLE_CODES if scope == "kitchen_only" else _FRONT_OF_HOUSE_ROLE_CODES
        return bool(role_codes & allowed)
    if scope == "department":
        if viewer.department_id is None:
            return False
        rule = await session.scalar(
            select(KnowledgeVisibilityRule).where(
                KnowledgeVisibilityRule.article_id == article.id,
                KnowledgeVisibilityRule.rule_type == "department",
                KnowledgeVisibilityRule.department_id == viewer.department_id,
            )
        )
        return rule is not None
    if scope == "role":
        role_codes = await _viewer_role_codes(session, viewer.id)
        if not role_codes:
            return False
        rules = (
            await session.scalars(
                select(KnowledgeVisibilityRule).where(
                    KnowledgeVisibilityRule.article_id == article.id,
                    KnowledgeVisibilityRule.rule_type == "role",
                )
            )
        ).all()
        if not rules:
            return False
        rule_role_ids = {rule.role_id for rule in rules}
        viewer_role_ids = await session.scalars(select(Role.id).where(Role.code.in_(role_codes)))
        return bool(rule_role_ids & set(viewer_role_ids.all()))
    if scope == "specific_staff":
        rule = await session.scalar(
            select(KnowledgeVisibilityRule).where(
                KnowledgeVisibilityRule.article_id == article.id,
                KnowledgeVisibilityRule.rule_type == "staff",
                KnowledgeVisibilityRule.staff_id == viewer.id,
            )
        )
        return rule is not None
    return False


async def list_visibility_rules(
    session: AsyncSession, article_id: uuid.UUID
) -> list[KnowledgeVisibilityRule]:
    result = await session.scalars(
        select(KnowledgeVisibilityRule).where(KnowledgeVisibilityRule.article_id == article_id)
    )
    return list(result.all())


async def add_visibility_rule(
    session: AsyncSession, *, article: KnowledgeArticle, payload: VisibilityRuleCreateIn
) -> KnowledgeVisibilityRule:
    if article.visibility_scope not in ("department", "role", "specific_staff"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Visibility rules only apply when the article's visibility scope is "
            "department, role, or specific_staff.",
        )
    if payload.rule_type != article.visibility_scope:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Rule type must match the article's visibility_scope "
            f"({article.visibility_scope!r}).",
        )
    rule = KnowledgeVisibilityRule(
        article_id=article.id,
        rule_type=payload.rule_type,
        department_id=payload.department_id,
        role_id=payload.role_id,
        staff_id=payload.staff_id,
    )
    session.add(rule)
    await session.flush()
    return rule


async def remove_visibility_rule(
    session: AsyncSession, *, article_id: uuid.UUID, rule_id: uuid.UUID
) -> None:
    rule = await session.get(KnowledgeVisibilityRule, rule_id)
    if rule is None or rule.article_id != article_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Visibility rule not found.")
    await session.delete(rule)
    await session.flush()
