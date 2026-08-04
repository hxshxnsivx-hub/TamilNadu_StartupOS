"""ProfileCompleteness ORM model (design.md Req 6.1 · Profile_Completeness)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProfileCompleteness(Base):
    __tablename__ = "profile_completeness"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    founder_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("founders.founder_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    missing_fields: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    verified_fields: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "completeness_score IN (0, 40, 60, 80, 100)", name="valid_completeness_score"
        ),
        Index("ix_profile_completeness_founder", "founder_id"),
    )
