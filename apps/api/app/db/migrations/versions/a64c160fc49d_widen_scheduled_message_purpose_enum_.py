"""widen scheduled_message purpose enum for campaigns

Revision ID: a64c160fc49d
Revises: c8f5d1d4e495
Create Date: 2026-07-31 09:51:23.822431

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a64c160fc49d"
down_revision: str | Sequence[str] | None = "c8f5d1d4e495"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_PURPOSES = ("reservation_reminder", "feedback_request", "lead_follow_up", "manual")
_NEW_PURPOSES = (*_OLD_PURPOSES, "campaign")


def upgrade() -> None:
    op.drop_constraint("valid_purpose", "scheduled_messages", type_="check")
    op.create_check_constraint(
        "valid_purpose", "scheduled_messages", f"purpose IN {_NEW_PURPOSES!r}"
    )


def downgrade() -> None:
    op.drop_constraint("valid_purpose", "scheduled_messages", type_="check")
    op.create_check_constraint(
        "valid_purpose", "scheduled_messages", f"purpose IN {_OLD_PURPOSES!r}"
    )
