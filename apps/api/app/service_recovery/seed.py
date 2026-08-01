"""Idempotent development seed data for compensation approval rules and
service-recovery actions. Run after `app.feedback.seed`/
`app.complaints.seed` — every recovery action here is proposed against a
complaint those seeds already created."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CompensationApprovalRule,
    Complaint,
    Customer,
    ServiceRecoveryAction,
    StaffUser,
)
from app.service_recovery import service
from app.service_recovery.schemas import ApprovalRuleCreateIn


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def _customer_id(session: AsyncSession, email: str) -> uuid.UUID | None:
    result: uuid.UUID | None = await session.scalar(
        select(Customer.id).where(Customer.primary_email == email)
    )
    return result


async def _latest_complaint(
    session: AsyncSession, *, customer_id: uuid.UUID, category: str
) -> Complaint | None:
    result: Complaint | None = await session.scalar(
        select(Complaint)
        .where(Complaint.customer_id == customer_id, Complaint.category == category)
        .order_by(Complaint.created_at.desc())
        .limit(1)
    )
    return result


async def _seed_approval_rule(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(CompensationApprovalRule).where(
            CompensationApprovalRule.code == "high_value_compensation"
        )
    )
    if existing is not None:
        return
    await service.create_approval_rule(
        session,
        payload=ApprovalRuleCreateIn(
            code="high_value_compensation",
            name="High-value compensation (>= INR 100, high/critical severity)",
            recovery_type=None,
            min_value_minor=10_000,
            max_value_minor=None,
            applicable_severities=["high", "critical"],
            required_permission="recovery.approve",
            # Dev seeding only ever has one privileged staff_user available
            # (the 65-person roster isn't seeded — see app.db.seed's own
            # docstring), so the same actor proposes and approves below;
            # `True` here is a seed-data concession, not the production
            # default an admin would configure.
            allow_self_approval=True,
        ),
    )


async def seed_service_recovery(session: AsyncSession) -> None:
    await _seed_approval_rule(session)

    actor = await _system_actor(session)
    if actor is None:
        return

    karthik_id = await _customer_id(session, "karthik.iyer@example.test")
    if karthik_id is not None:
        complaint = await _latest_complaint(session, customer_id=karthik_id, category="delivery")
        if complaint is not None:
            existing_action = await session.scalar(
                select(ServiceRecoveryAction).where(
                    ServiceRecoveryAction.complaint_id == complaint.id,
                    ServiceRecoveryAction.recovery_type == "loyalty_credit",
                )
            )
            if existing_action is None:
                action = await service.propose_action(
                    session,
                    actor=actor,
                    complaint=complaint,
                    recovery_type="loyalty_credit",
                    value_minor=None,
                    points=200,
                    description="200 bonus loyalty points for the late-delivery inconvenience.",
                )
                if not action.approval_required:
                    await service.execute_action(session, actor=actor, action=action)

    shreya_id = await _customer_id(session, "shreya.kulkarni@example.test")
    if shreya_id is not None:
        complaint = await _latest_complaint(session, customer_id=shreya_id, category="delay")
        if complaint is not None:
            existing_action = await session.scalar(
                select(ServiceRecoveryAction).where(
                    ServiceRecoveryAction.complaint_id == complaint.id,
                    ServiceRecoveryAction.recovery_type == "complimentary_item",
                )
            )
            if existing_action is None:
                action = await service.propose_action(
                    session,
                    actor=actor,
                    complaint=complaint,
                    recovery_type="complimentary_item",
                    value_minor=15_000,
                    points=None,
                    description="Complimentary combo meal voucher (INR 150) for the late order.",
                )
                if action.approval_required:
                    action = await service.approve_action(session, actor=actor, action=action)
                await service.execute_action(session, actor=actor, action=action)
