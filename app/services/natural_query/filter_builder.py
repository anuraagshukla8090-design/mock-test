"""
Stage 4 — SQLFilterBuilder

Pure function: given a ResolvedBlueprint, returns a list of SQLAlchemy
filter expressions. Never executes queries.

Keeping this as a separate class means:
  - Filters are testable without a real DB
  - CandidatePreview and QuestionSelector both use the same filters
  - Adding a new filter requires changes only here
"""
from __future__ import annotations

from sqlalchemy import ColumnElement, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast

from app.models.question import Question
from app.services.natural_query.schemas import ResolvedBlueprint


class SQLFilterBuilder:
    """Builds SQLAlchemy filter expressions from a ResolvedBlueprint."""

    def build(self, blueprint: ResolvedBlueprint) -> list[ColumnElement]:
        """
        Returns a list of filter expressions to pass to Query.filter(*filters).
        All conditions are AND-joined (i.e. the question must satisfy every filter).
        """
        filters: list[ColumnElement] = []

        # ── Always required ───────────────────────────────────────────────────
        filters.append(Question.status == "active")
        # Exact match — exam names and subjects are canonical since the normalizer
        # was applied at ingestion time and at LLM parse time.
        filters.append(Question.exam_name == blueprint.exam_name)
        filters.append(Question.subject == blueprint.subject)

        # ── Chapter inclusion ─────────────────────────────────────────────────
        # Empty list = mode=all_, no filter needed
        if blueprint.resolved_chapters:
            filters.append(Question.chapter.in_(blueprint.resolved_chapters))

        # ── Chapter exclusion ─────────────────────────────────────────────────
        if blueprint.excluded_chapters:
            filters.append(~Question.chapter.in_(blueprint.excluded_chapters))

        # ── Difficulty ───────────────────────────────────────────────────────
        # Note: difficulty_distribution is handled in QuestionSelector, not here.
        # Only the single-value difficulty filter goes to SQL.
        if blueprint.difficulty:
            filters.append(Question.difficulty == blueprint.difficulty)

        # ── Question type ─────────────────────────────────────────────────────
        if blueprint.question_type:
            filters.append(Question.question_type == blueprint.question_type)

        # ── Section type (MCQ vs integer) ─────────────────────────────────────
        if blueprint.section_type:
            filters.append(Question.section_type == blueprint.section_type)

        # ── Boolean flags ─────────────────────────────────────────────────────
        if blueprint.has_formula is not None:
            filters.append(Question.has_formula == blueprint.has_formula)

        if blueprint.has_diagram is not None:
            filters.append(Question.has_diagram == blueprint.has_diagram)

        # ── Concepts — OR semantics (V1) ──────────────────────────────────────
        # V1: concept_match_mode="any" → question must have ANY listed concept.
        # V2 extension: when concept_match_mode="all", switch to AND loop.
        #
        # PostgreSQL JSONB @> operator: '[concept]'::jsonb checks if the
        # question's concepts JSONB array contains the given element.
        if blueprint.concepts:
            if blueprint.concept_match_mode == "all":
                # AND semantics: all concepts must be present (V2 path)
                for concept in blueprint.concepts:
                    filters.append(
                        Question.concepts.op("@>")(cast([concept], JSONB))
                    )
            else:
                # OR semantics: any concept matches (V1 default)
                or_conditions = [
                    Question.concepts.op("@>")(cast([c], JSONB))
                    for c in blueprint.concepts
                ]
                filters.append(or_(*or_conditions))

        return filters
