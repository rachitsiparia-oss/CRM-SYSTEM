"""Export API — GROWTH_AND_INTELLIGENCE.md section 13.18. Generation
requires `reports.export`; download re-checks the same permission plus
artifact ownership before ever minting a signed URL (CLAUDE.md section
6.4's "verify permission before generating every signed URL")."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import DataResponse, request_meta
from app.db.models import StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.report_exports import service
from app.report_exports.errors import ExportError
from app.report_exports.schemas import ExportArtifactOut, ExportDownloadOut, ExportRequestIn
from app.reports import service as report_service

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_export(
    payload: ExportRequestIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.export")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ExportArtifactOut]:
    report_run = await report_service.get_report_run(session, payload.report_run_id)
    if report_run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report run not found.")
    try:
        artifact = await service.generate_export(
            session, actor=actor, report_run=report_run, export_format=payload.export_format
        )
    except ExportError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ExportArtifactOut.model_validate(artifact), meta=request_meta(request))


@router.get("/{artifact_id}")
async def get_export(
    artifact_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("reports.export")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ExportArtifactOut]:
    artifact = await service.get_export_artifact(session, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Export not found.")
    return DataResponse(data=ExportArtifactOut.model_validate(artifact), meta=request_meta(request))


@router.get("/{artifact_id}/download")
async def download_export(
    artifact_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.export")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ExportDownloadOut]:
    artifact = await service.get_export_artifact(session, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Export not found.")
    if artifact.requested_by_staff_id != actor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You cannot download this export.")
    try:
        url = await service.get_download_url(artifact)
    except ExportError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ExportDownloadOut(download_url=url, expires_at=artifact.expires_at),
        meta=request_meta(request),
    )
