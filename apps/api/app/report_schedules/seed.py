"""Idempotent development seed data — a disabled-by-default scheduled
report example (Phase 14 instruction's seed-data rule: "scheduled report
examples disabled by default unless safe"). Recipients use PROJECT_PLAN.md's
dummy report-recipient addresses (`owner@rkpr-demo.example`,
`manager@rkpr-demo.example`) as email overrides — CLAUDE.md section 23's
"report-recipient addresses belong in Settings and must not be hardcoded"
is satisfied by these living in a seeded, UI-editable row, not literal
code anywhere delivery actually happens.
"""

from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReportDefinition, ScheduledReport, ScheduledReportRecipient, StaffUser

_SCHEDULE_NAME = "Weekly Executive Overview"


async def seed_scheduled_reports(session: AsyncSession) -> None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return
    definition = await session.scalar(
        select(ReportDefinition).where(ReportDefinition.code == "system-executive-overview")
    )
    if definition is None:
        return

    existing = await session.scalar(
        select(ScheduledReport).where(ScheduledReport.name == _SCHEDULE_NAME)
    )
    if existing is not None:
        return

    scheduled = ScheduledReport(
        report_definition_id=definition.id,
        name=_SCHEDULE_NAME,
        schedule_frequency="weekly",
        schedule_day_of_week=0,
        schedule_time_of_day=time(6, 0),
        timezone="Asia/Kolkata",
        output_format="pdf",
        include_ai_narrative=False,
        is_enabled=False,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(scheduled)
    await session.flush()

    session.add_all(
        [
            ScheduledReportRecipient(
                scheduled_report_id=scheduled.id,
                recipient_email_override="owner@rkpr-demo.example",
            ),
            ScheduledReportRecipient(
                scheduled_report_id=scheduled.id,
                recipient_email_override="manager@rkpr-demo.example",
            ),
        ]
    )
    await session.flush()
