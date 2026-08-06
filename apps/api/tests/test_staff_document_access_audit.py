import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import AuditEvent, StaffDocument, StaffUser
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _fake_signed_url(document: StaffDocument) -> str:
    return f"https://storage.test/{document.storage_path}?signed=1"


async def test_document_signed_url_access_is_audited(
    authed_client: AsyncClient,
    make_staff_user: MakeStaffUser,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.staff_operations.router.documents.get_document_signed_url", _fake_signed_url
    )
    hr = await make_staff_user(role_code="hr_manager")
    target = await make_staff_user(role_code="kitchen_staff")

    document = StaffDocument(
        id=uuid.uuid4(),
        staff_user_id=target.id,
        document_type="identity_proof",
        file_name="id.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        storage_bucket="staff-documents",
        storage_path=f"staff/{target.id}/{uuid.uuid4()}.pdf",
        upload_status="uploaded",
        scan_status="skipped",
    )
    db_session.add(document)
    await db_session.flush()

    response = await authed_client.get(
        f"/api/v1/staff-operations/documents/{document.id}/signed-url",
        headers=_headers(hr),
    )
    assert response.status_code == 200
    assert response.json()["data"]["signed_url"].startswith("https://storage.test/")

    event = await db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.action_code == "staff.document_accessed",
            AuditEvent.target_id == document.id,
        )
    )
    assert event is not None
    assert event.actor_id == hr.id
    assert event.target_type == "staff_document"
    assert event.safe_metadata is not None
    assert event.safe_metadata["staff_user_id"] == str(target.id)
    assert event.safe_metadata["document_type"] == "identity_proof"


async def test_document_signed_url_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    unauthorized = await make_staff_user(role_code="kitchen_staff")
    target = await make_staff_user(role_code="kitchen_staff")

    document = StaffDocument(
        id=uuid.uuid4(),
        staff_user_id=target.id,
        document_type="identity_proof",
        file_name="id.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        storage_bucket="staff-documents",
        storage_path=f"staff/{target.id}/{uuid.uuid4()}.pdf",
        upload_status="uploaded",
        scan_status="skipped",
    )
    db_session.add(document)
    await db_session.flush()

    response = await authed_client.get(
        f"/api/v1/staff-operations/documents/{document.id}/signed-url",
        headers=_headers(unauthorized),
    )
    assert response.status_code == 403
