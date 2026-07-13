from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.question import QuestionResponse


class GeneratePaperRequest(BaseModel):
    prompt: str


class PaperQuestionItem(BaseModel):
    id: uuid.UUID                   # PaperQuestion row ID
    paper_id: uuid.UUID
    question_id: uuid.UUID
    position: int
    paper_section: str | None = None
    display_number: int | None = None
    locked: bool
    question: QuestionResponse

    model_config = {"from_attributes": True}


class PaperResponse(BaseModel):
    id: uuid.UUID
    prompt: str
    blueprint: dict
    status: str
    notes: str | None = None
    questions: list[PaperQuestionItem] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperListItem(BaseModel):
    id: uuid.UUID
    prompt: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SwapQuestionRequest(BaseModel):
    new_question_id: uuid.UUID


class AddQuestionRequest(BaseModel):
    question_id: uuid.UUID
    position: int | None = None     # If None, appends to end
    paper_section: str | None = None


class ApproveRequest(BaseModel):
    notes: str | None = None


class AlternativesResponse(BaseModel):
    alternatives: list[QuestionResponse]
