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
    RegenerateDraftResponse,
    RegenerateSaveRequest,
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


@router.post("/{question_id}/regenerate", response_model=RegenerateDraftResponse)
async def regenerate_question_draft(
    question_id: uuid.UUID,
    provider: str | None = Query(
        default=None,
        description="LLM provider for regeneration: 'ollama' or 'groq'. "
                    "Defaults to the REGEN_PROVIDER setting in .env.",
    ),
    db: Session = Depends(get_db),
):
    """
    Generate a new AI variant of an existing question.

    Supports 'ollama' (local) and 'groq' (cloud) providers, selectable
    per-request via the ?provider= query param. Defaults to the REGEN_PROVIDER
    setting in .env.

    The regenerated question is NOT saved to the database yet — this endpoint
    returns a preview draft. Call /regenerate/save to persist it.

    Works for any question type (MCQ, integer, match-the-following).
    The caller (frontend) is responsible for gating this to text-only questions.
    """
    import httpx
    from app.services.question_regenerator import regenerate_question

    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, f"Question {question_id} not found.")

    # Validate provider value if explicitly passed
    if provider and provider not in ("ollama", "groq"):
        raise HTTPException(400, f"Invalid provider {provider!r}. Choose 'ollama' or 'groq'.")

    try:
        draft = await regenerate_question(q, provider=provider)  # type: ignore[arg-type]
    except httpx.ConnectError:
        raise HTTPException(
            503,
            "Could not reach local Ollama. Make sure Ollama is running and the model is pulled.",
        )
    except ValueError as exc:
        # Catches missing API key or bad JSON from LLM
        raise HTTPException(422, str(exc))
    except Exception as exc:
        # Groq API errors etc.
        raise HTTPException(502, f"LLM provider error: {exc}")

    return RegenerateDraftResponse(
        original_id=question_id,
        stem_md=draft["stem_md"],
        options=draft["options"],
        answer=draft["answer"],
        section_type=draft["section_type"],
        provider_used=draft.get("provider_used", "ollama"),
    )


@router.post("/{question_id}/regenerate/save", response_model=QuestionResponse, status_code=201)
def save_regenerated_question(
    question_id: uuid.UUID,
    body: RegenerateSaveRequest,
    db: Session = Depends(get_db),
):
    """
    Persist an accepted AI-regenerated question draft as a new Question row.

    - Copies all metadata (subject, chapter, topic, difficulty, etc.) from the original.
    - Sets generation_type="ai_regenerated" and parent_question_id=original.id.
    - The original question is never modified.
    """
    original = db.get(Question, question_id)
    if not original:
        raise HTTPException(404, f"Original question {question_id} not found.")

    # Detect if new stem contains LaTeX formulas
    has_formula = any(
        marker in body.stem_md
        for marker in ("$", "\\frac", "\\sqrt", "\\int", "\\sum")
    )

    new_q = Question(
        # ── Source (inherit ingestion context but mark as regenerated)
        ingestion_id=original.ingestion_id,
        source_pdf=original.source_pdf,
        source_page=None,
        question_number=None,
        # ── Content from the accepted draft
        stem_md=body.stem_md,
        options=body.options,
        answer=body.answer,
        images=[],          # text-only variant — no images
        section_type=original.section_type,
        section_label=original.section_label,
        # ── Metadata inherited from the original
        exam_name=original.exam_name,
        subject=original.subject,
        chapter=original.chapter,
        topic=original.topic,
        subtopic=original.subtopic,
        difficulty=original.difficulty,
        question_type=original.question_type,
        concepts=list(original.concepts or []),
        has_diagram=False,
        has_formula=has_formula,
        # ── Lineage
        generation_type="ai_regenerated",
        parent_question_id=original.id,
        # ── Status
        status="active",
    )
    db.add(new_q)
    db.commit()
    db.refresh(new_q)
    return new_q
