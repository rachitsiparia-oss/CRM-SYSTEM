from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ExportFormat = Literal["csv", "xlsx", "pdf"]
ExportStatus = Literal["pending", "generating", "completed", "failed"]


class ExportRequestIn(BaseModel):
    report_run_id: uuid.UUID
    export_format: ExportFormat = "csv"


class ExportArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_run_id: uuid.UUID | None
    requested_by_staff_id: uuid.UUID
    export_format: ExportFormat
    status: ExportStatus
    file_size_bytes: int | None
    row_count: int | None
    checksum_sha256: str | None
    expires_at: datetime | None
    failure_details: str | None
    completed_at: datetime | None
    created_at: datetime


class ExportDownloadOut(BaseModel):
    download_url: str
    expires_at: datetime | None
