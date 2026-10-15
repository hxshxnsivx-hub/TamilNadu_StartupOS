"""agent_sessions: saved ideation conversations

Revision ID: 0004_agent_sessions
Revises: 0003_embeddings
Create Date: 2026-10-08

One row per conversation; the session itself is a JSON document
(SYSTEM-DESIGN.md §5.1). `version` guards against lost updates.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004_agent_sessions"
down_revision: str | None = "0003_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("session_id", sa.String(32), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("idea_version", sa.String(12), nullable=True),
        sa.Column("private", sa.Boolean(), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("session_id", name="pk_agent_sessions"),
    )
    op.create_index("ix_agent_sessions_user_id", "agent_sessions", ["user_id"])
    op.create_index("ix_agent_sessions_last_active", "agent_sessions", ["last_active"])


def downgrade() -> None:
    op.drop_index("ix_agent_sessions_last_active", table_name="agent_sessions")
    op.drop_index("ix_agent_sessions_user_id", table_name="agent_sessions")
    op.drop_table("agent_sessions")
