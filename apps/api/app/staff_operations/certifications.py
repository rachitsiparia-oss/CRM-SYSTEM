"""Staff certifications — this phase's own instruction section 23.
Expiry-window queries feed both `app.staff_operations.analytics` and the
(not-yet-automated) expiry-warning notification, matching the "engine, not
scheduler" pattern Phase 10 established for `process_due_scheduled_messages`.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StaffCertification, StaffUser
from app.staff_operations.schemas import CertificationCreateIn, CertificationVerifyIn


async def create_certification(
    session: AsyncSession, *, actor: StaffUser, payload: CertificationCreateIn
) -> StaffCertification:
    certification = StaffCertification(
        staff_user_id=payload.staff_user_id,
        certification_type=payload.certification_type,
        issuer=payload.issuer,
        certificate_number=payload.certificate_number,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        renewal_of_certification_id=payload.renewal_of_certification_id,
        created_by=actor.id,
    )
    session.add(certification)
    await session.flush()
    return certification


async def verify_certification(
    session: AsyncSession,
    *,
    actor: StaffUser,
    certification: StaffCertification,
    payload: CertificationVerifyIn,
) -> StaffCertification:
    certification.verification_status = payload.verification_status
    certification.verified_by = actor.id
    certification.verified_at = datetime.now(UTC)
    await session.flush()
    return certification


async def list_certifications(
    session: AsyncSession, staff_user_id: uuid.UUID | None
) -> list[StaffCertification]:
    stmt = select(StaffCertification)
    if staff_user_id:
        stmt = stmt.where(StaffCertification.staff_user_id == staff_user_id)
    return list((await session.scalars(stmt)).all())


async def list_certifications_expiring_within(
    session: AsyncSession, *, days: int
) -> list[StaffCertification]:
    cutoff = (datetime.now(UTC) + timedelta(days=days)).date()
    result = await session.scalars(
        select(StaffCertification).where(
            StaffCertification.expiry_date.is_not(None), StaffCertification.expiry_date <= cutoff
        )
    )
    return list(result.all())
