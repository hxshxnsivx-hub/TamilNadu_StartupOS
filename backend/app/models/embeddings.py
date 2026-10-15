"""Vector store ORM (namespaced embeddings) — Task 1.6.5.

One generic ``embeddings`` table serves every consumer (scheme text, startup
domain, opportunity, investor thesis) via a ``namespace`` discriminator, so we
don't couple to tables that only exist in later phases. Cosine-distance HNSW
index is created in migration 0003.
"""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk

# Fixed at the model level because the pgvector column dimension is physical.
# Matches settings.embedding_dim (BGE-M3 / Cohere-multilingual = 1024).
EMBEDDING_DIM = 1024


class Embedding(Base, TimestampMixin):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = uuid_pk()
    namespace: Mapped[str] = mapped_column(String(40), nullable=False)  # scheme|startup_domain|...
    ref_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    __table_args__ = (Index("ix_embeddings_ns_ref", "namespace", "ref_id"),)
