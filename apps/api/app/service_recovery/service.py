"""Compensation approval routing and service-recovery action lifecycle —
GROWTH_AND_INTELLIGENCE.md section 12.6, instruction sections 6/14.

No value-threshold approval-routing precedent exists anywhere else in the
codebase (`customer_credit.approve` is granted in the role matrix but never
actually checked against a threshold anywhere) — the evaluation logic here
is new, not a reuse of an existing pattern.

Execution never mutates a balance directly. It calls the already-audited,
already-permission-gated `app.loyalty`/`app.customer_credit`/`app.orders`
services that actually record the value, and stores only a reference to
the resulting row (`execution_reference_type`/`execution_reference_id`) —
PROJECT_PLAN.md's Phase 13 scope bullet: "Compensation approval routed
through the correct order/loyalty/promotion module (never directly
mutated from the complaint screen)."
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    CompensationApprovalRule,
    Complaint,
    Customer,
    ServiceRecoveryAction,
    ServiceRecoveryActionHistory,
    StaffUser,
)
from app.notifications.service import notify
from app.service_recovery.errors import (
    AlreadyExecutedError,
    ApprovalNotRequiredError,
    InvalidActionStatusTransitionError,
    NotApprovedError,
    SelfApprovalNotAllowedError,
)
from app.service_recovery.schemas import ApprovalRuleCreateIn, ApprovalRuleUpdateIn

_MONEY_TYPES = {"refund_request", "approved_refund", "discount", "complimentary_item"}
_POINTS_TYPES = {"loyalty_credit"}

_ACTION_TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"approval_required", "executing", "cancelled"},
    "approval_required": {"approved", "rejected", "cancelled"},
    "approved": {"executing", "cancelled"},
    "rejected": set(),
    "executing": {"completed", "failed"},
    "completed": {"reversed"},
    "failed": {"executing", "cancelled"},
    "reversed": set(),
    "cancelled": set(),
}


def _idempotency_key(complaint_id: uuid.UUID, action_id: uuid.UUID) -> str:
    return f"complaint:{complaint_id}:recovery:{action_id}"


async def get_action(session: AsyncSession, action_id: uuid.UUID) -> ServiceRecoveryAction | None:
    return await session.get(ServiceRecoveryAction, action_id)


async def list_actions(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    complaint_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    status: str | None = None,
    recovery_type: str | None = None,
) -> tuple[list[ServiceRecoveryAction], int]:
    from sqlalchemy import func

    query = select(ServiceRecoveryAction)
    if complaint_id:
        query = query.where(ServiceRecoveryAction.complaint_id == complaint_id)
    if customer_id:
        query = query.where(ServiceRecoveryAction.customer_id == customer_id)
    if status:
        query = query.where(ServiceRecoveryAction.status == status)
    if recovery_type:
        query = query.where(ServiceRecoveryAction.recovery_type == recovery_type)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    query = (
        query.order_by(ServiceRecoveryAction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list((await session.scalars(query)).all())
    return rows, total or 0


def _rule_specificity(rule: CompensationApprovalRule) -> int:
    score = 0
    if rule.recovery_type is not None:
        score += 2
    if rule.applicable_severities is not None:
        score += 1
    return score


async def evaluate_approval_requirement(
    session: AsyncSession,
    *,
    recovery_type: str,
    value_minor: int | None,
    points: int | None,
    severity: str,
) -> CompensationApprovalRule | None:
    """The most specific matching *active* rule governs; its mere existence
    means the action requires approval under `required_permission`. No
    matching rule means self-service under the base `recovery.propose`/
    `recovery.execute` grants alone."""
    rows = list(
        (
            await session.scalars(
                select(CompensationApprovalRule).where(CompensationApprovalRule.is_active.is_(True))
            )
        ).all()
    )
    matching: list[CompensationApprovalRule] = []
    for rule in rows:
        if rule.recovery_type is not None and rule.recovery_type != recovery_type:
            continue
        if rule.applicable_severities is not None and severity not in rule.applicable_severities:
            continue
        if recovery_type in _MONEY_TYPES and value_minor is not None:
            if rule.min_value_minor is not None and value_minor < rule.min_value_minor:
                continue
            if rule.max_value_minor is not None and value_minor > rule.max_value_minor:
                continue
        matching.append(rule)

    if not matching:
        return None
    matching.sort(key=lambda r: (-_rule_specificity(r), r.created_at))
    return matching[0]


async def propose_action(
    session: AsyncSession,
    *,
    actor: StaffUser,
    complaint: Complaint,
    recovery_type: str,
    value_minor: int | None,
    points: int | None,
    description: str,
) -> ServiceRecoveryAction:
    action_id = uuid.uuid4()
    rule = await evaluate_approval_requirement(
        session,
        recovery_type=recovery_type,
        value_minor=value_minor,
        points=points,
        severity=complaint.severity,
    )
    approval_required = rule is not None

    action = ServiceRecoveryAction(
        id=action_id,
        complaint_id=complaint.id,
        customer_id=complaint.customer_id,
        recovery_type=recovery_type,
        status="approval_required" if approval_required else "proposed",
        value_minor=value_minor,
        points=points,
        description=description,
        proposed_by_staff_id=actor.id,
        approval_required=approval_required,
        approval_rule_id=rule.id if rule else None,
        idempotency_key=_idempotency_key(complaint.id, action_id),
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(action)
    session.add(
        ServiceRecoveryActionHistory(
            action_id=action.id, from_status=None, to_status=action.status, actor_id=actor.id
        )
    )
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="recovery.proposed",
        target_type="service_recovery_action",
        target_id=action.id,
        safe_metadata={"recovery_type": recovery_type, "approval_required": approval_required},
    )

    if approval_required and rule is not None:
        await _notify_approvers(
            session,
            action=action,
            required_permission=rule.required_permission,
            title=f"Recovery approval needed for complaint {complaint.complaint_number}",
        )
    return action


async def _notify_approvers(
    session: AsyncSession, *, action: ServiceRecoveryAction, required_permission: str, title: str
) -> None:
    """Notifies every active staff member currently holding
    `required_permission` — the recovery-approval analogue of
    `app.complaints.service._notify_management`."""
    from app.db.models import Role, StaffRole
    from app.permissions.role_matrix import ROLE_PERMISSIONS

    role_codes_with_permission = [
        code for code, codes in ROLE_PERMISSIONS.items() if required_permission in codes
    ]
    if not role_codes_with_permission:
        return
    recipients = await session.scalars(
        select(StaffUser.id)
        .join(StaffRole, StaffRole.staff_user_id == StaffUser.id)
        .join(Role, Role.id == StaffRole.role_id)
        .where(
            Role.code.in_(role_codes_with_permission),
            StaffUser.account_status == "active",
            StaffUser.deleted_at.is_(None),
        )
        .distinct()
    )
    for recipient_id in recipients.all():
        await notify(
            session,
            notification_type="recovery.approval_requested",
            title=title,
            recipient_staff_id=recipient_id,
            body=action.description,
            priority="high",
            record_type="service_recovery_action",
            record_id=action.id,
            dedup_key=f"recovery.approval_requested:{action.id}:{recipient_id}",
        )


def _transition(action: ServiceRecoveryAction, target_status: str) -> None:
    allowed = _ACTION_TRANSITIONS.get(action.status, set())
    if target_status not in allowed:
        raise InvalidActionStatusTransitionError(
            f"Cannot transition recovery action from {action.status!r} to {target_status!r}."
        )


async def _record_transition(
    session: AsyncSession,
    *,
    actor: StaffUser | None,
    action: ServiceRecoveryAction,
    target_status: str,
    reason: str | None = None,
) -> None:
    from_status = action.status
    action.status = target_status
    action.updated_by = actor.id if actor else action.updated_by
    session.add(
        ServiceRecoveryActionHistory(
            action_id=action.id,
            from_status=from_status,
            to_status=target_status,
            actor_id=actor.id if actor else None,
            reason=reason,
        )
    )
    await session.flush()


async def approve_action(
    session: AsyncSession, *, actor: StaffUser, action: ServiceRecoveryAction
) -> ServiceRecoveryAction:
    if action.status != "approval_required":
        raise ApprovalNotRequiredError(
            f"Recovery action {action.id} does not require approval right now."
        )
    if action.proposed_by_staff_id == actor.id:
        rule = (
            await session.get(CompensationApprovalRule, action.approval_rule_id)
            if action.approval_rule_id
            else None
        )
        if rule is None or not rule.allow_self_approval:
            raise SelfApprovalNotAllowedError(
                "You cannot approve a recovery action you proposed yourself."
            )

    action.approved_by_staff_id = actor.id
    action.approved_at = datetime.now(UTC)
    await _record_transition(session, actor=actor, action=action, target_status="approved")
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="recovery.approved",
        target_type="service_recovery_action",
        target_id=action.id,
        safe_metadata={},
    )
    await notify(
        session,
        notification_type="recovery.approved",
        title="Recovery action approved",
        recipient_staff_id=action.proposed_by_staff_id,
        body=action.description,
        priority="normal",
        record_type="service_recovery_action",
        record_id=action.id,
        dedup_key=f"recovery.approved:{action.id}",
    )
    return action


async def reject_action(
    session: AsyncSession, *, actor: StaffUser, action: ServiceRecoveryAction, reason: str
) -> ServiceRecoveryAction:
    if action.status != "approval_required":
        raise ApprovalNotRequiredError(
            f"Recovery action {action.id} does not require approval right now."
        )
    action.rejected_reason = reason
    await _record_transition(
        session, actor=actor, action=action, target_status="rejected", reason=reason
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="recovery.rejected",
        target_type="service_recovery_action",
        target_id=action.id,
        safe_metadata={"reason": reason},
    )
    await notify(
        session,
        notification_type="recovery.rejected",
        title="Recovery action rejected",
        recipient_staff_id=action.proposed_by_staff_id,
        body=reason,
        priority="normal",
        record_type="service_recovery_action",
        record_id=action.id,
        dedup_key=f"recovery.rejected:{action.id}",
    )
    return action


async def execute_action(
    session: AsyncSession, *, actor: StaffUser, action: ServiceRecoveryAction
) -> ServiceRecoveryAction:
    if action.status not in ("proposed", "approved"):
        if action.status in ("completed", "executing"):
            raise AlreadyExecutedError(f"Recovery action {action.id} was already executed.")
        raise NotApprovedError(
            f"Recovery action {action.id} must be approved before it can be executed."
        )

    await _record_transition(session, actor=actor, action=action, target_status="executing")

    try:
        reference_type, reference_id = await _dispatch_execution(
            session, actor=actor, action=action
        )
    except Exception as exc:  # noqa: BLE001 — converted into a domain failure state, not swallowed
        action.failed_reason = str(exc)
        await _record_transition(session, actor=actor, action=action, target_status="failed")
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="recovery.execution_failed",
            target_type="service_recovery_action",
            target_id=action.id,
            safe_metadata={"reason": str(exc)},
        )
        return action

    action.execution_reference_type = reference_type
    action.execution_reference_id = reference_id
    action.executed_at = datetime.now(UTC)
    await _record_transition(session, actor=actor, action=action, target_status="completed")
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="recovery.executed",
        target_type="service_recovery_action",
        target_id=action.id,
        safe_metadata={
            "execution_reference_type": reference_type,
            "execution_reference_id": str(reference_id) if reference_id else None,
        },
    )

    customer = await session.get(Customer, action.customer_id)
    if customer is not None and customer.customer_segment not in ("vip",):
        customer.customer_segment = "complaint_recovery"
    return action


async def _dispatch_execution(
    session: AsyncSession, *, actor: StaffUser, action: ServiceRecoveryAction
) -> tuple[str, uuid.UUID | None]:
    idempotency_key = action.idempotency_key

    if action.recovery_type == "loyalty_credit":
        from app.loyalty import accounts as loyalty_accounts
        from app.loyalty import ledger as loyalty_ledger
        from app.loyalty.schemas import EnrollIn

        account = await loyalty_accounts.enroll(
            session, actor=actor, payload=EnrollIn(customer_id=action.customer_id)
        )
        entry = await loyalty_ledger.post_entry(
            session,
            account_id=account.id,
            entry_type="service_recovery_credit",
            points=action.points or 0,
            idempotency_key=idempotency_key,
            actor_id=actor.id,
            source_type="complaint",
            source_id=action.complaint_id,
            description=action.description,
        )
        return "loyalty_ledger_entry", entry.id

    if action.recovery_type in ("approved_refund", "discount"):
        entry_id = await _execute_order_adjustment(session, actor=actor, action=action)
        if entry_id is not None:
            return "order_payment", entry_id
        return "manual", None

    # apology_only, replacement, refund_request, coupon, complimentary_item,
    # manager_follow_up, operational_correction — none has an automated
    # ledger to post to; fulfilment happens operationally (handing over an
    # item, placing a phone call, or a staff member issuing a coupon
    # through the Offers module themselves). Recorded as a manual reference
    # rather than invented as a fake integration (CLAUDE.md section 16).
    return "manual", None


async def _execute_order_adjustment(
    session: AsyncSession, *, actor: StaffUser, action: ServiceRecoveryAction
) -> uuid.UUID | None:
    from app.db.models import Order, OrderPayment
    from app.orders.service import update_payment_status

    complaint = await session.get(Complaint, action.complaint_id)
    if complaint is None or complaint.order_id is None:
        return None
    order = await session.get(Order, complaint.order_id)
    if order is None:
        return None
    payment = await session.scalar(
        select(OrderPayment)
        .where(OrderPayment.order_id == order.id, OrderPayment.status == "paid")
        .order_by(OrderPayment.recorded_at.desc())
        .limit(1)
    )
    if payment is None:
        return None
    await update_payment_status(
        session, actor=actor, order=order, payment=payment, new_status="refunded", request=None
    )
    return payment.id


async def reverse_action(
    session: AsyncSession, *, actor: StaffUser, action: ServiceRecoveryAction, reason: str
) -> ServiceRecoveryAction:
    if action.status != "completed":
        raise InvalidActionStatusTransitionError(
            f"Only a completed recovery action can be reversed (current status: {action.status!r})."
        )

    if action.execution_reference_type == "loyalty_ledger_entry" and action.execution_reference_id:
        from app.db.models import LoyaltyLedgerEntry
        from app.loyalty import ledger as loyalty_ledger

        original = await session.get(LoyaltyLedgerEntry, action.execution_reference_id)
        if original is not None:
            await loyalty_ledger.reverse_entry(
                session,
                original=original,
                actor_id=actor.id,
                reason=reason,
                idempotency_key=f"{action.idempotency_key}:reverse",
            )

    action.reversed_at = datetime.now(UTC)
    action.reversed_by_staff_id = actor.id
    action.reversal_reason = reason
    await _record_transition(
        session, actor=actor, action=action, target_status="reversed", reason=reason
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="recovery.reversed",
        target_type="service_recovery_action",
        target_id=action.id,
        safe_metadata={"reason": reason},
    )
    return action


async def list_action_history(
    session: AsyncSession, action_id: uuid.UUID
) -> list[ServiceRecoveryActionHistory]:
    result = await session.scalars(
        select(ServiceRecoveryActionHistory)
        .where(ServiceRecoveryActionHistory.action_id == action_id)
        .order_by(ServiceRecoveryActionHistory.created_at.asc())
    )
    return list(result.all())


# --- Approval rules ----------------------------------------------------------


async def get_approval_rule(
    session: AsyncSession, rule_id: uuid.UUID
) -> CompensationApprovalRule | None:
    return await session.get(CompensationApprovalRule, rule_id)


async def list_approval_rules(
    session: AsyncSession, *, is_active: bool | None = None
) -> list[CompensationApprovalRule]:
    query = select(CompensationApprovalRule)
    if is_active is not None:
        query = query.where(CompensationApprovalRule.is_active == is_active)
    result = await session.scalars(query.order_by(CompensationApprovalRule.name))
    return list(result.all())


async def create_approval_rule(
    session: AsyncSession, *, payload: ApprovalRuleCreateIn
) -> CompensationApprovalRule:
    rule = CompensationApprovalRule(
        code=payload.code,
        name=payload.name,
        recovery_type=payload.recovery_type,
        min_value_minor=payload.min_value_minor,
        max_value_minor=payload.max_value_minor,
        applicable_severities=payload.applicable_severities,
        required_permission=payload.required_permission,
        allow_self_approval=payload.allow_self_approval,
    )
    session.add(rule)
    await session.flush()
    return rule


async def update_approval_rule(
    session: AsyncSession, *, rule: CompensationApprovalRule, payload: ApprovalRuleUpdateIn
) -> CompensationApprovalRule:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(rule, field, value)
    await session.flush()
    return rule
