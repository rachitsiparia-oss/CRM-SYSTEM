"""Idempotent development seed data for the Knowledge Base — canonical
categories from PROJECT_PLAN.md's "Dummy document categories" plus this
phase's own instruction section 1's category list, and the ten sample SOPs
that same instruction names. Every article is carried through the full
draft -> in_review -> approved -> published lifecycle using the one
bootstrapped owner account as author/reviewer/publisher (the owner's
`is_privileged` flag is what makes self-approval allowed here) — mirroring
`app.communications.seed`'s `_system_actor` pattern, since no other real
staff account exists until Supabase Auth identities are created.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeArticle, KnowledgeCategory, StaffUser
from app.knowledge.articles import (
    create_article,
    make_review_decision,
    publish_article,
    submit_for_review,
)
from app.knowledge.assignments import create_assignment
from app.knowledge.categories import create_category
from app.knowledge.schemas import ArticleCreateIn, ArticleType, AssignmentCreateIn, CategoryCreateIn

_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Restaurant Operations", "restaurant_operations"),
    ("Front of House", "front_of_house"),
    ("Kitchen", "kitchen"),
    ("Food Safety", "food_safety"),
    ("Customer Service", "customer_service"),
    ("Reservations", "reservations"),
    ("Orders and POS", "orders_pos"),
    ("Inventory", "inventory"),
    ("Cleaning", "cleaning"),
    ("Emergency Procedures", "emergency_procedures"),
    ("HR Policies", "hr_policies"),
    ("Training", "training"),
)

# title, category_code, article_type, requires_acknowledgement, content
_ARTICLES: tuple[tuple[str, str, ArticleType, bool, str], ...] = (
    (
        "Opening Checklist",
        "restaurant_operations",
        "checklist",
        False,
        "1. Unlock and disarm alarm.\n2. Turn on kitchen equipment.\n3. Check walk-in "
        "temperatures.\n4. Restock front-of-house stations.\n5. Brief the floor team.",
    ),
    (
        "Closing Checklist",
        "restaurant_operations",
        "checklist",
        False,
        "1. Reconcile the till.\n2. Store perishables correctly.\n3. Clean all stations.\n"
        "4. Arm the alarm and lock up.",
    ),
    (
        "Guest Complaint Handling SOP",
        "customer_service",
        "sop",
        False,
        "Listen without interrupting, apologize sincerely, offer a concrete resolution "
        "(remake, discount, or complimentary item per manager approval), and log the "
        "complaint in the CRM.",
    ),
    (
        "Reservation Escalation SOP",
        "reservations",
        "sop",
        False,
        "For overbooked slots or VIP requests, notify the on-duty reservation manager "
        "immediately. Do not promise a table the floor plan cannot support.",
    ),
    (
        "Food Allergy Protocol",
        "food_safety",
        "sop",
        True,
        "Always ask about allergies before taking an order. Flag allergy orders to the "
        "kitchen verbally and on the ticket. Use separate utensils and surfaces for "
        "allergen-free preparation. When in doubt, escalate to the kitchen manager.",
    ),
    (
        "Inventory Receiving Procedure",
        "inventory",
        "procedure",
        False,
        "Verify delivered quantities against the purchase order, inspect for damage or "
        "spoilage, record the goods receipt in the CRM, and reject anything that fails "
        "quality checks.",
    ),
    (
        "Wastage Reporting Procedure",
        "inventory",
        "procedure",
        False,
        "Record every wastage event with quantity, reason, and photo evidence where "
        "practical. Wastage above the daily threshold requires manager approval.",
    ),
    (
        "Emergency Evacuation Procedure",
        "emergency_procedures",
        "emergency_instruction",
        True,
        "On alarm activation, stop service immediately, guide guests to the nearest exit "
        "calmly, account for all staff at the assembly point, and call emergency services.",
    ),
    (
        "Cleaning and Hygiene SOP",
        "cleaning",
        "sop",
        True,
        "Sanitize all food-contact surfaces every two hours, follow the color-coded "
        "cloth system, and complete the hygiene log at the end of every shift.",
    ),
    (
        "Data Privacy Guideline",
        "hr_policies",
        "policy",
        True,
        "Customer and staff personal data must only be accessed for legitimate "
        "operational purposes, never shared outside the CRM, and reported to management "
        "immediately if a breach is suspected.",
    ),
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_knowledge_categories(session: AsyncSession) -> dict[str, KnowledgeCategory]:
    actor = await _system_actor(session)
    by_code: dict[str, KnowledgeCategory] = {}
    for index, (name, code) in enumerate(_CATEGORIES):
        existing = await session.scalar(
            select(KnowledgeCategory).where(KnowledgeCategory.code == code)
        )
        if existing is not None:
            by_code[code] = existing
            continue
        if actor is None:
            continue
        category = await categories_create(
            session, actor=actor, name=name, code=code, sort_order=index
        )
        by_code[code] = category
    return by_code


async def categories_create(
    session: AsyncSession, *, actor: StaffUser, name: str, code: str, sort_order: int
) -> KnowledgeCategory:
    return await create_category(
        session, actor=actor, payload=CategoryCreateIn(name=name, code=code, sort_order=sort_order)
    )


async def seed_knowledge_articles(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return
    categories_by_code = await seed_knowledge_categories(session)

    for title, category_code, article_type, requires_ack, content in _ARTICLES:
        existing = await session.scalar(
            select(KnowledgeArticle).where(KnowledgeArticle.title == title)
        )
        if existing is not None:
            continue
        category = categories_by_code.get(category_code)
        article = await create_article(
            session,
            actor=actor,
            payload=ArticleCreateIn(
                title=title,
                summary=content[:120],
                content=content,
                article_type=article_type,
                category_id=category.id if category else None,
                owner_staff_id=actor.id,
                visibility_scope="all_staff",
                requires_acknowledgement=requires_ack,
            ),
        )
        await submit_for_review(session, actor=actor, article=article)
        await make_review_decision(
            session, actor=actor, article=article, decision="approved", comment=None
        )
        await publish_article(session, actor=actor, article=article)

        if requires_ack:
            await create_assignment(
                session,
                actor=actor,
                article=article,
                payload=AssignmentCreateIn(
                    assignee_type="staff", staff_id=actor.id, is_mandatory=True
                ),
            )
