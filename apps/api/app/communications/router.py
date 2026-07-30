import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications import (
    aggregation,
    analytics,
    consent,
    scheduling,
    service,
    webhooks,
)
from app.communications import (
    templates as templates_service,
)
from app.communications.messaging import send_message
from app.communications.providers import get_provider
from app.communications.schemas import (
    CommunicationAnalyticsOut,
    CommunicationChannelOut,
    CommunicationChannelUpdateIn,
    CommunicationConsentCreateIn,
    CommunicationConsentOut,
    CommunicationPreferenceOut,
    CommunicationPreferenceUpdateIn,
    CommunicationSuppressionCreateIn,
    CommunicationSuppressionOut,
    ConversationAssignIn,
    ConversationCreateIn,
    ConversationOut,
    ConversationPriorityIn,
    ConversationTimelineEntryOut,
    ConversationTransitionIn,
    CustomerCommunicationStatsOut,
    InternalNoteCreateIn,
    ManualCallLogCreateIn,
    ManualCallLogOut,
    MessageCreateIn,
    MessageOut,
    MessageTemplateCreateIn,
    MessageTemplateOut,
    MessageTemplateUpdateIn,
    ScheduledMessageCreateIn,
    ScheduledMessageOut,
    TemplatePreviewIn,
    TemplatePreviewOut,
)
from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import (
    CommunicationChannel,
    CommunicationSuppression,
    Conversation,
    ManualCallLog,
    Message,
    MessageTemplate,
    ScheduledMessage,
    StaffUser,
)
from app.db.session import get_db
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/communications", tags=["communications"])


async def _get_conversation_or_404(
    session: AsyncSession, conversation_id: uuid.UUID
) -> Conversation:
    conversation = await service.get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


async def _get_channel_or_404(session: AsyncSession, channel_id: uuid.UUID) -> CommunicationChannel:
    channel = await session.get(CommunicationChannel, channel_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Communication channel not found.")
    return channel


# --- Channels ----------------------------------------------------------------


@router.get("/channels")
async def list_channels(
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.channels.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[CommunicationChannelOut]]:
    rows = (
        await session.scalars(
            select(CommunicationChannel).order_by(CommunicationChannel.sort_order)
        )
    ).all()
    return DataResponse(
        data=[CommunicationChannelOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.patch("/channels/{channel_id}")
async def update_channel(
    channel_id: uuid.UUID,
    payload: CommunicationChannelUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.channels.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CommunicationChannelOut]:
    channel = await _get_channel_or_404(session, channel_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)
    channel.updated_by = actor.id
    await session.flush()
    return DataResponse(
        data=CommunicationChannelOut.model_validate(channel), meta=request_meta(request)
    )


# --- Conversations / Inbox ----------------------------------------------------


@router.get("/inbox")
async def list_inbox(
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    conversation_status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    channel_id: uuid.UUID | None = Query(default=None),
    assigned_staff_id: uuid.UUID | None = Query(default=None),
    unread_only: bool = Query(default=False),
    unassigned_only: bool = Query(default=False),
    mine_only: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=200),
) -> PaginatedResponse[ConversationOut]:
    stmt = select(Conversation)
    count_stmt = select(func.count()).select_from(Conversation)

    if search:
        pattern = f"%{search}%"
        clause = or_(
            Conversation.conversation_number.ilike(pattern),
            Conversation.guest_name.ilike(pattern),
            Conversation.phone_e164.ilike(pattern),
            Conversation.subject.ilike(pattern),
        )
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if conversation_status:
        stmt = stmt.where(Conversation.status == conversation_status)
        count_stmt = count_stmt.where(Conversation.status == conversation_status)
    if priority:
        stmt = stmt.where(Conversation.priority == priority)
        count_stmt = count_stmt.where(Conversation.priority == priority)
    if channel_id:
        stmt = stmt.where(Conversation.channel_id == channel_id)
        count_stmt = count_stmt.where(Conversation.channel_id == channel_id)
    if assigned_staff_id:
        stmt = stmt.where(Conversation.assigned_staff_id == assigned_staff_id)
        count_stmt = count_stmt.where(Conversation.assigned_staff_id == assigned_staff_id)
    if unread_only:
        stmt = stmt.where(Conversation.unread_count > 0)
        count_stmt = count_stmt.where(Conversation.unread_count > 0)
    if unassigned_only:
        stmt = stmt.where(Conversation.assigned_staff_id.is_(None))
        count_stmt = count_stmt.where(Conversation.assigned_staff_id.is_(None))
    if mine_only:
        stmt = stmt.where(Conversation.assigned_staff_id == actor.id)
        count_stmt = count_stmt.where(Conversation.assigned_staff_id == actor.id)

    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(Conversation.last_activity_at.desc().nulls_last())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[ConversationOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ConversationOut]:
    conversation = await _get_conversation_or_404(session, conversation_id)
    return DataResponse(
        data=ConversationOut.model_validate(conversation), meta=request_meta(request)
    )


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ConversationOut]:
    conversation = await service.create_conversation(
        session, actor=actor, payload=payload, request=request
    )
    if payload.initial_message_body:
        channel = await _get_channel_or_404(session, conversation.channel_id)
        recipient = conversation.phone_e164 or conversation.email
        await send_message(
            session,
            conversation=conversation,
            channel=channel,
            recipient_reference=recipient,
            body_text=payload.initial_message_body,
            actor=actor,
        )
    return DataResponse(
        data=ConversationOut.model_validate(conversation), meta=request_meta(request)
    )


@router.post("/conversations/{conversation_id}/transition")
async def transition_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ConversationOut]:
    conversation = await _get_conversation_or_404(session, conversation_id)
    conversation = await service.transition_conversation_status(
        session,
        actor=actor,
        conversation=conversation,
        target_status=payload.target_status,
        reason=payload.reason,
        snoozed_until=payload.snoozed_until,
        spam_reason=payload.spam_reason,
        request=request,
    )
    return DataResponse(
        data=ConversationOut.model_validate(conversation), meta=request_meta(request)
    )


