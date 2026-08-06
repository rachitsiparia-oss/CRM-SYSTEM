from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import StaffUser
from app.storage.scanning import ScanResult
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _create_article(
    authed_client: AsyncClient, staff_user: StaffUser, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": "Test SOP",
        "content": "Do the thing safely.",
        "article_type": "sop",
    }
    payload.update(overrides)
    response = await authed_client.post(
        "/api/v1/knowledge/articles", json=payload, headers=_headers(staff_user)
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()["data"]
    return result


async def test_uploaded_attachment_records_skipped_scan_status_when_no_provider_configured(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.knowledge.attachments.upload_object", _fake_upload_object)
    staff_user = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, staff_user)

    response = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/attachments",
        headers=_headers(staff_user),
        files={"file": ("notes.pdf", b"%PDF-1.4 fake pdf body", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["upload_status"] == "uploaded"
    assert body["scan_status"] == "skipped"  # NoOpScanner — no provider configured


async def test_infected_scan_result_blocks_the_upload(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.knowledge.attachments.upload_object", _fake_upload_object)
    monkeypatch.setattr(
        "app.knowledge.attachments.scan_upload",
        _fake_infected_scan,
    )
    staff_user = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, staff_user)

    response = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/attachments",
        headers=_headers(staff_user),
        files={"file": ("notes.pdf", b"%PDF-1.4 fake pdf body", "application/pdf")},
    )
    assert response.status_code == 400
    assert "malware" in response.json()["error"]["message"].lower()

    list_response = await authed_client.get(
        f"/api/v1/knowledge/articles/{article['id']}/attachments", headers=_headers(staff_user)
    )
    assert list_response.json()["data"] == []


async def _fake_upload_object(*, bucket: str, path: str, data: bytes, content_type: str) -> None:
    del bucket, path, data, content_type


async def _fake_infected_scan(data: bytes) -> ScanResult:
    del data
    return ScanResult(status="infected", detail="test double: forced infected result")
