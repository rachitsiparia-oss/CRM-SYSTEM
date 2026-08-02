"""Admin read/cancel surface over `JobRecord` — execution itself lives in
`app.jobs.runner`. Kept separate so the execution hot path never imports
anything router-facing."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobRecord


async def list_job_records(
    session: AsyncSession,
    *,
    status: str | None = None,
    job_type: str | None = None,
    queue_name: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[JobRecord], int]:
    conditions = []
    if status is not None:
        conditions.append(JobRecord.status == status)
    if job_type is not None:
        conditions.append(JobRecord.job_type == job_type)
    if queue_name is not None:
        conditions.append(JobRecord.queue_name == queue_name)

    total = await session.scalar(select(func.count()).select_from(JobRecord).where(*conditions))
    rows = (
        await session.scalars(
            select(JobRecord)
            .where(*conditions)
            .order_by(JobRecord.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).all()
    return list(rows), total or 0


async def get_queue_stats(session: AsyncSession) -> list[dict[str, str | int]]:
    rows = (
        await session.execute(
            select(JobRecord.queue_name, JobRecord.status, func.count())
            .group_by(JobRecord.queue_name, JobRecord.status)
            .order_by(JobRecord.queue_name)
        )
    ).all()
    return [
        {"queue_name": queue_name, "status": status, "count": count}
        for queue_name, status, count in rows
    ]
