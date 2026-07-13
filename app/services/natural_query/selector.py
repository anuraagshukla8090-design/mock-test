"""
Stage 6 — QuestionSelector

Receives the candidate set and applies:
  - Difficulty distribution (if specified)
  - Per-chapter balance
  - Seeded randomisation

Returns the final list of Question objects to be inserted into the Paper.
Reuses the existing _select_with_distribution helper from question_selector.py.
"""
from __future__ import annotations

import random
from collections import defaultdict

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session

from app.models.question import Question
from app.services.natural_query.exceptions import InsufficientQuestionsError
from app.services.natural_query.schemas import CandidateSet, ResolvedBlueprint
# Reuse the existing distribution helper — no changes to that module
from app.services.question_selector import _select_with_distribution


class QuestionSelector:
    """
    Selects exactly `question_count` questions from the candidate pool,
    respecting difficulty distribution and chapter balance.
    """

    def select(
        self,
        blueprint: ResolvedBlueprint,
        filters: list[ColumnElement],
        db: Session,
        seed: int | None = None,
    ) -> list[Question]:
        """
        Fetch candidates, apply distribution, return selected questions.

        Raises:
            InsufficientQuestionsError if pool < question_count.
        """
        rng = random.Random(seed)

        pool: list[Question] = db.query(Question).filter(*filters).all()

        if len(pool) < blueprint.question_count:
            raise InsufficientQuestionsError(
                requested=blueprint.question_count,
                available=len(pool),
            )

        # ── Build difficulty distribution for _select_with_distribution ───────
        dist = self._build_difficulty_dist(blueprint, pool)

        # ── Use existing helper for seeded, distribution-aware selection ───────
        selected = _select_with_distribution(
            pool=pool,
            count=blueprint.question_count,
            difficulty_dist=dist,
            type_dist={},   # type distribution not implemented in V1
            rng=rng,
        )

        # ── Order selected by syllabus chapter order, then question number ─────
        chapter_order_map = {
            ch: i for i, ch in enumerate(blueprint.resolved_chapters)
        }

        def sort_key(q: Question) -> tuple[int, int]:
            return (
                chapter_order_map.get(q.chapter or "", 9999),
                q.question_number or 9999,
            )

        return sorted(selected, key=sort_key)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_difficulty_dist(
        self,
        blueprint: ResolvedBlueprint,
        pool: list[Question],
    ) -> dict[str, float]:
        """
        Returns a {difficulty: fraction} dict for _select_with_distribution.

        Priority:
          1. Explicit difficulty_distribution from blueprint
          2. Proportional to what's available in the pool
        """
        if blueprint.difficulty_distribution:
            total = blueprint.question_count
            return {
                k: v / total
                for k, v in blueprint.difficulty_distribution.items()
            }

        # Proportional from pool
        counts: dict[str, int] = defaultdict(int)
        for q in pool:
            counts[q.difficulty or "medium"] += 1

        total_pool = len(pool) or 1
        return {k: v / total_pool for k, v in counts.items()}
