from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.services.question_builder.registry import VALID_LAYOUT_TYPES

# Allowed subject values — extensible list
VALID_SUBJECTS = [
    "physics", "chemistry", "mathematics", "biology",
    "english", "hindi", "history", "geography",
]


class IngestionCreate(BaseModel):
    filename: str


class IngestionStatusResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    # Upload-form fields
    exam_name: str | None = None
    subject: str | None = None
    layout_type: str | None = None
    # State
    error_message: str | None = None
    failed_at_stage: str | None = None
    questions_found: int
    questions_saved: int
    detected_layout: str | None = None
    detected_subjects: list[str] = []
    processing_time_s: float | None = None
    processing_report: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestionListItem(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    exam_name: str | None = None
    subject: str | None = None
    layout_type: str | None = None
    questions_saved: int
    created_at: datetime

    model_config = {"from_attributes": True}
