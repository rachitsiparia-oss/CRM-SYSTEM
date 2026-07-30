import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

RULE_TYPES = ("department", "role", "staff")


class KnowledgeVisibilityRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Additional visibility grants for an article whose
    `visibility_scope` is `department`/`role`/`specific_staff` — this
    phase's own instruction section 5. Only one of `department_id`/
    `role_id`/`staff_id` is set, matching `rule_type`; the other five
    `visibility_scope` values (`all_staff`/`management_only`/`hr_only`/
    `kitchen_only`/`front_of_house_only`) are pure predicates over the
    requester's own department/role/permissions in `app.knowledge.visibility`
    and need no rows here."""

    __tablename__ = "knowledge_visibility_rules"
    __table_args__ = (
        CheckConstraint(f"rule_type IN {RULE_TYPES!r}", name="valid_rule_type"),
        CheckConstraint(
            "(rule_type = 'department' AND department_id IS NOT NULL "
            "AND role_id IS NULL AND staff_id IS NULL) OR "
            "(rule_type = 'role' AND role_id IS NOT NULL "
            "AND department_id IS NULL AND staff_id IS NULL) OR "
            "(rule_type = 'staff' AND staff_id IS NOT NULL "
            "AND department_id IS NULL AND role_id IS NULL)",
            name="valid_rule_target",
        ),
        Index("ix_knowledge_visibility_rules_article_id", "article_id"),
        Index(
            "uq_knowledge_visibility_rules_department",
            "article_id",
            "department_id",
            unique=True,
            postgresql_where=text("rule_type = 'department'"),
        ),
        Index(
            "uq_knowledge_visibility_rules_role",
            "article_id",
            "role_id",
            unique=True,
            postgresql_where=text("rule_type = 'role'"),
        ),
        Index(
            "uq_knowledge_visibility_rules_staff",
            "article_id",
            "staff_id",
            unique=True,
            postgresql_where=text("rule_type = 'staff'"),
        ),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(16), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
