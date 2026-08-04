"""initial schema — founders, startups, documents, profile_completeness

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-19

Baseline migration. Creates the extensions the platform needs, then builds the
Phase-1 tables straight from the ORM metadata so the migration can never drift
from the models. Subsequent migrations use explicit op.* operations (and support
`alembic upgrade --sql`).
"""

from collections.abc import Sequence

from alembic import op
from app.models import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Phase-1 tables built by this baseline.
_TABLES = ["founders", "startups", "documents", "profile_completeness"]


def upgrade() -> None:
    bind = op.get_bind()
    # gen_random_uuid() is core in PG13+, but ensure pgcrypto for older servers.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    tables = [Base.metadata.tables[name] for name in _TABLES]
    Base.metadata.create_all(bind=bind, tables=tables, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    tables = [Base.metadata.tables[name] for name in reversed(_TABLES)]
    Base.metadata.drop_all(bind=bind, tables=tables, checkfirst=True)
