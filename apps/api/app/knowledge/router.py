import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import (
    KnowledgeAcknowledgement,
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeAssignment,
    KnowledgeAttachment,
    KnowledgeCategory,
    StaffUser,
)
from app.db.session import get_db
from app.knowledge import articles, assignments, attachments, categories, search, tags, visibility
from app.knowledge.analytics import get_knowledge_analytics
from app.knowledge.schemas import (
    AcknowledgementOut,
    ArticleCreateIn,
    ArticleOut,
    ArticleTransitionIn,
    ArticleUpdateIn,
    ArticleVersionOut,
    AssignmentCreateIn,
    AssignmentOut,
    AttachmentOut,
    CategoryCreateIn,
    CategoryOut,
    CategoryUpdateIn,
    KnowledgeAnalyticsOut,
    RelationCreateIn,
    RelationOut,
    ReviewOut,
    TagAssignIn,
    VisibilityRuleCreateIn,
    VisibilityRuleOut,
)
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


async def _get_article_or_404(session: AsyncSession, article_id: uuid.UUID) -> KnowledgeArticle:
    article = await articles.get_article(session, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found.")
    return article


async def _require_visible(
    session: AsyncSession, *, article: KnowledgeArticle, viewer: StaffUser
) -> None:
    if not await visibility.is_article_visible_to(session, article=article, viewer=viewer):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You do not have visibility into this article."
        )


# --- Categories -----------------------------------------------------------


