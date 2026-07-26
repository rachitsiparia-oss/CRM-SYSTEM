import uuid
from typing import Any

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class CustomerMergeEvent(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """DATABASE_AND_API.md section 6.7. Immutable audit trail of every
    merge; `Customer.merged_into_customer_id` is the fast current-state
    pointer this table's history explains."""

    __tablename__ = "customer_merge_events"

    source_customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    surviving_customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    mapping_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
