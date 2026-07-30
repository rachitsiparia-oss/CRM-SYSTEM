import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ArticleType = Literal[
    "sop",
    "policy",
    "procedure",
    "checklist",
    "guide",
    "troubleshooting",
    "training_material",
    "emergency_instruction",
    "announcement",
]
ArticleStatus = Literal[
    "draft", "in_review", "changes_requested", "approved", "published", "superseded", "archived"
]
VisibilityScope = Literal[
    "all_staff",
    "department",
    "role",
    "specific_staff",
    "management_only",
    "hr_only",
    "kitchen_only",
    "front_of_house_only",
]
RelatedType = Literal[
    "knowledge_article",
    "menu_item",
    "inventory_item",
    "reservation_policy",
    "order_workflow",
    "training_course",
    "operational_task",
]
AssigneeType = Literal["staff", "department", "role"]


class CategoryCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=48)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    version: int


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    code: str
    description: str | None
    sort_order: int
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ArticleCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=220)
    summary: str | None = None
    content: str = Field(min_length=1)
    article_type: ArticleType
    category_id: uuid.UUID | None = None
    owner_staff_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    visibility_scope: VisibilityScope = "all_staff"
    effective_at: datetime | None = None
    review_at: datetime | None = None
    expiry_at: datetime | None = None
    estimated_reading_minutes: int | None = Field(default=None, ge=0)
    requires_acknowledgement: bool = False
    requires_training: bool = False


class ArticleUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str | None = None
    content: str | None = Field(default=None, min_length=1)
    category_id: uuid.UUID | None = None
    owner_staff_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    visibility_scope: VisibilityScope | None = None
    effective_at: datetime | None = None
    review_at: datetime | None = None
    expiry_at: datetime | None = None
    estimated_reading_minutes: int | None = Field(default=None, ge=0)
    requires_acknowledgement: bool | None = None
    requires_training: bool | None = None
    version: int


class ArticleTransitionIn(BaseModel):
    target_status: ArticleStatus
    comment: str | None = None


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_number: str
    title: str
    summary: str | None
    content: str
    article_type: str
    category_id: uuid.UUID | None
    owner_staff_id: uuid.UUID | None
    department_id: uuid.UUID | None
    visibility_scope: str
    status: str
    latest_version_number: int
    published_version_id: uuid.UUID | None
    effective_at: datetime | None
    review_at: datetime | None
    expiry_at: datetime | None
    estimated_reading_minutes: int | None
    requires_acknowledgement: bool
    requires_training: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ArticleVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    version_number: int
    title_snapshot: str
    summary_snapshot: str | None
    content_snapshot: str
    change_summary: str | None
    author_id: uuid.UUID | None
    reviewer_id: uuid.UUID | None
    submitted_at: datetime
    approved_at: datetime | None
    published_at: datetime | None
    effective_at: datetime | None
    superseded_at: datetime | None
    created_at: datetime


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    version_id: uuid.UUID
    action: str
    actor_id: uuid.UUID
    comment: str | None
    created_at: datetime


class TagAssignIn(BaseModel):
    tag_ids: list[uuid.UUID] = Field(min_length=1)


class RelationCreateIn(BaseModel):
    related_type: RelatedType
    related_id: uuid.UUID
    relation_note: str | None = Field(default=None, max_length=200)


class RelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    related_type: str
    related_id: uuid.UUID
    relation_note: str | None
    created_at: datetime


class VisibilityRuleCreateIn(BaseModel):
    rule_type: Literal["department", "role", "staff"]
    department_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    staff_id: uuid.UUID | None = None


class VisibilityRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    rule_type: str
    department_id: uuid.UUID | None
    role_id: uuid.UUID | None
    staff_id: uuid.UUID | None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    version_id: uuid.UUID | None
    file_name: str
    mime_type: str
    size_bytes: int
    upload_status: str
    scan_status: str
    created_at: datetime


class AssignmentCreateIn(BaseModel):
    version_id: uuid.UUID | None = None
    assignee_type: AssigneeType
    staff_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    due_at: datetime | None = None
    is_mandatory: bool = True
    reason: str | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    version_id: uuid.UUID | None
    assignee_type: str
    staff_id: uuid.UUID | None
    department_id: uuid.UUID | None
    role_id: uuid.UUID | None
    due_at: datetime | None
    is_mandatory: bool
    reason: str | None
    assigned_by: uuid.UUID | None
    status: str
    created_at: datetime


class AcknowledgementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    article_id: uuid.UUID
    version_id: uuid.UUID
    staff_id: uuid.UUID
    first_opened_at: datetime | None
    last_opened_at: datetime | None
    open_count: int
    acknowledged_at: datetime | None
    due_at: datetime | None
    revoked_at: datetime | None


class KnowledgeAnalyticsOut(BaseModel):
    published_articles: int
    drafts_awaiting_review: int
    articles_due_for_review: int
    expired_articles: int
    mandatory_acknowledgements_completed: int
    mandatory_acknowledgements_overdue: int
    most_viewed_articles: list[dict[str, object]]