@router.get("/categories")
async def list_categories(
    request: Request,
    _viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[CategoryOut]]:
    rows = await categories.list_categories(session)
    return DataResponse(
        data=[CategoryOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CategoryOut]:
    category = await categories.create_category(session, actor=actor, payload=payload)
    return DataResponse(data=CategoryOut.model_validate(category), meta=request_meta(request))


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CategoryOut]:
    category = await session.get(KnowledgeCategory, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found.")
    category = await categories.update_category(
        session, actor=actor, category=category, payload=payload
    )
    return DataResponse(data=CategoryOut.model_validate(category), meta=request_meta(request))


# --- Search -----------------------------------------------------------


@router.get("/search")
async def search_knowledge(
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    q: str | None = Query(default=None, max_length=200),
    category_id: uuid.UUID | None = Query(default=None),
    article_type: str | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None),
    published_only: bool = Query(default=True),
) -> PaginatedResponse[ArticleOut]:
    rows, total = await search.search_articles(
        session,
        viewer=viewer,
        query=q,
        category_id=category_id,
        article_type=article_type,
        department_id=department_id,
        status_filter=None,
        owner_staff_id=None,
        published_only=published_only,
        page=page_params.page,
        page_size=page_params.page_size,
    )
    return PaginatedResponse(
        data=[ArticleOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


# --- Analytics -----------------------------------------------------------


@router.get("/analytics")
async def knowledge_analytics(
    request: Request,
    _viewer: StaffUser = Depends(require_permission("knowledge.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[KnowledgeAnalyticsOut]:
    data = await get_knowledge_analytics(session)
    return DataResponse(data=KnowledgeAnalyticsOut.model_validate(data), meta=request_meta(request))


# --- Articles -----------------------------------------------------------


@router.get("/articles")
async def list_articles(
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    status_filter: str | None = Query(default=None, alias="status"),
    category_id: uuid.UUID | None = Query(default=None),
    article_type: str | None = Query(default=None),
    owner_staff_id: uuid.UUID | None = Query(default=None),
) -> PaginatedResponse[ArticleOut]:
    rows, total = await search.search_articles(
        session,
        viewer=viewer,
        query=None,
        category_id=category_id,
        article_type=article_type,
        department_id=None,
        status_filter=status_filter,
        owner_staff_id=owner_staff_id,
        published_only=False,
        page=page_params.page,
        page_size=page_params.page_size,
    )
    return PaginatedResponse(
        data=[ArticleOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/articles", status_code=status.HTTP_201_CREATED)
async def create_article(
    payload: ArticleCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ArticleOut]:
    article = await articles.create_article(session, actor=actor, payload=payload)
    return DataResponse(data=ArticleOut.model_validate(article), meta=request_meta(request))


@router.get("/articles/{article_id}")
async def get_article(
    article_id: uuid.UUID,
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ArticleOut]:
    article = await _get_article_or_404(session, article_id)
    await _require_visible(session, article=article, viewer=viewer)
    await assignments.record_view(session, article=article, viewer=viewer)
    return DataResponse(data=ArticleOut.model_validate(article), meta=request_meta(request))


@router.patch("/articles/{article_id}")
async def update_article(
    article_id: uuid.UUID,
    payload: ArticleUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ArticleOut]:
    article = await _get_article_or_404(session, article_id)
    article = await articles.update_article(session, actor=actor, article=article, payload=payload)
    return DataResponse(data=ArticleOut.model_validate(article), meta=request_meta(request))


@router.post("/articles/{article_id}/submit")
async def submit_article(
    article_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ArticleOut]:
    article = await _get_article_or_404(session, article_id)
    article = await articles.submit_for_review(session, actor=actor, article=article)
    return DataResponse(data=ArticleOut.model_validate(article), meta=request_meta(request))


@router.post("/articles/{article_id}/review")
async def review_article(
    article_id: uuid.UUID,
    payload: ArticleTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.approve")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ArticleOut]:
    article = await _get_article_or_404(session, article_id)
    article = await articles.make_review_decision(
        session,
        actor=actor,
        article=article,
        decision=payload.target_status,
        comment=payload.comment,
    )
    return DataResponse(data=ArticleOut.model_validate(article), meta=request_meta(request))


@router.post("/articles/{article_id}/publish")
async def publish_article(
    article_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.publish")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ArticleOut]:
    article = await _get_article_or_404(session, article_id)
    article = await articles.publish_article(session, actor=actor, article=article)
    return DataResponse(data=ArticleOut.model_validate(article), meta=request_meta(request))


@router.post("/articles/{article_id}/transition")
async def transition_article(
    article_id: uuid.UUID,
    payload: ArticleTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.publish")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ArticleOut]:
    article = await _get_article_or_404(session, article_id)
    article = await articles.transition_simple(
        session,
        actor=actor,
        article=article,
        target_status=payload.target_status,
        comment=payload.comment,
    )
    return DataResponse(data=ArticleOut.model_validate(article), meta=request_meta(request))


@router.get("/articles/{article_id}/versions")
async def list_versions(
    article_id: uuid.UUID,
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ArticleVersionOut]]:
    article = await _get_article_or_404(session, article_id)
    await _require_visible(session, article=article, viewer=viewer)
    rows = (
        await session.scalars(
            select(KnowledgeArticleVersion)
            .where(KnowledgeArticleVersion.article_id == article_id)
            .order_by(KnowledgeArticleVersion.version_number.desc())
        )
    ).all()
    return DataResponse(
        data=[ArticleVersionOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.get("/articles/{article_id}/timeline")
async def get_article_timeline(
    article_id: uuid.UUID,
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ReviewOut]]:
    article = await _get_article_or_404(session, article_id)
    await _require_visible(session, article=article, viewer=viewer)
    rows = await articles.get_article_timeline(session, article_id)
    return DataResponse(
        data=[ReviewOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Tags and relations ---------------------------------------------------


@router.post("/articles/{article_id}/tags")
async def assign_tags(
    article_id: uuid.UUID,
    payload: TagAssignIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.tags.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    article = await _get_article_or_404(session, article_id)
    await tags.assign_tags(session, actor=actor, article=article, tag_ids=payload.tag_ids)
    return DataResponse(data={"status": "ok"}, meta=request_meta(request))


@router.delete("/articles/{article_id}/tags/{tag_id}")
async def remove_tag(
    article_id: uuid.UUID,
    tag_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("knowledge.tags.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    await tags.remove_tag(session, article_id=article_id, tag_id=tag_id)
    return DataResponse(data={"status": "ok"}, meta=request_meta(request))


@router.post("/articles/{article_id}/relations", status_code=status.HTTP_201_CREATED)
async def create_relation(
    article_id: uuid.UUID,
    payload: RelationCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RelationOut]:
    article = await _get_article_or_404(session, article_id)
    relation = await tags.create_relation(session, actor=actor, article=article, payload=payload)
    return DataResponse(data=RelationOut.model_validate(relation), meta=request_meta(request))


@router.get("/articles/{article_id}/relations")
async def list_relations(
    article_id: uuid.UUID,
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[RelationOut]]:
    rows = await tags.list_relations(session, article_id)
    return DataResponse(
        data=[RelationOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.delete("/articles/{article_id}/relations/{relation_id}")
async def remove_relation(
    article_id: uuid.UUID,
    relation_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("knowledge.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    await tags.remove_relation(session, article_id=article_id, relation_id=relation_id)
    return DataResponse(data={"status": "ok"}, meta=request_meta(request))


# --- Visibility rules ------------------------------------------------------


@router.get("/articles/{article_id}/visibility-rules")
async def list_visibility_rules(
    article_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("knowledge.visibility.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[VisibilityRuleOut]]:
    rows = await visibility.list_visibility_rules(session, article_id)
    return DataResponse(
        data=[VisibilityRuleOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/articles/{article_id}/visibility-rules", status_code=status.HTTP_201_CREATED)
async def add_visibility_rule(
    article_id: uuid.UUID,
    payload: VisibilityRuleCreateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("knowledge.visibility.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[VisibilityRuleOut]:
    article = await _get_article_or_404(session, article_id)
    rule = await visibility.add_visibility_rule(session, article=article, payload=payload)
    return DataResponse(data=VisibilityRuleOut.model_validate(rule), meta=request_meta(request))


@router.delete("/articles/{article_id}/visibility-rules/{rule_id}")
async def remove_visibility_rule(
    article_id: uuid.UUID,
    rule_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("knowledge.visibility.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    await visibility.remove_visibility_rule(session, article_id=article_id, rule_id=rule_id)
    return DataResponse(data={"status": "ok"}, meta=request_meta(request))


# --- Attachments ------------------------------------------------------


@router.get("/articles/{article_id}/attachments")
async def list_attachments(
    article_id: uuid.UUID,
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[AttachmentOut]]:
    article = await _get_article_or_404(session, article_id)
    await _require_visible(session, article=article, viewer=viewer)
    rows = await attachments.list_attachments(session, article_id)
    return DataResponse(
        data=[AttachmentOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/articles/{article_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    article_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.update")),
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    version_id: uuid.UUID | None = Form(default=None),
) -> DataResponse[AttachmentOut]:
    article = await _get_article_or_404(session, article_id)
    data = await file.read()
    attachment = await attachments.upload_attachment(
        session,
        actor=actor,
        article_id=article.id,
        version_id=version_id,
        data=data,
        filename=file.filename or "upload",
        declared_content_type=file.content_type or "application/octet-stream",
    )
    return DataResponse(data=AttachmentOut.model_validate(attachment), meta=request_meta(request))


@router.get("/articles/{article_id}/attachments/{attachment_id}/signed-url")
async def get_attachment_signed_url(
    article_id: uuid.UUID,
    attachment_id: uuid.UUID,
    request: Request,
    viewer: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    article = await _get_article_or_404(session, article_id)
    await _require_visible(session, article=article, viewer=viewer)
    attachment = await session.get(KnowledgeAttachment, attachment_id)
    if (
        attachment is None
        or attachment.article_id != article_id
        or attachment.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
    url = await attachments.get_attachment_signed_url(attachment)
    return DataResponse(data={"signed_url": url}, meta=request_meta(request))


@router.delete("/articles/{article_id}/attachments/{attachment_id}")
async def delete_attachment(
    article_id: uuid.UUID,
    attachment_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, str]]:
    attachment = await session.get(KnowledgeAttachment, attachment_id)
    if attachment is None or attachment.article_id != article_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
    await attachments.delete_attachment(session, actor=actor, attachment=attachment)
    return DataResponse(data={"status": "ok"}, meta=request_meta(request))


# --- Assignments and acknowledgements ---------------------------------------


@router.post("/articles/{article_id}/assignments", status_code=status.HTTP_201_CREATED)
async def create_assignment(
    article_id: uuid.UUID,
    payload: AssignmentCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AssignmentOut]:
    article = await _get_article_or_404(session, article_id)
    assignment = await assignments.create_assignment(
        session, actor=actor, article=article, payload=payload
    )
    return DataResponse(data=AssignmentOut.model_validate(assignment), meta=request_meta(request))


@router.get("/articles/{article_id}/assignments")
async def list_assignments(
    article_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("knowledge.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[AssignmentOut]]:
    rows = await assignments.list_assignments(session, article_id)
    return DataResponse(
        data=[AssignmentOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/articles/{article_id}/assignments/{assignment_id}/cancel")
async def cancel_assignment(
    article_id: uuid.UUID,
    assignment_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("knowledge.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AssignmentOut]:
    assignment = await session.get(KnowledgeAssignment, assignment_id)
    if assignment is None or assignment.article_id != article_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    assignment = await assignments.cancel_assignment(session, assignment=assignment)
    return DataResponse(data=AssignmentOut.model_validate(assignment), meta=request_meta(request))


@router.post("/articles/{article_id}/acknowledge")
async def acknowledge_article(
    article_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.acknowledge")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AcknowledgementOut]:
    article = await _get_article_or_404(session, article_id)
    await _require_visible(session, article=article, viewer=actor)
    ack = await assignments.acknowledge_article(session, article=article, staff=actor)
    return DataResponse(data=AcknowledgementOut.model_validate(ack), meta=request_meta(request))


@router.get("/acknowledgements/mine")
async def list_my_acknowledgements(
    request: Request,
    actor: StaffUser = Depends(require_permission("knowledge.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[AcknowledgementOut]]:
    rows = (
        await session.scalars(
            select(KnowledgeAcknowledgement).where(KnowledgeAcknowledgement.staff_id == actor.id)
        )
    ).all()
    return DataResponse(
        data=[AcknowledgementOut.model_validate(r) for r in rows], meta=request_meta(request)
    )
