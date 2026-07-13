"""
Stage 5 — CandidatePreview

Queries the database efficiently using SQL aggregation (COUNT + GROUP BY)
to build distribution breakdowns, then fetches only the first 5 sample
questions with LIMIT 5.

Previous implementation loaded ALL matching questions into Python memory,
which became expensive (seconds + hundreds of MB) for broad queries
like "All Physics JEE Main questions".
"""
from __future__ import annotations

import re
from collections import Counter

from sqlalchemy import ColumnElement, func
from sqlalchemy.orm import Session

from app.models.question import Question
from app.services.natural_query.schemas import (
    CandidateSet,
    QuestionPreview,
    ResolvedBlueprint,
)

# Regex to strip LaTeX-style math from stem text for previews
_LATEX_RE = re.compile(r"\$\$?.*?\$\$?", re.DOTALL)


def _stem_preview(q: Question, max_len: int = 120) -> str:
    """Return a short plain-text preview of the question stem."""
    text = q.raw_text or q.stem_md or ""
    # Strip markdown math delimiters for readability
    text = _LATEX_RE.sub("[formula]", text)
    # Collapse whitespace
    text = " ".join(text.split())
    return text[:max_len].rstrip() + ("…" if len(text) > max_len else "")


class CandidatePreview:
    """
    Queries the DB and returns a CandidateSet showing what's available
    for the given filters — without loading the full result set into memory.

    Uses SQL COUNT + GROUP BY for all distribution tallies, and fetches
    only 5 sample rows with LIMIT.
    """

    def preview(
        self,
        blueprint: ResolvedBlueprint,
        filters: list[ColumnElement],
        db: Session,
    ) -> CandidateSet:
        """
        Build a CandidateSet using efficient SQL queries.

        Steps:
          1. COUNT(*) for total — O(index) not O(all rows)
          2. GROUP BY chapter/difficulty/section_type/question_type for breakdowns
          3. LIMIT 5 for sample questions, ordered by chapter position then question number
        """
        base = db.query(Question).filter(*filters)

        # ── 1. Total count ────────────────────────────────────────────────────
        total: int = db.query(func.count(Question.id)).filter(*filters).scalar() or 0

        # ── 2. Distribution breakdowns via GROUP BY ───────────────────────────
        by_chapter = dict(
            db.query(Question.chapter, func.count(Question.id))
            .filter(*filters)
            .group_by(Question.chapter)
            .all()
        )
        # Remove None key if any questions lack a chapter
        by_chapter.pop(None, None)

        by_difficulty = dict(
            db.query(Question.difficulty, func.count(Question.id))
            .filter(*filters)
            .group_by(Question.difficulty)
            .all()
        )
        by_difficulty.pop(None, None)

        by_section_type = dict(
            db.query(Question.section_type, func.count(Question.id))
            .filter(*filters)
            .group_by(Question.section_type)
            .all()
        )

        by_question_type = dict(
            db.query(Question.question_type, func.count(Question.id))
            .filter(*filters)
            .group_by(Question.question_type)
            .all()
        )
        by_question_type.pop(None, None)

        # ── 3. Sample questions — LIMIT 5 ────────────────────────────────────
        # Sort by question_number as a proxy for syllabus order within a source PDF.
        # A syllabus-order sort would require a subquery join; question_number is
        # a good approximation and keeps this query simple.
        sample_rows: list[Question] = (
            base
            .order_by(Question.question_number.asc().nullslast())
            .limit(5)
            .all()
        )

        sample = [
            QuestionPreview(
                id=str(q.id),
                question_number=q.question_number,
                chapter=q.chapter,
                difficulty=q.difficulty,
                question_type=q.question_type,
                stem_preview=_stem_preview(q),
            )
            for q in sample_rows
        ]

        can_generate = total >= blueprint.question_count

        return CandidateSet(
            total_available=total,
            by_chapter=by_chapter,
            by_difficulty=by_difficulty,
            by_section_type=by_section_type,
            by_question_type=by_question_type,
            sample_questions=sample,
            can_generate=can_generate,
            shortage=max(0, blueprint.question_count - total),
            resolved_blueprint=blueprint,
        )
