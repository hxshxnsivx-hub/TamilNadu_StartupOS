"""User (authentication identity) ORM model.

Separated from ``Founder`` so sign-up needs only email + password; the rich
founder profile is created later and linked via ``founder_id``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    founder_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("founders.founder_id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            r"email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="valid_email",
        ),
        Index("ix_users_email", "email"),
    )
