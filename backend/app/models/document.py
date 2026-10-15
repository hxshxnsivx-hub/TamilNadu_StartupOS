"""Document ORM model (design.md Req 6.1 · Document entity)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # A document belongs to a founder and/or a startup (at least one set).
    founder_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("founders.founder_id", ondelete="CASCADE"),
        nullable=True,
    )
    startup_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("startups.startup_id", ondelete="CASCADE"),
        nullable=True,
    )

    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted S3 key
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    verification_status: Mapped[str] = mapped_column(
        String(50), default="pending", server_default="pending"
    )
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verifier_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "founder_id IS NOT NULL OR startup_id IS NOT NULL",
            name="owner_present",
        ),
        Index("ix_documents_founder", "founder_id"),
        Index("ix_documents_startup", "startup_id"),
        Index("ix_documents_type", "document_type"),
    )
