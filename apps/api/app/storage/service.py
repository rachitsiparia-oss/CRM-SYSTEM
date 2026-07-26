"""Supabase Storage adapter — the first real Storage integration in this
codebase (`staff_users.avatar_storage_path` from Phase 3 has never had an
upload path wired to it). TOOLS.md section 5.3: private buckets by default,
short-lived signed URLs, backend authorization before file access, no
public bucket added for convenience.

Deliberately thin: upload, delete, and sign — no derivative generation, no
CDN, matching this phase's own "no optimization pipeline beyond basic
validation" instruction.
"""

import uuid

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

# Private by default (TOOLS.md section 5.3) — created on first use if it
# doesn't exist yet, since Supabase Storage buckets aren't provisioned by
# an Alembic migration.
MENU_IMAGES_BUCKET = "menu-images"
SIGNED_URL_EXPIRY_SECONDS = 3600


class StorageError(RuntimeError):
    """Raised when Supabase Storage is unreachable or refuses a request —
    the caller turns this into a 502, never a raw 500."""


def _require_storage_settings() -> tuple[str, str]:
    settings = get_settings()
    if not (settings.supabase_url and settings.supabase_service_role_key):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File storage is not configured on this environment.",
        )
    return settings.supabase_url, settings.supabase_service_role_key


def _auth_headers(service_role_key: str) -> dict[str, str]:
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }


async def ensure_bucket_exists(bucket: str = MENU_IMAGES_BUCKET) -> None:
    """Idempotent: checks first, creates only if missing. Safe to call on
    every upload — Supabase returns 200 for an existing bucket lookup, so
    the common case is one cheap GET."""
    supabase_url, service_role_key = _require_storage_settings()
    headers = _auth_headers(service_role_key)
    async with httpx.AsyncClient(timeout=10) as client:
        existing = await client.get(f"{supabase_url}/storage/v1/bucket/{bucket}", headers=headers)
        if existing.status_code == 200:
            return
        response = await client.post(
            f"{supabase_url}/storage/v1/bucket",
            headers=headers,
            json={"id": bucket, "name": bucket, "public": False},
        )
        if response.status_code >= 400 and "already exists" not in response.text.lower():
            raise StorageError(f"Could not create storage bucket {bucket!r}: {response.text}")


def build_object_path(*, product_id: uuid.UUID, filename_extension: str) -> str:
    # Server-generated path, never derived from client input beyond the
    # validated extension — SECURITY_PERFORMANCE_AND_QUALITY.md section 9.2
    # ("no user-controlled traversal paths").
    return f"products/{product_id}/{uuid.uuid4()}{filename_extension}"


async def upload_object(*, bucket: str, path: str, data: bytes, content_type: str) -> None:
    supabase_url, service_role_key = _require_storage_settings()
    headers = {**_auth_headers(service_role_key), "Content-Type": content_type}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{supabase_url}/storage/v1/object/{bucket}/{path}", headers=headers, content=data
        )
    if response.status_code >= 400:
        raise StorageError(f"Upload to {bucket}/{path} failed: {response.text}")


async def delete_object(*, bucket: str, path: str) -> None:
    supabase_url, service_role_key = _require_storage_settings()
    headers = _auth_headers(service_role_key)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(
            f"{supabase_url}/storage/v1/object/{bucket}/{path}", headers=headers
        )
    # A 404 here means the object is already gone — treat delete as
    # idempotent rather than surfacing an error for a state the caller
    # already wants.
    if response.status_code >= 400 and response.status_code != 404:
        raise StorageError(f"Delete of {bucket}/{path} failed: {response.text}")


async def create_signed_url(
    *, bucket: str, path: str, expires_in: int = SIGNED_URL_EXPIRY_SECONDS
) -> str:
    """Backend authorization must happen before this is ever called — the
    signed URL itself is the only thing standing between a private object
    and anyone with the link (TOOLS.md section 5.3, "backend authorization
    before file access"; SECURITY_PERFORMANCE_AND_QUALITY.md section 9.5,
    "signed URLs are created only after backend permission checks")."""
    supabase_url, service_role_key = _require_storage_settings()
    headers = _auth_headers(service_role_key)
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{supabase_url}/storage/v1/object/sign/{bucket}/{path}",
            headers=headers,
            json={"expiresIn": expires_in},
        )
    if response.status_code >= 400:
        raise StorageError(f"Could not sign {bucket}/{path}: {response.text}")
    signed_path = response.json()["signedURL"]
    return f"{supabase_url}/storage/v1{signed_path}"
