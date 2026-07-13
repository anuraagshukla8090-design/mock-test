from __future__ import annotations

import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.question import Question
from app.schemas.question import (
    QuestionListItem,
    QuestionMetadataUpdate,
    QuestionResponse,
    QuestionStatsResponse,
)

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionListItem])
def list_questions(
    subject: str | None = None,
    chapter: str | None = None,
    difficulty: str | None = None,
    exam_name: str | None = None,
    section_type: str | None = None,
    question_type: str | None = None,
    has_diagram: bool | None = None,
    has_formula: bool | None = None,
    status: str = "active",
    ingestion_id: uuid.UUID | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = Query(default=20, le=500),
    db: Session = Depends(get_db),
):
    """
    Browse and filter questions.
    All filters are optional and combinable.
    """
    q = db.query(Question).filter(Question.status == status)

    if subject:
        q = q.filter(Question.subject == subject)
    if chapter:
        q = q.filter(Question.chapter == chapter)
    if difficulty:
        q = q.filter(Question.difficulty == difficulty)
    if exam_name:
        q = q.filter(Question.exam_name == exam_name)
    if section_type:
        q = q.filter(Question.section_type == section_type)
    if question_type:
        q = q.filter(Question.question_type == question_type)
    if has_diagram is not None:
        q = q.filter(Question.has_diagram == has_diagram)
    if has_formula is not None:
        q = q.filter(Question.has_formula == has_formula)
    if ingestion_id:
        q = q.filter(Question.ingestion_id == ingestion_id)
    if search:
        q = q.filter(
            Question.raw_text.ilike(f"%{search}%")
        )

    return q.order_by(Question.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/stats", response_model=QuestionStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Question bank statistics — counts by subject, difficulty, chapter."""
    questions = db.query(Question).filter(Question.status == "active").all()

    by_subject: Counter = Counter()
    by_difficulty: Counter = Counter()
    by_chapter: Counter = Counter()
    by_section_type: Counter = Counter()

    for q in questions:
        if q.subject:
            by_subject[q.subject] += 1
        if q.difficulty:
            by_difficulty[q.difficulty] += 1
        if q.chapter:
            by_chapter[q.chapter] += 1
        by_section_type[q.section_type] += 1

    return QuestionStatsResponse(
        total=len(questions),
        by_subject=dict(by_subject),
        by_difficulty=dict(by_difficulty),
        by_chapter=dict(by_chapter),
        by_section_type=dict(by_section_type),
    )


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get full question detail including metadata and raw LLM response."""
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, f"Question {question_id} not found.")
    return q


@router.patch("/{question_id}/metadata", response_model=QuestionResponse)
def update_metadata(
    question_id: uuid.UUID,
    updates: QuestionMetadataUpdate,
    db: Session = Depends(get_db),
):
    """
    Manually correct LLM-generated metadata.
    Only the provided fields are updated — unset fields are left unchanged.
    """
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, f"Question {question_id} not found.")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(q, field, value)

    db.commit()
    db.refresh(q)
    return q


@router.patch("/{question_id}/status", response_model=QuestionResponse)
def update_status(
    question_id: uuid.UUID,
    new_status: str,
    db: Session = Depends(get_db),
):
    """Archive or flag a question. Allowed values: active, archived, flagged."""
    if new_status not in ("active", "archived", "flagged"):
        raise HTTPException(400, "Status must be: active, archived, or flagged.")
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, f"Question {question_id} not found.")
    q.status = new_status
    db.commit()
    db.refresh(q)
    return q


@router.delete("/{question_id}", status_code=204)
def delete_question(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Hard-delete a single question.
    Also removes any PaperQuestion join records referencing it (CASCADE).
    This is irreversible.
    """
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, f"Question {question_id} not found.")
    db.delete(q)
    db.commit()

