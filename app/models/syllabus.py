from __future__ import annotations

import uuid
from sqlalchemy import Integer, String, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Syllabus(Base):
    """
    Official chapter ordering for each exam and subject.

    Populated at migration time with NCERT/NTA data.
    Used by SyllabusResolver to deterministically expand chapter range filters.
    The LLM never reads this table — only the backend resolver does.
    """
    __tablename__ = "syllabus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Partition key — every query filters on (exam_name, subject)
    exam_name: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)

    # Canonical NCERT chapter name (the source of truth)
    chapter_name: Mapped[str] = mapped_column(String(256), nullable=False)

    # 1-indexed, no gaps — drives all range queries
    chapter_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Common alternate names the LLM or teacher might use.
    # Alias match is checked before fuzzy matching.
    # Example: ["Rotational Motion", "Rigid Body", "System of Particles"]
    chapter_aliases: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    __table_args__ = (
        UniqueConstraint("exam_name", "subject", "chapter_order",
                         name="uq_syllabus_order"),
        UniqueConstraint("exam_name", "subject", "chapter_name",
                         name="uq_syllabus_name"),
        Index("idx_syllabus_exam_subject", "exam_name", "subject"),
    )

    def __repr__(self) -> str:
        return (
            f"<Syllabus {self.exam_name}/{self.subject} "
            f"#{self.chapter_order} {self.chapter_name!r}>"
        )
