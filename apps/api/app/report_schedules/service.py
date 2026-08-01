"""Scheduled report execution — GROWTH_AND_INTELLIGENCE.md section 13.19.
`execute_due_occurrence()` is the deterministic, idempotent, directly-
callable entry point Phase 15 will register on a timer (the "engine, not
scheduler" split already used in Phases 9/10/12/13); nothing here depends
on a live cron process. Permission is rechecked at generation time (the
report owner's *current* effective permissions, not a cached value from
when the schedule was created) and again per recipient at delivery time —
GROWTH_AND_INTELLIGENCE.md section 13.19's explicit "schedules must not
expose data to unauthorized recipients after a role change."
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.registry import get_metric
from app.communications.providers import get_provider
from app.core.pagination import DEFAULT_PAGE_SIZE
from app.db.models import (
    ReportDefinition,
    ReportDeliveryAttempt,
    Role,
    ScheduledReport,
    ScheduledReportRecipient,
    StaffRole,
    StaffUser,
)
from app.permissions.service import get_effective_permissions
from app.report_exports import service as export_service
from app.report_schedules.errors import NoRecipientsError, ScheduleOwnerLacksPermissionError
from app.reports import service as report_service


def compute_occurrence_key(scheduled_report: ScheduledReport, *, as_of: date | None = None) -> str:
    today = as_of or datetime.now(UTC).date()
    if scheduled_report.schedule_frequency == "daily":
        period_label = today.isoformat()
    elif scheduled_report.schedule_frequency == "weekly":
        iso = today.isocalendar()
        period_label = f"{iso.year}-W{iso.week:02d}"
    else:  # "monthly"
        period_label = f"{today.year}-{today.month:02d}"
    return f"{scheduled_report.id}:{period_label}"


async def _resolve_staff_recipients(
    session: AsyncSession, recipient: ScheduledReportRecipient
) -> list[StaffUser]:
    if recipient.recipient_staff_id is not None:
        staff = await session.get(StaffUser, recipient.recipient_staff_id)
        return [staff] if staff is not None and staff.deleted_at is None else []
    if recipient.recipient_role_code is not None:
        rows = await session.scalars(
            select(StaffUser)
            .join(StaffRole, StaffRole.staff_user_id == StaffUser.id)
            .join(Role, Role.id == StaffRole.role_id)
            .where(
                Role.code == recipient.recipient_role_code,
                Role.is_active.is_(True),
                StaffUser.deleted_at.is_(None),
                StaffUser.account_status == "active",
            )
        )
        return list(rows.all())
    return []


async def execute_due_occurrence(
    session: AsyncSession, scheduled_report: ScheduledReport
) -> list[ReportDeliveryAttempt]:
    definition = await session.get(ReportDefinition, scheduled_report.report_definition_id)
    if definition is None or definition.owner_staff_id is None:
        raise ScheduleOwnerLacksPermissionError(
            "This scheduled report's definition has no resolvable owner."
        )
    owner = await session.get(StaffUser, definition.owner_staff_id)
    if owner is None:
        raise ScheduleOwnerLacksPermissionError("This scheduled report's owner no longer exists.")

    owner_permissions = await get_effective_permissions(session, owner.id)
    for metric_code in definition.metric_codes:
        metric = get_metric(metric_code)
        if metric.required_permission not in owner_permissions:
            raise ScheduleOwnerLacksPermissionError(
                f"The report owner no longer holds {metric.required_permission!r}; "
                "this schedule cannot run until re-authorized."
            )

    run, _results = await report_service.execute_report(
        session,
        actor=owner,
        definition=definition,
        permissions=owner_permissions,
        window_code=definition.default_window,
        custom_start=None,
        custom_end=None,
        trigger_source="scheduled",
    )
    artifact = await export_service.generate_export(
        session, actor=owner, report_run=run, export_format=scheduled_report.output_format
    )

    occurrence_key = compute_occurrence_key(scheduled_report)
    recipients_rows = (
        await session.scalars(
            select(ScheduledReportRecipient).where(
                ScheduledReportRecipient.scheduled_report_id == scheduled_report.id
            )
        )
    ).all()
    if not recipients_rows:
        raise NoRecipientsError("This scheduled report has no configured recipients.")

    resolved: dict[str, uuid.UUID | None] = {}
    for recipient in recipients_rows:
        if recipient.recipient_email_override is not None:
            resolved.setdefault(recipient.recipient_email_override, None)
            continue
        for staff in await _resolve_staff_recipients(session, recipient):
            resolved.setdefault(staff.email, staff.id)

    provider = get_provider(None)
    attempts: list[ReportDeliveryAttempt] = []
    for recipient_reference, staff_id in resolved.items():
        existing = await session.scalar(
            select(ReportDeliveryAttempt).where(
                ReportDeliveryAttempt.scheduled_report_id == scheduled_report.id,
                ReportDeliveryAttempt.occurrence_key == occurrence_key,
                ReportDeliveryAttempt.recipient_reference == recipient_reference,
            )
        )
        if existing is not None:
            attempts.append(existing)
            continue

        attempt = ReportDeliveryAttempt(
            scheduled_report_id=scheduled_report.id,
            report_run_id=run.id,
            export_artifact_id=artifact.id,
            occurrence_key=occurrence_key,
            recipient_reference=recipient_reference,
            delivery_channel="email",
            status="pending",
        )
        session.add(attempt)
        await session.flush()

        # Re-check permission at delivery time for a resolvable staff
        # recipient — a raw email override has no staff account to check
        # against, per this table's own documented scope.
        if staff_id is not None:
            recipient_permissions = await get_effective_permissions(session, staff_id)
            if "reports.view" not in recipient_permissions:
                attempt.status = "failed"
                attempt.failure_details = "Recipient no longer holds reports.view."
                attempt.attempted_at = datetime.now(UTC)
                await session.flush()
                attempts.append(attempt)
                continue

        result = await provider.send_text(
            recipient_reference=recipient_reference,
            body=f"Your scheduled report {scheduled_report.name!r} is ready: {definition.name}.",
        )
        attempt.status = "sent" if result.accepted else "failed"
        attempt.failure_details = result.failure_reason
        attempt.attempted_at = datetime.now(UTC)
        await session.flush()
        attempts.append(attempt)

    return attempts


async def create_scheduled_report(
    session: AsyncSession, *, actor: StaffUser, payload: object
) -> ScheduledReport:
    from app.report_schedules.schemas import ScheduledReportCreateIn

    assert isinstance(payload, ScheduledReportCreateIn)
    scheduled = ScheduledReport(
        report_definition_id=payload.report_definition_id,
        name=payload.name,
        schedule_frequency=payload.schedule_frequency,
        schedule_day_of_week=payload.schedule_day_of_week,
        schedule_day_of_month=payload.schedule_day_of_month,
        schedule_time_of_day=payload.schedule_time_of_day,
        timezone=payload.timezone,
        output_format=payload.output_format,
        fixed_filters=payload.fixed_filters,
        include_ai_narrative=payload.include_ai_narrative,
        is_enabled=False,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(scheduled)
    await session.flush()
    return scheduled


async def add_recipient(
    session: AsyncSession, *, scheduled_report: ScheduledReport, payload: object
) -> ScheduledReportRecipient:
    from app.report_schedules.schemas import ScheduledReportRecipientCreateIn

    assert isinstance(payload, ScheduledReportRecipientCreateIn)
    recipient = ScheduledReportRecipient(
        scheduled_report_id=scheduled_report.id,
        recipient_staff_id=payload.recipient_staff_id,
        recipient_role_code=payload.recipient_role_code,
        recipient_email_override=payload.recipient_email_override,
    )
    session.add(recipient)
    await session.flush()
    return recipient


async def list_recipients(
    session: AsyncSession, scheduled_report_id: uuid.UUID
) -> list[ScheduledReportRecipient]:
    rows = await session.scalars(
        select(ScheduledReportRecipient).where(
            ScheduledReportRecipient.scheduled_report_id == scheduled_report_id
        )
    )
    return list(rows.all())


async def set_enabled(
    session: AsyncSession, *, scheduled_report: ScheduledReport, actor: StaffUser, is_enabled: bool
) -> ScheduledReport:
    scheduled_report.is_enabled = is_enabled
    scheduled_report.updated_by = actor.id
    scheduled_report.version += 1
    await session.flush()
    return scheduled_report


async def get_scheduled_report(
    session: AsyncSession, scheduled_report_id: uuid.UUID
) -> ScheduledReport | None:
    return await session.get(ScheduledReport, scheduled_report_id)


async def list_scheduled_reports(
    session: AsyncSession, *, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
) -> tuple[list[ScheduledReport], int]:
    total = (await session.scalar(select(func.count()).select_from(ScheduledReport))) or 0
    rows = await session.scalars(
        select(ScheduledReport)
        .order_by(ScheduledReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.all()), total


async def list_delivery_attempts(
    session: AsyncSession,
    *,
    scheduled_report_id: uuid.UUID,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[ReportDeliveryAttempt], int]:
    conditions = (ReportDeliveryAttempt.scheduled_report_id == scheduled_report_id,)
    total = (
        await session.scalar(
            select(func.count()).select_from(ReportDeliveryAttempt).where(*conditions)
        )
    ) or 0
    rows = await session.scalars(
        select(ReportDeliveryAttempt)
        .where(*conditions)
        .order_by(ReportDeliveryAttempt.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.all()), total
