"""enable_row_level_security_on_all_tables

Revision ID: 68a3f066b2b9
Revises: c9582fab677e
Create Date: 2026-07-25 20:22:48.691934

Enables RLS with zero policies on every table created so far. Supabase's
`anon` key is public (shipped in the browser bundle) and, without RLS,
every table is reachable through Supabase's auto-generated REST API
(PostgREST) using that key -- completely bypassing FastAPI's own
authorization layer, regardless of whether the frontend is intended to use
that path. RLS-enabled-with-no-policies denies all access through
PostgREST by default.

This does not affect `apps/api`: it connects as the table-owning
`postgres.<project-ref>` role over a direct Postgres connection, not
through PostgREST, and table owners bypass RLS unless `FORCE ROW LEVEL
SECURITY` is also set (it is not, here) --
ARCHITECTURE_AND_TECH_STACK.md section 10.4 ("PostgreSQL application-level
authorization is primary... Supabase RLS may still be used for direct
browser-accessed services").
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "68a3f066b2b9"
down_revision: str | Sequence[str] | None = "c9582fab677e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "audit_events",
    "outbox_events",
    "job_records",
    "departments",
    "roles",
    "permissions",
    "role_permissions",
    "staff_roles",
    "staff_users",
    "staff_invitations",
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
