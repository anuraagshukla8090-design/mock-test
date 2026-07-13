"""
Pipeline orchestrator — runs all 6 stages in sequence.

  NaturalQueryParser  (LLM call)
  → BlueprintValidator (pure validation)
  → SyllabusResolver   (DB lookup + range expansion)
  → SQLFilterBuilder   (pure filter construction)
  → CandidatePreview   (DB query → counts + samples)
  → QuestionSelector   (DB query → selected Question objects)
  → create_draft       (DB write → Paper record)

Returns SyllabusQueryResponse.
If can_generate is False, paper_id is None and create_draft is skipped.
"""
from __future__ import annotations

import random

from sqlalchemy.orm import Session, joinedload

from app.models.paper import Paper, PaperQuestion
from app.services.natural_query.candidate_preview import CandidatePreview
from app.services.natural_query.exceptions import (
    InsufficientQuestionsError,
    NaturalQueryError,
)
from app.services.natural_query.filter_builder import SQLFilterBuilder
from app.services.natural_query.parser import NaturalQueryParser
from app.services.natural_query.resolver import SyllabusResolver
from app.services.natural_query.schemas import (
    CandidateSet,
    SyllabusQueryResponse,
)
from app.services.natural_query.selector import QuestionSelector
from app.services.natural_query.validator import BlueprintValidator
from app.services.paper_generator import create_draft
from app.services.question_selector import PaperBlueprint


def _resolved_to_legacy_blueprint(
    resolved,
    seed: int,
) -> PaperBlueprint:
    """
    Convert a ResolvedBlueprint to the legacy PaperBlueprint that
    create_draft() expects. No changes to paper_generator.py needed.
    """
    dist = resolved.difficulty_distribution
    if dist:
        total = resolved.question_count
        frac_dist = {k: v / total for k, v in dist.items()}
    else:
        frac_dist = {"easy": 0.2, "medium": 0.5, "hard": 0.3}

    return PaperBlueprint(
        exam_name=resolved.exam_name,
        subject=resolved.subject,
        total_questions=resolved.question_count,
        section_a_count=resolved.question_count,  # will be split by section_type in create_draft
        section_b_count=0,
        chapters=resolved.resolved_chapters,
        difficulty_distribution=frac_dist,
        type_distribution={"conceptual": 0.5, "numerical": 0.5},
        seed=seed,
        special_instructions=resolved.chapter_range_description,
    )


def _paper_to_dict(paper: Paper, db: Session) -> dict:
    """
    Serialize the Paper + its PaperQuestions for the API response.
    Keeps the pipeline self-contained (no circular imports with schemas/paper).
    """
    p = (
        db.query(Paper)
        .options(
            joinedload(Paper.questions).joinedload(PaperQuestion.question)
        )
        .filter(Paper.id == paper.id)
        .first()
    )
    return {
        "id": str(p.id),
        "prompt": p.prompt,
        "status": p.status,
        "blueprint": p.blueprint,
        "created_at": p.created_at.isoformat(),
        "question_count": len(p.questions),
        "questions": [
            {
                "id": str(pq.id),
                "position": pq.position,
                "paper_section": pq.paper_section,
                "display_number": pq.display_number,
                "question_id": str(pq.question_id),
                "chapter": pq.question.chapter,
                "difficulty": pq.question.difficulty,
                "question_type": pq.question.question_type,
                "section_type": pq.question.section_type,
            }
            for pq in sorted(p.questions, key=lambda q: q.position)
        ],
    }


class SyllabusQueryPipeline:
    """Orchestrates all 6 stages of the natural query pipeline."""

    def __init__(self) -> None:
        self._parser = NaturalQueryParser()
        self._validator = BlueprintValidator()
        self._resolver = SyllabusResolver()
        self._filter_builder = SQLFilterBuilder()
        self._preview = CandidatePreview()
        self._selector = QuestionSelector()

    async def run(
        self,
        prompt: str,
        db: Session,
    ) -> SyllabusQueryResponse:
        """
        Full pipeline. Returns SyllabusQueryResponse.

        If can_generate is True  → draft Paper created, paper_id is set.
        If can_generate is False → no Paper created, paper_id is None.

        All NaturalQueryError subclasses propagate to the API layer for
        conversion into appropriate HTTP responses.
        """
        # ── Stage 1: Parse ────────────────────────────────────────────────────
        raw_blueprint = await self._parser.parse(prompt)

        # ── Stage 2: Validate ─────────────────────────────────────────────────
        validated = self._validator.validate(raw_blueprint)

        # ── Stage 3: Resolve chapters from syllabus ───────────────────────────
        resolved = self._resolver.resolve(validated, db)

        # ── Stage 4: Build SQL filters ────────────────────────────────────────
        filters = self._filter_builder.build(resolved)

        # ── Stage 5: Candidate preview ────────────────────────────────────────
        candidate_set: CandidateSet = self._preview.preview(resolved, filters, db)

        # ── Short-circuit if not enough questions ─────────────────────────────
        if not candidate_set.can_generate:
            return SyllabusQueryResponse(
                paper_id=None,
                candidates=candidate_set,
                paper=None,
            )

        # ── Stage 6: Select questions ─────────────────────────────────────────
        seed = random.randint(1, 2**31)
        try:
            selected = self._selector.select(resolved, filters, db, seed=seed)
        except InsufficientQuestionsError:
            # Edge case: preview said ok but selector found fewer
            # (e.g., concurrent deletes). Return the preview without a paper.
            candidate_set = CandidateSet(
                **{**candidate_set.model_dump(), "can_generate": False,
                   "shortage": resolved.question_count}
            )
            return SyllabusQueryResponse(
                paper_id=None,
                candidates=candidate_set,
                paper=None,
            )

        # ── Stage 7: Create draft paper ───────────────────────────────────────
        legacy_bp = _resolved_to_legacy_blueprint(resolved, seed)
        paper = create_draft(prompt, legacy_bp, selected, db)

        return SyllabusQueryResponse(
            paper_id=str(paper.id),
            candidates=candidate_set,
            paper=_paper_to_dict(paper, db),
        )
