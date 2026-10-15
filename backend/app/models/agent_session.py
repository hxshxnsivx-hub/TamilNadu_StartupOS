"""Saved ideation conversations (IDEATION-PIPELINE-DESIGN.md §3.4).

One row per conversation, holding the whole session as a JSON document plus
the columns the platform needs to look sessions up and to guard writes. The
document is split into normalised tables when cohort analysis needs to query
inside it (Phase 5).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AgentSessionRow(Base, TimestampMixin):
    __tablename__ = "agent_sessions"

    session_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # Bumped on every save; a save carrying an older version is refused.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idea_version: Mapped[str | None] = mapped_column(String(12), nullable=True)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    data: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
