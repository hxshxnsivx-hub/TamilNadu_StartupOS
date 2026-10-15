"""Pydantic domain models and SQLAlchemy ORM models.

Importing this package registers all ORM tables on ``Base.metadata`` so Alembic
autogenerate and ``metadata.create_all`` see the full schema.
"""

from app.db.base import Base
from app.models.agent_session import AgentSessionRow
from app.models.document import Document
from app.models.embeddings import Embedding
from app.models.founder import Founder
from app.models.profile import ProfileCompleteness
from app.models.startup import Startup
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Founder",
    "Startup",
    "Document",
    "ProfileCompleteness",
    "Embedding",
    "AgentSessionRow",
]
