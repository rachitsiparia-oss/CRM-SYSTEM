"""Controlled AI API — GROWTH_AND_INTELLIGENCE.md section 14. Every
capability requires `ai.analytics.use`; `nl_question_query_plan`
additionally requires `ai.analytics.query`, the more powerful natural-
language capability."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.controlled_ai import service
from app.controlled_ai.errors import ControlledAiError
from app.controlled_ai.schemas import (
    AiCompletionRequestIn,
    AiRequestFeedbackIn,
    AiRequestFeedbackOut,
    AiRequestOut,
)
from app.core.rate_limit import check_rate_limit
from app.core.responses import DataResponse, request_meta
from app.db.models import StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import get_effective_permissions

router = APIRouter(prefix="/api/v1/ai", tags=["controlled-ai"])

_QUERY_PLAN_FEATURE = "nl_question_query_plan"
# CLAUDE.md section 6.5 calls out AI endpoints as their own rate-limit
# classification, distinct from the generic per-IP auth limiter every
# authenticated request already gets — a generation has a real per-call
# cost once a live provider is configured, so this is scoped per staff
# account rather than per IP.
_AI_REQUEST_LIMIT = 20
_AI_REQUEST_WINDOW_SECONDS = 3600


@router.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_ai_request(
    payload: AiCompletionRequestIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("ai.analytics.use")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AiRequestOut]:
    if not await check_rate_limit(
        f"ai:{actor.id}", limit=_AI_REQUEST_LIMIT, window_seconds=_AI_REQUEST_WINDOW_SECONDS
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests. Try again later.",
        )
    permissions = await get_effective_permissions(session, actor.id)
    if payload.feature_code == _QUERY_PLAN_FEATURE and "ai.analytics.query" not in permissions:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="This capability requires ai.analytics.query."
        )
    try:
        ai_request = await service.request_completion(
            session,
            actor=actor,
            feature_code=payload.feature_code,
            permissions=permissions,
            params=payload.params,
        )
    except ControlledAiError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=AiRequestOut.model_validate(ai_request), meta=request_meta(request))


@router.get("/requests/{request_id}")
async def get_ai_request(
    request_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("ai.analytics.use")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AiRequestOut]:
    ai_request = await service.get_ai_request(session, request_id)
    if ai_request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI request not found.")
    if ai_request.requested_by_staff_id != actor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You cannot view this AI request.")
    return DataResponse(data=AiRequestOut.model_validate(ai_request), meta=request_meta(request))


@router.post("/requests/{request_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_ai_feedback(
    request_id: uuid.UUID,
    payload: AiRequestFeedbackIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("ai.analytics.use")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AiRequestFeedbackOut]:
    ai_request = await service.get_ai_request(session, request_id)
    if ai_request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI request not found.")
    if ai_request.requested_by_staff_id != actor.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You cannot provide feedback on this AI request."
        )
    feedback = await service.record_feedback(
        session, actor=actor, ai_request=ai_request, payload=payload
    )
    return DataResponse(
        data=AiRequestFeedbackOut.model_validate(feedback), meta=request_meta(request)
    )
