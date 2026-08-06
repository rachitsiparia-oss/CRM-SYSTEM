"""Knowledge base attachment upload/list/delete — this phase's own
instruction section 7, using the same private-storage-path/signed-URL
discipline `app.storage` established for product images (TOOLS.md section
5.3). Generalizes beyond images (PDF, DOCX, CSV) since knowledge documents
are not photos. Every upload is passed through `app.storage.scanning`
before being stored — Phase 16 hardening: `scan_status` is now always
explicitly set (never left at its DB default of `"pending"` forever), and
an `"infected"` result blocks the upload before it ever reaches storage.
No scanning provider is configured or approved anywhere in `docs/TOOLS.md`
yet, so every upload is honestly marked `"skipped"` rather than a
fabricated `"clean"` (CLAUDE.md section 16) — see that module for detail.
"""

import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeAttachment, StaffUser
from app.storage.scanning import scan_upload
from app.storage.service import create_signed_url, delete_object, upload_object

KNOWLEDGE_ATTACHMENTS_BUCKET = "knowledge-attachments"
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024

_IMAGE_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv": "text/csv",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class AttachmentValidationError(ValueError):
    """Raised for any upload that fails validation — the router turns this
    into a 400, never a raw 500."""


@dataclass(frozen=True)
class ValidatedAttachment:
    mime_type: str
    size_bytes: int


def _extension_of(filename: str) -> str:
    dot_index = filename.rfind(".")
    return filename[dot_index:].lower() if dot_index != -1 else ""


def validate_attachment_upload(
    *, data: bytes, filename: str, declared_content_type: str
) -> ValidatedAttachment:
    if len(data) == 0:
        raise AttachmentValidationError("The uploaded file is empty.")
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise AttachmentValidationError(
            f"The file is too large — the limit is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )
    extension = _extension_of(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise AttachmentValidationError(
            "Unsupported file type — only PDF, DOCX, CSV, JPG, PNG, and WEBP are allowed."
        )
    if ALLOWED_EXTENSIONS[extension] != declared_content_type:
        raise AttachmentValidationError(
            "The file extension does not match its declared content type."
        )

    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise AttachmentValidationError("The file is not a valid PDF (signature mismatch).")
    elif extension == ".docx":
        # DOCX is a ZIP container — checking the ZIP local-file-header
        # signature is the lightweight, dependency-free signature check
        # available without a full OOXML parser.
        if not data.startswith(b"PK\x03\x04"):
            raise AttachmentValidationError("The file is not a valid DOCX (signature mismatch).")
    elif extension == ".csv":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AttachmentValidationError(
                "The file is not valid UTF-8 text and cannot be a CSV."
            ) from exc
        if b"\x00" in data:
            raise AttachmentValidationError("The file contains binary content and is not a CSV.")
    else:
        try:
            with Image.open(io.BytesIO(data)) as probe:
                probe.verify()
            with Image.open(io.BytesIO(data)) as image:
                if image.format != _IMAGE_TYPES[declared_content_type]:
                    raise AttachmentValidationError(
                        "The file's actual format does not match its declared content type."
                    )
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise AttachmentValidationError(
                "The file could not be read as a valid image despite its extension."
            ) from exc

    return ValidatedAttachment(mime_type=declared_content_type, size_bytes=len(data))


async def upload_attachment(
    session: AsyncSession,
    *,
    actor: StaffUser,
    article_id: uuid.UUID,
    version_id: uuid.UUID | None,
    data: bytes,
    filename: str,
    declared_content_type: str,
) -> KnowledgeAttachment:
    try:
        validated = validate_attachment_upload(
            data=data, filename=filename, declared_content_type=declared_content_type
        )
    except AttachmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    scan_result = await scan_upload(data)
    if scan_result.status == "infected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This file was rejected by malware scanning and was not uploaded.",
        )

    extension = _extension_of(filename)
    path = f"articles/{article_id}/{uuid.uuid4()}{extension}"
    await upload_object(
        bucket=KNOWLEDGE_ATTACHMENTS_BUCKET, path=path, data=data, content_type=validated.mime_type
    )
    attachment = KnowledgeAttachment(
        article_id=article_id,
        version_id=version_id,
        file_name=filename,
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        storage_bucket=KNOWLEDGE_ATTACHMENTS_BUCKET,
        storage_path=path,
        upload_status="uploaded",
        scan_status=scan_result.status,
        created_by=actor.id,
    )
    session.add(attachment)
    await session.flush()
    return attachment


async def list_attachments(
    session: AsyncSession, article_id: uuid.UUID
) -> list[KnowledgeAttachment]:
    result = await session.scalars(
        select(KnowledgeAttachment).where(
            KnowledgeAttachment.article_id == article_id, KnowledgeAttachment.deleted_at.is_(None)
        )
    )
    return list(result.all())


async def get_attachment_signed_url(attachment: KnowledgeAttachment) -> str:
    return await create_signed_url(bucket=attachment.storage_bucket, path=attachment.storage_path)


async def delete_attachment(
    session: AsyncSession, *, actor: StaffUser, attachment: KnowledgeAttachment
) -> None:
    await delete_object(bucket=attachment.storage_bucket, path=attachment.storage_path)
    attachment.deleted_at = datetime.now(UTC)
    attachment.deleted_by = actor.id
    await session.flush()
