"""embeddings vector store (pgvector + HNSW)

Revision ID: 0003_embeddings
Revises: 0002_users
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "0003_embeddings"
down_revision: str | None = "0002_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "embeddings",
        sa.Column(
            "id", PGUUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("namespace", sa.String(40), nullable=False),
        sa.Column("ref_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("embedding", Vector(_DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_embeddings"),
    )
    op.create_index("ix_embeddings_ns_ref", "embeddings", ["namespace", "ref_id"])
    # Approximate-nearest-neighbour index for cosine distance.
    op.execute(
        "CREATE INDEX ix_embeddings_hnsw ON embeddings "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_hnsw")
    op.drop_index("ix_embeddings_ns_ref", table_name="embeddings")
    op.drop_table("embeddings")
