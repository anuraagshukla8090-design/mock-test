"""
Syllabus management API.

GET  /api/syllabus                       → list exam+subject combinations
GET  /api/syllabus/{exam_name}/{subject} → ordered chapter list
POST /api/syllabus/{exam_name}/{subject} → add/update a chapter (admin, V1 no auth)
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.syllabus import Syllabus

router = APIRouter(prefix="/api/syllabus", tags=["syllabus"])


# ── Response schemas ──────────────────────────────────────────────────────────

class SyllabusPartition(BaseModel):
    exam_name: str
    subject: str
    chapter_count: int


class SyllabusChapter(BaseModel):
    chapter_order: int
    chapter_name: str
    chapter_aliases: list[str]


class AddChapterRequest(BaseModel):
    chapter_name: str
    chapter_order: int
    chapter_aliases: list[str] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[SyllabusPartition])
def list_syllabuses(db: Session = Depends(get_db)):
    """List all (exam_name, subject) combinations that have syllabus data."""
    from sqlalchemy import func
    rows = (
        db.query(
            Syllabus.exam_name,
            Syllabus.subject,
            func.count(Syllabus.id).label("chapter_count"),
        )
        .group_by(Syllabus.exam_name, Syllabus.subject)
        .order_by(Syllabus.exam_name, Syllabus.subject)
        .all()
    )
    return [
        SyllabusPartition(
            exam_name=r.exam_name,
            subject=r.subject,
            chapter_count=r.chapter_count,
        )
        for r in rows
    ]


@router.get("/{exam_name}/{subject}", response_model=list[SyllabusChapter])
def get_syllabus(
    exam_name: Annotated[str, Path(description="e.g. 'JEE Main'")],
    subject: Annotated[str, Path(description="e.g. 'physics'")],
    db: Session = Depends(get_db),
):
    """Return ordered chapter list for an exam+subject. Case-sensitive exam_name."""
    rows = (
        db.query(Syllabus)
        .filter(
            Syllabus.exam_name == exam_name,
            Syllabus.subject == subject,
        )
        .order_by(Syllabus.chapter_order)
        .all()
    )
    if not rows:
        raise HTTPException(
            404,
            f"No syllabus found for exam='{exam_name}', subject='{subject}'. "
            "Use GET /api/syllabus to list available combinations.",
        )
    return [
        SyllabusChapter(
            chapter_order=r.chapter_order,
            chapter_name=r.chapter_name,
            chapter_aliases=r.chapter_aliases or [],
        )
        for r in rows
    ]


@router.post("/{exam_name}/{subject}", status_code=201)
def add_chapter(
    exam_name: str,
    subject: str,
    request: AddChapterRequest,
    db: Session = Depends(get_db),
):
    """
    Add or update a chapter in the syllabus.
    If a chapter with the same chapter_order already exists, it is updated.
    (Admin-only endpoint — no auth in V1.)
    """
    existing = (
        db.query(Syllabus)
        .filter(
            Syllabus.exam_name == exam_name,
            Syllabus.subject == subject,
            Syllabus.chapter_order == request.chapter_order,
        )
        .first()
    )

    if existing:
        existing.chapter_name = request.chapter_name
        existing.chapter_aliases = request.chapter_aliases
        db.commit()
        return {
            "action": "updated",
            "exam_name": exam_name,
            "subject": subject,
            "chapter_order": request.chapter_order,
            "chapter_name": request.chapter_name,
        }

    row = Syllabus(
        id=uuid.uuid4(),
        exam_name=exam_name,
        subject=subject,
        chapter_name=request.chapter_name,
        chapter_order=request.chapter_order,
        chapter_aliases=request.chapter_aliases,
    )
    db.add(row)
    db.commit()
    return {
        "action": "created",
        "exam_name": exam_name,
        "subject": subject,
        "chapter_order": request.chapter_order,
        "chapter_name": request.chapter_name,
    }
