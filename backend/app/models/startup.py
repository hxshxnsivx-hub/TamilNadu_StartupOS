"""Startup ORM model (design.md Data Models · Startup Profile)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, uuid_pk


class Startup(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "startups"

    startup_id: Mapped[uuid.UUID] = uuid_pk()
    founder_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("founders.founder_id", ondelete="CASCADE"),
        nullable=False,
    )

    startup_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cin_number: Mapped[str | None] = mapped_column(String(21), unique=True, nullable=True)
    dpiit_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(15), unique=True, nullable=True)

    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    incorporation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employee_count: Mapped[int] = mapped_column(default=0, server_default="0")
    monthly_revenue: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("0"), server_default="0"
    )

    verification_status: Mapped[str] = mapped_column(
        String(50), default="pending", server_default="pending"
    )
    legal_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # v2: terrain roadmap mode (design B1 · P-29)
    terrain: Mapped[str | None] = mapped_column(String(30), nullable=True)

    __table_args__ = (
        CheckConstraint(
            r"cin_number IS NULL OR cin_number ~* "
            r"'^[LUF][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$'",
            name="valid_cin",
        ),
        CheckConstraint("gstin IS NULL OR LENGTH(gstin) = 15", name="valid_gstin"),
        CheckConstraint("employee_count >= 0", name="positive_employees"),
        CheckConstraint("monthly_revenue >= 0", name="positive_revenue"),
        Index("ix_startups_founder", "founder_id"),
        Index("ix_startups_domain", "domain"),
        Index("ix_startups_stage", "stage"),
        Index("ix_startups_verification", "verification_status"),
    )
