from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: uuid.UUID
    ingestion_id: uuid.UUID
    source_pdf: str
    source_page: int | None = None
    question_number: int | None = None
    stem_md: str
    options: dict
    answer: str
    images: list[dict] = []
    section_type: str
    section_label: str | None = None
    exam_name: str | None = None
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: str | None = None
    question_type: str | None = None
    concepts: list = []
    has_diagram: bool
    has_formula: bool
    status: str
    generation_type: str = "ingested"
    parent_question_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionListItem(BaseModel):
    id: uuid.UUID
    question_number: int | None = None
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    question_type: str | None = None
    has_diagram: bool
    has_formula: bool
    section_type: str
    status: str
    generation_type: str = "ingested"
    parent_question_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class QuestionMetadataUpdate(BaseModel):
    """For PATCH /api/questions/{id}/metadata — teacher manually corrects tags."""
    exam_name: str | None = None
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    subtopic: str | None = None
    difficulty: str | None = None
    question_type: str | None = None
    concepts: list[str] | None = None
    has_diagram: bool | None = None
    has_formula: bool | None = None


class QuestionStatsResponse(BaseModel):
    total: int
    by_subject: dict[str, int]
    by_difficulty: dict[str, int]
    by_chapter: dict[str, int]
    by_section_type: dict[str, int]


class RegenerateDraftResponse(BaseModel):
    """Returned by POST /api/questions/{id}/regenerate — not yet persisted."""
    original_id: uuid.UUID
    stem_md: str
    options: dict
    answer: str
    section_type: str
    provider_used: str = "ollama"  # "ollama" | "groq"


class RegenerateSaveRequest(BaseModel):
    """Body for POST /api/questions/{id}/regenerate/save — teacher accepted the draft."""
    stem_md: str
    options: dict
    answer: str
