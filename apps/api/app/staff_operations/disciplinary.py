"""Disciplinary records — PROJECT_PLAN.md "Disciplinary records with
strict permissions." Never edited after creation except for status/
resolution (no PATCH on the incident description itself), and never
surfaced through the general staff directory endpoints."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StaffDisciplinaryRecord, StaffUser
from app.staff_operations.schemas import DisciplinaryRecordCreateIn


async def create_disciplinary_record(
    session: AsyncSession, *, actor: StaffUser, payload: DisciplinaryRecordCreateIn
) -> StaffDisciplinaryRecord:
    record = StaffDisciplinaryRecord(
        staff_user_id=payload.staff_user_id,
        incident_date=payload.incident_date,
        category=payload.category,
        description=payload.description,
        severity=payload.severity,
        action_taken=payload.action_taken,
        recorded_by=actor.id,
        created_by=actor.id,
    )
    session.add(record)
    await session.flush()
    return record


async def resolve_disciplinary_record(
    session: AsyncSession, *, record: StaffDisciplinaryRecord, resolution_status: str
) -> StaffDisciplinaryRecord:
    if resolution_status not in ("resolved", "appealed"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid status.")
    record.status = resolution_status
    if resolution_status == "resolved":
        record.resolved_at = datetime.now(UTC)
    await session.flush()
    return record


async def list_disciplinary_records(
    session: AsyncSession, staff_user_id: uuid.UUID
) -> list[StaffDisciplinaryRecord]:
    result = await session.scalars(
        select(StaffDisciplinaryRecord).where(
            StaffDisciplinaryRecord.staff_user_id == staff_user_id
        )
    )
    return list(result.all())
