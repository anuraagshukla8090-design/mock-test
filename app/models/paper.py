from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import Boolean, String, Text, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Paper(Base):
    """
    A generated exam paper.

    Always starts as 'draft'. Teacher must explicitly approve.
    Questions are stored in the paper_questions join table (ordered, lockable).
    """
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # What the teacher typed
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured blueprint parsed from the prompt by the LLM.
    # Includes the random seed so the same paper can be regenerated exactly.
    # Schema mirrors PaperBlueprint dataclass in paper_generator.py
    blueprint: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # "draft" | "approved"
    # There is no auto-approve. The teacher must always call POST /approve.
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    questions: Mapped[list["PaperQuestion"]] = relationship(
        "PaperQuestion",
        back_populates="paper",
        order_by="PaperQuestion.position",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Paper id={self.id} status={self.status}>"


class PaperQuestion(Base):
    """
    Join table between Paper and Question.

    Supports per-question ordering, display numbering, and locking.
    Using a proper join table (vs UUID[]) allows:
      - Reorder without replacing the whole array
      - Lock individual questions
      - Add/remove/swap without array surgery
    """
    __tablename__ = "paper_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # 1-based display order within the paper
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # Section label in the generated paper (may differ from original)
    paper_section: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # 1-based number printed on the paper (e.g., 1, 2, ..., 30)
    display_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # When locked=True, shuffle operations skip this question
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    paper: Mapped["Paper"] = relationship("Paper", back_populates="questions")
    question: Mapped["Question"] = relationship(
        "Question", back_populates="paper_questions"
    )

    __table_args__ = (
        UniqueConstraint("paper_id", "position", name="uq_paper_position"),
        UniqueConstraint("paper_id", "question_id", name="uq_paper_question"),
    )

    def __repr__(self) -> str:
        return (
            f"<PaperQuestion paper={self.paper_id} "
            f"q={self.question_id} pos={self.position}>"
        )


# ── Table-level indexes ───────────────────────────────────────────────────────
Index("idx_pq_paper",    PaperQuestion.paper_id)
Index("idx_pq_position", PaperQuestion.paper_id, PaperQuestion.position)


# Deferred import to avoid circular reference with question.py
from app.models.question import Question  # noqa: E402, F401
