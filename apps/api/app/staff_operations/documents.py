"""Staff HR document upload/list/verify — this phase's own instruction
section 14. Reuses `app.knowledge.attachments`' validator (extension/MIME/
signature checks for PDF/DOCX/CSV/images) rather than a duplicate one.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StaffDocument, StaffUser
from app.knowledge.attachments import AttachmentValidationError, validate_attachment_upload
from app.staff_operations.schemas import DocumentVerifyIn
from app.storage.service import create_signed_url, upload_object

STAFF_DOCUMENTS_BUCKET = "staff-documents"


async def upload_document(
    session: AsyncSession,
    *,
    actor: StaffUser,
    staff_user_id: uuid.UUID,
    document_type: str,
    data: bytes,
    filename: str,
    declared_content_type: str,
    issue_date: str | None,
    expiry_date: str | None,
    replaces_document_id: uuid.UUID | None,
) -> StaffDocument:
    try:
        validated = validate_attachment_upload(
            data=data, filename=filename, declared_content_type=declared_content_type
        )
    except AttachmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    extension = filename[filename.rfind(".") :].lower() if "." in filename else ""
    path = f"staff/{staff_user_id}/{uuid.uuid4()}{extension}"
    await upload_object(
        bucket=STAFF_DOCUMENTS_BUCKET, path=path, data=data, content_type=validated.mime_type
    )
    document = StaffDocument(
        staff_user_id=staff_user_id,
        document_type=document_type,
        file_name=filename,
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        storage_bucket=STAFF_DOCUMENTS_BUCKET,
        storage_path=path,
        upload_status="uploaded",
        issue_date=issue_date,
        expiry_date=expiry_date,
        replaces_document_id=replaces_document_id,
        created_by=actor.id,
    )
    session.add(document)
    if replaces_document_id is not None:
        previous = await session.get(StaffDocument, replaces_document_id)
        if previous is not None:
            previous.reminder_eligible = False
    await session.flush()
    return document


async def list_documents(session: AsyncSession, staff_user_id: uuid.UUID) -> list[StaffDocument]:
    result = await session.scalars(
        select(StaffDocument).where(
            StaffDocument.staff_user_id == staff_user_id, StaffDocument.deleted_at.is_(None)
        )
    )
    return list(result.all())


async def verify_document(
    session: AsyncSession, *, actor: StaffUser, document: StaffDocument, payload: DocumentVerifyIn
) -> StaffDocument:
    document.verification_status = payload.verification_status
    document.verified_by = actor.id
    document.verified_at = datetime.now(UTC)
    await session.flush()
    return document


async def get_document_signed_url(document: StaffDocument) -> str:
    return await create_signed_url(bucket=document.storage_bucket, path=document.storage_path)


async def list_documents_expiring_within(
    session: AsyncSession, *, days: int
) -> list[StaffDocument]:
    cutoff = (datetime.now(UTC) + timedelta(days=days)).date()
    result = await session.scalars(
        select(StaffDocument).where(
            StaffDocument.expiry_date.is_not(None),
            StaffDocument.expiry_date <= cutoff,
            StaffDocument.reminder_eligible.is_(True),
            StaffDocument.deleted_at.is_(None),
        )
    )
    return list(result.all())
