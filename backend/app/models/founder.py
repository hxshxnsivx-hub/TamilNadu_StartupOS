"""Founder ORM model (design.md Data Models · Founder Profile)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, uuid_pk

# NOTE: fields marked "encrypted-at-rest" (phone, date_of_birth, caste_category) are
# stored as plain columns now; the AES-256 EncryptedString TypeDecorator wraps them
# in Task 5.4 / design ADDENDUM v2 · B14. Kept as columns so the wrap is transparent.


class Founder(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "founders"

    founder_id: Mapped[uuid.UUID] = uuid_pk()

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)

    # Location
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Education
    highest_qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(nullable=True)
    first_graduate: Mapped[bool] = mapped_column(default=False, server_default="false")
    caste_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # v2: peer discovery opt-in (design B2 · P-41)
    discoverable: Mapped[bool] = mapped_column(default=False, server_default="false")

    __table_args__ = (
        CheckConstraint(
            r"email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="valid_email",
        ),
        CheckConstraint(r"phone ~* '^\+?[1-9]\d{1,14}$'", name="valid_phone"),
        Index("ix_founders_email", "email"),
        Index("ix_founders_phone", "phone"),
        Index("ix_founders_location", "state", "district"),
    )