@router.post("/conversations/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationAssignIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ConversationOut]:
    conversation = await _get_conversation_or_404(session, conversation_id)
    conversation = await service.assign_conversation(
        session,
        actor=actor,
        conversation=conversation,
        assignee_id=payload.assignee_id,
        reason=payload.reason,
        request=request,
    )
    return DataResponse(
        data=ConversationOut.model_validate(conversation), meta=request_meta(request)
    )


@router.post("/conversations/{conversation_id}/priority")
async def set_conversation_priority(
    conversation_id: uuid.UUID,
    payload: ConversationPriorityIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.priority.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ConversationOut]:
    conversation = await _get_conversation_or_404(session, conversation_id)
    conversation = await service.set_conversation_priority(
        session, actor=actor, conversation=conversation, priority=payload.priority
    )
    return DataResponse(
        data=ConversationOut.model_validate(conversation), meta=request_meta(request)
    )


@router.get("/conversations/{conversation_id}/timeline")
async def get_conversation_timeline(
    conversation_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ConversationTimelineEntryOut]]:
    await _get_conversation_or_404(session, conversation_id)
    entries = await service.get_conversation_timeline(session, conversation_id)
    return DataResponse(
        data=[ConversationTimelineEntryOut.model_validate(e) for e in entries],
        meta=request_meta(request),
    )


