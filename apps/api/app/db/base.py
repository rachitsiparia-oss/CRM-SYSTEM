import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Explicit naming convention so every constraint gets a stable, predictable
# name — required for Alembic autogenerate to produce clean, reviewable
# migrations instead of arbitrary database-assigned names. See
# ARCHITECTURE_AND_TECH_STACK.md section 8.5 (constraint strategy).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Without this, a server-computed column (created_at/updated_at's
    # onupdate=func.now()) is marked expired after a flush instead of
    # populated via Postgres RETURNING, so reading it later needs a lazy
    # SQL refresh — a real bug this phase's tests caught: serializing
    # updated_at right after an in-request UPDATE raised MissingGreenlet,
    # since that refresh can't be awaited from inside Pydantic's synchronous
    # model_validate. Phase 3's staff schemas never exposed updated_at, so
    # this was already latent but never triggered until now.
    __mapper_args__ = {"eager_defaults": True}


class UUIDPrimaryKeyMixin:
    """UUID primary keys generated application-side — DATABASE_AND_API.md
    section 8.2. Generating in Python (rather than relying on a Postgres
    extension such as pgcrypto) keeps identifier generation portable and
    testable without database-specific setup."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """created_at/updated_at in UTC — DATABASE_AND_API.md section 3.1 and
    3.4. Business-local display conversion (Asia/Kolkata) happens at the
    presentation layer, never in storage."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AppendOnlyTimestampMixin:
    """created_at only, for append-oriented ledgers and history tables that
    are never updated in place — DATABASE_AND_API.md section 3.1 ("Append-
    only ledgers and history tables do not require updated_at")."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditedMixin:
    """created_by/updated_by/version — DATABASE_AND_API.md section 3.1.

    Nullable because the very first row in the system (the bootstrapped
    owner) has no prior staff_user to attribute the action to.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)


class SoftDeleteMixin:
    """deleted_at/deleted_by/deletion_reason — DATABASE_AND_API.md section
    3.1, for soft-deletable entities."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    deletion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
