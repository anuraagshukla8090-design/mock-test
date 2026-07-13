from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import Boolean, String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Question(Base):
    """
    A single parsed question extracted from a PDF.

    Content fields store markdown with inline LaTeX — the frontend renders them
    directly with react-markdown + rehype-katex.
    """
    __tablename__ = "questions"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    # ── Source tracing ────────────────────────────────────────────────────────
    ingestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_pdf: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Content ───────────────────────────────────────────────────────────────
    # stem_md: markdown text with inline $latex$ and $$display$$ LaTeX
    stem_md: Mapped[str] = mapped_column(Text, nullable=False)

    # options: {"A": "md string", "B": "md string", "C": "...", "D": "..."}
    #          or {} for integer-type questions
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # answer: "A" / "B" / "C" / "D" for MCQ, or "42" for integer-type
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # images: [{"filename": "abc123.jpg", "position": "stem" | "options"}]
    images: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # section_type: "mcq" | "integer"
    section_type: Mapped[str] = mapped_column(String(16), nullable=False, default="mcq")

    # section_label: "SECTION-A" | "SECTION-B" (from the PDF header)
    section_label: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── LLM-generated metadata ────────────────────────────────────────────────
    exam_name: Mapped[str | None] = mapped_column(Text, nullable=True)   # "JEE Main"
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)     # "physics"
    chapter: Mapped[str | None] = mapped_column(Text, nullable=True)     # "Rotational Motion"
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)       # "Moment of Inertia"
    subtopic: Mapped[str | None] = mapped_column(Text, nullable=True)    # "Parallel Axis Theorem"
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)  # "easy|medium|hard"
    question_type: Mapped[str | None] = mapped_column(Text, nullable=True)     # "conceptual|numerical|..."
    concepts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    has_diagram: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_formula: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Raw JSON response from the LLM — preserved for debugging and future
    # metadata migrations (e.g., if the prompt changes and you want to re-parse
    # old responses without calling the LLM again).
    llm_raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Full-text search ──────────────────────────────────────────────────────
    # LaTeX-stripped plain text version of stem + options.
    # Generated at ingestion time. Used for PostgreSQL full-text search.
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Soft status ───────────────────────────────────────────────────────────
    # "active" | "archived" | "flagged"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    # ── NOTE: Semantic search (pgvector embedding) is planned for V2. ─────────
    # When implementing: ALTER TABLE questions ADD COLUMN embedding VECTOR(384);
    # No schema changes needed beyond that single column addition.

    # ── Relationships ─────────────────────────────────────────────────────────
    paper_questions: Mapped[list["PaperQuestion"]] = relationship(
        "PaperQuestion", back_populates="question"
    )

    def __repr__(self) -> str:
        return (
            f"<Question id={self.id} number={self.question_number} "
            f"subject={self.subject!r} chapter={self.chapter!r}>"
        )


# ── Table-level indexes ───────────────────────────────────────────────────────
Index("idx_q_ingestion",  Question.ingestion_id)
Index("idx_q_subject",    Question.subject)
Index("idx_q_chapter",    Question.chapter)
Index("idx_q_difficulty", Question.difficulty)
Index("idx_q_exam",       Question.exam_name)
Index("idx_q_status",     Question.status)


# Deferred import to avoid circular references
from app.models.paper import PaperQuestion  # noqa: E402, F401
