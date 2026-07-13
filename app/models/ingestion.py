from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import String, Text, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Ingestion(Base):
    """
    Tracks a single PDF upload through the full ingestion pipeline.

    State machine:
        UPLOADED → MINERU_COMPLETE → QUESTIONS_BUILT → METADATA_COMPLETE → SAVED
                                                                          ↘ FAILED (from any stage)
    """
    __tablename__ = "ingestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # ── Source ────────────────────────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Upload-form fields ────────────────────────────────────────────────────
    # Provided by the teacher at upload time. Never overridden by LLM.
    exam_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    layout_type: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── State machine ─────────────────────────────────────────────────────────
    # Allowed values: UPLOADED | MINERU_COMPLETE | QUESTIONS_BUILT |
    #                 METADATA_COMPLETE | SAVED | FAILED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UPLOADED")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_at_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── MinerU output paths ───────────────────────────────────────────────────
    # Absolute path to the output directory created by MinerU.
    # Stores content_list.json, *.md, and images/ subdirectory.
    # Set after MINERU_COMPLETE. Allows Question Builder to be rerun
    # without reprocessing the PDF.
    mineru_output_dir: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Pipeline summary ──────────────────────────────────────────────────────
    questions_found: Mapped[int] = mapped_column(Integer, default=0)
    questions_saved: Mapped[int] = mapped_column(Integer, default=0)
    detected_layout: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_subjects: Mapped[list | None] = mapped_column(JSONB, default=list)

    processing_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Processing report ─────────────────────────────────────────────────────
    # Generated after SAVED. Contains per-question breakdown, warnings, errors.
    # Schema:
    # {
    #   "questions_detected": int,
    #   "questions_stored": int,
    #   "questions_skipped": int,
    #   "answers_mapped": int,
    #   "images_linked": int,
    #   "processing_time_s": float,
    #   "warnings": [str, ...],
    #   "errors": [str, ...],
    #   "per_question": [
    #     {"number": int, "status": "ok"|"skipped"|"error", "warnings": [str]}
    #   ]
    # }
    processing_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Ingestion id={self.id} file={self.filename!r} status={self.status}>"