# --- Messages ------------------------------------------------------------


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
) -> PaginatedResponse[MessageOut]:
    await _get_conversation_or_404(session, conversation_id)
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    total = (
        await session.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        or 0
    )
    stmt = stmt.order_by(Message.created_at.desc())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[MessageOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
async def reply_to_conversation(
    conversation_id: uuid.UUID,
    payload: MessageCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.reply")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[MessageOut]:
    conversation = await _get_conversation_or_404(session, conversation_id)
    channel = await _get_channel_or_404(session, conversation.channel_id)
    template = None
    if payload.template_id is not None:
        template = await templates_service.get_template(session, payload.template_id)
        if template is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template not found.")
    recipient = payload.recipient_reference or conversation.phone_e164 or conversation.email
    message = await send_message(
        session,
        conversation=conversation,
        channel=channel,
        recipient_reference=recipient,
        body_text=payload.body_text,
        message_type=payload.message_type,
        template=template,
        template_variables=payload.template_variables,
        idempotency_key=payload.idempotency_key,
        actor=actor,
    )
    return DataResponse(data=MessageOut.model_validate(message), meta=request_meta(request))


@router.post("/conversations/{conversation_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_internal_note(
    conversation_id: uuid.UUID,
    payload: InternalNoteCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.notes.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[MessageOut]:
    conversation = await _get_conversation_or_404(session, conversation_id)
    note = await service.add_internal_note(
        session, actor=actor, conversation=conversation, payload=payload
    )
    return DataResponse(data=MessageOut.model_validate(note), meta=request_meta(request))


# --- Templates -------------------------------------------------------------


@router.get("/templates")
async def list_templates(
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.templates.view")),
    session: AsyncSession = Depends(get_db),
    channel_id: uuid.UUID | None = Query(default=None),
    category: str | None = Query(default=None),
) -> DataResponse[list[MessageTemplateOut]]:
    stmt = select(MessageTemplate)
    if channel_id:
        stmt = stmt.where(MessageTemplate.channel_id == channel_id)
    if category:
        stmt = stmt.where(MessageTemplate.category == category)
    rows = (await session.scalars(stmt.order_by(MessageTemplate.name))).all()
    return DataResponse(
        data=[MessageTemplateOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: MessageTemplateCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.templates.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[MessageTemplateOut]:
    template = await templates_service.create_template(session, actor=actor, payload=payload)
    return DataResponse(
        data=MessageTemplateOut.model_validate(template), meta=request_meta(request)
    )


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: uuid.UUID,
    payload: MessageTemplateUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.templates.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[MessageTemplateOut]:
    template = await templates_service.get_template(session, template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template not found.")
    template = await templates_service.update_template(
        session, actor=actor, template=template, payload=payload
    )
    return DataResponse(
        data=MessageTemplateOut.model_validate(template), meta=request_meta(request)
    )


@router.post("/templates/{template_id}/preview")
async def preview_template(
    template_id: uuid.UUID,
    payload: TemplatePreviewIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.templates.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TemplatePreviewOut]:
    template = await templates_service.get_template(session, template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template not found.")
    body, subject = templates_service.render_template(
        body=template.body,
        subject=template.subject,
        declared_variables=template.variables,
        values=payload.variables,
    )
    return DataResponse(
        data=TemplatePreviewOut(subject=subject, body=body), meta=request_meta(request)
    )


# --- Scheduled messages ------------------------------------------------------


@router.get("/scheduled")
async def list_scheduled_messages(
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    scheduled_status: str | None = Query(default=None),
) -> PaginatedResponse[ScheduledMessageOut]:
    stmt = select(ScheduledMessage)
    count_stmt = select(func.count()).select_from(ScheduledMessage)
    if scheduled_status:
        stmt = stmt.where(ScheduledMessage.status == scheduled_status)
        count_stmt = count_stmt.where(ScheduledMessage.status == scheduled_status)
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(ScheduledMessage.scheduled_for)
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[ScheduledMessageOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/scheduled", status_code=status.HTTP_201_CREATED)
async def create_scheduled_message(
    payload: ScheduledMessageCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.reply")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ScheduledMessageOut]:
    scheduled = ScheduledMessage(
        purpose=payload.purpose,
        template_id=payload.template_id,
        conversation_id=payload.conversation_id,
        customer_id=payload.customer_id,
        lead_id=payload.lead_id,
        channel_id=payload.channel_id,
        recipient_reference=payload.recipient_reference,
        scheduled_for=payload.scheduled_for,
        timezone=payload.timezone,
        template_variables=payload.template_variables,
        idempotency_key=payload.idempotency_key,
        created_by=actor.id,
    )
    session.add(scheduled)
    await session.flush()
    return DataResponse(
        data=ScheduledMessageOut.model_validate(scheduled), meta=request_meta(request)
    )


@router.post("/scheduled/{scheduled_id}/cancel")
async def cancel_scheduled_message(
    scheduled_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.reply")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ScheduledMessageOut]:
    scheduled = await session.get(ScheduledMessage, scheduled_id)
    if scheduled is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Scheduled message not found.")
    scheduled = await scheduling.cancel_scheduled_message(
        session, scheduled=scheduled, actor_id=actor.id
    )
    return DataResponse(
        data=ScheduledMessageOut.model_validate(scheduled), meta=request_meta(request)
    )


# --- Preferences / Consent / Suppression -------------------------------------


@router.get("/preferences/{customer_id}")
async def get_preferences(
    customer_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.preferences.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CommunicationPreferenceOut]:
    preference = await consent.get_or_create_preference(session, customer_id=customer_id)
    return DataResponse(
        data=CommunicationPreferenceOut.model_validate(preference), meta=request_meta(request)
    )


@router.patch("/preferences/{customer_id}")
async def update_preferences(
    customer_id: uuid.UUID,
    payload: CommunicationPreferenceUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.preferences.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CommunicationPreferenceOut]:
    preference = await consent.get_or_create_preference(session, customer_id=customer_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(preference, field, value)
    preference.updated_by = actor.id
    await session.flush()
    return DataResponse(
        data=CommunicationPreferenceOut.model_validate(preference), meta=request_meta(request)
    )


@router.post("/consents", status_code=status.HTTP_201_CREATED)
async def create_consent(
    payload: CommunicationConsentCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.preferences.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CommunicationConsentOut]:
    record = await consent.record_consent(
        session,
        customer_id=payload.customer_id,
        consent_type=payload.consent_type,
        consent_given=payload.consent_given,
        source=payload.source,
        consent_version=payload.consent_version,
        actor=actor,
    )
    return DataResponse(
        data=CommunicationConsentOut.model_validate(record), meta=request_meta(request)
    )


@router.get("/suppressions")
async def list_suppressions(
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.suppressions.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    active_only: bool = Query(default=True),
) -> PaginatedResponse[CommunicationSuppressionOut]:
    stmt = select(CommunicationSuppression)
    count_stmt = select(func.count()).select_from(CommunicationSuppression)
    if active_only:
        stmt = stmt.where(CommunicationSuppression.is_active.is_(True))
        count_stmt = count_stmt.where(CommunicationSuppression.is_active.is_(True))
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(CommunicationSuppression.created_at.desc())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[CommunicationSuppressionOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/suppressions", status_code=status.HTTP_201_CREATED)
async def create_suppression(
    payload: CommunicationSuppressionCreateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.suppressions.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CommunicationSuppressionOut]:
    record = await consent.suppress_destination(
        session,
        destination_type=payload.destination_type,
        destination_value=payload.destination_value,
        reason=payload.reason,
        scope=payload.scope,
        suppressed_until=payload.suppressed_until,
        customer_id=payload.customer_id,
        notes=payload.notes,
    )
    return DataResponse(
        data=CommunicationSuppressionOut.model_validate(record), meta=request_meta(request)
    )


@router.post("/suppressions/{suppression_id}/lift")
async def lift_suppression(
    suppression_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.suppressions.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CommunicationSuppressionOut]:
    suppression = await session.get(CommunicationSuppression, suppression_id)
    if suppression is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Suppression not found.")
    suppression = await consent.lift_suppression(session, suppression=suppression, actor=actor)
    return DataResponse(
        data=CommunicationSuppressionOut.model_validate(suppression), meta=request_meta(request)
    )


# --- Call logs ---------------------------------------------------------------


@router.get("/call-logs")
async def list_call_logs(
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.call_logs.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    customer_id: uuid.UUID | None = Query(default=None),
) -> PaginatedResponse[ManualCallLogOut]:
    stmt = select(ManualCallLog)
    count_stmt = select(func.count()).select_from(ManualCallLog)
    if customer_id:
        stmt = stmt.where(ManualCallLog.customer_id == customer_id)
        count_stmt = count_stmt.where(ManualCallLog.customer_id == customer_id)
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(ManualCallLog.started_at.desc())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[ManualCallLogOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/call-logs", status_code=status.HTTP_201_CREATED)
async def create_call_log(
    payload: ManualCallLogCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("communications.call_logs.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ManualCallLogOut]:
    call_log = await analytics.create_call_log(session, actor=actor, payload=payload)
    return DataResponse(data=ManualCallLogOut.model_validate(call_log), meta=request_meta(request))


# --- Analytics -----------------------------------------------------------


@router.get("/analytics")
async def get_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CommunicationAnalyticsOut]:
    stats = await analytics.get_communication_analytics(session)
    return DataResponse(data=stats, meta=request_meta(request))


@router.get("/customers/{customer_id}/stats")
async def get_customer_stats(
    customer_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("communications.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerCommunicationStatsOut]:
    stats = await aggregation.get_customer_communication_stats(session, customer_id)
    return DataResponse(data=stats, meta=request_meta(request))


# --- Webhooks (provider-signature auth, not staff auth) ----------------------


@router.post("/webhooks/{provider_name}/inbound", include_in_schema=False)
async def inbound_webhook(
    provider_name: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    channel = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.provider == provider_name)
    )
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown provider channel.")
    provider = get_provider(channel.provider)
    raw_body = await request.body()
    payload = await request.json()
    try:
        await webhooks.process_inbound_webhook(
            session,
            provider=provider,
            channel=channel,
            headers=dict(request.headers),
            raw_body=raw_body,
            payload=payload,
        )
    except webhooks.WebhookSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/webhooks/{provider_name}/status", include_in_schema=False)
async def status_webhook(
    provider_name: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    channel = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.provider == provider_name)
    )
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown provider channel.")
    provider = get_provider(channel.provider)
    raw_body = await request.body()
    payload = await request.json()
    try:
        await webhooks.process_status_webhook(
            session,
            provider=provider,
            channel=channel,
            headers=dict(request.headers),
            raw_body=raw_body,
            payload=payload,
        )
    except webhooks.WebhookSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return {"status": "ok"}
