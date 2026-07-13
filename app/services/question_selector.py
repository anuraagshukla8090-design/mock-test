from __future__ import annotations

import random
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.question import Question


@dataclass
class PaperBlueprint:
    """Structured representation of what the teacher wants in a paper."""
    exam_name: str
    subject: str
    total_questions: int
    section_a_count: int          # MCQ
    section_b_count: int          # Integer-type
    chapters: list[str]
    difficulty_distribution: dict[str, float]  # {"easy": 0.2, "medium": 0.6, "hard": 0.2}
    type_distribution: dict[str, float]        # {"conceptual": 0.6, "numerical": 0.4}
    seed: int
    special_instructions: str | None = None


def select_questions(
    blueprint: PaperBlueprint,
    db: Session,
) -> list[Question]:
    """
    Select questions from the database to satisfy a PaperBlueprint.

    Algorithm:
      1. Fetch all active candidates matching subject + chapters + exam
      2. Split into Section A (MCQ) and Section B (integer)
      3. Score each question against the difficulty + type distribution
      4. Use seeded random to shuffle within equal-score buckets
      5. Pick top N for each section
      6. Order results by chapter (syllabus order) then by section

    All randomness is seeded — same blueprint + seed = same paper every time.
    Different seed = different valid selection.
    """
    rng = random.Random(blueprint.seed)

    # ── Fetch candidates ──────────────────────────────────────────────────────
    query = db.query(Question).filter(
        Question.status == "active",
        Question.subject == blueprint.subject,
    )

    if blueprint.exam_name:
        # Exact match — exam names are now canonical (e.g. "JEE Main", "NEET")
        query = query.filter(Question.exam_name == blueprint.exam_name)

    if blueprint.chapters:
        query = query.filter(Question.chapter.in_(blueprint.chapters))

    all_candidates = query.all()

    # ── Split by section type ─────────────────────────────────────────────────
    section_a_pool = [q for q in all_candidates if q.section_type == "mcq"]
    section_b_pool = [q for q in all_candidates if q.section_type == "integer"]

    # ── Select with distribution ──────────────────────────────────────────────
    selected_a = _select_with_distribution(
        pool=section_a_pool,
        count=blueprint.section_a_count,
        difficulty_dist=blueprint.difficulty_distribution,
        type_dist=blueprint.type_distribution,
        rng=rng,
    )
    selected_b = _select_with_distribution(
        pool=section_b_pool,
        count=blueprint.section_b_count,
        difficulty_dist=blueprint.difficulty_distribution,
        type_dist=blueprint.type_distribution,
        rng=rng,
    )

    # ── Order by chapter (syllabus order) ─────────────────────────────────────
    chapter_order = {ch: i for i, ch in enumerate(blueprint.chapters)}

    def chapter_key(q: Question) -> int:
        return chapter_order.get(q.chapter or "", 9999)

    ordered_a = sorted(selected_a, key=chapter_key)
    ordered_b = sorted(selected_b, key=chapter_key)

    return ordered_a + ordered_b


def get_alternatives(
    paper_question_id_to_exclude: list,  # list of question UUIDs already in paper
    reference_question: Question,
    db: Session,
    count: int = 3,
) -> list[Question]:
    """
    Find alternative questions with the same chapter and similar difficulty
    as the reference question, excluding questions already in the paper.
    """
    query = db.query(Question).filter(
        Question.status == "active",
        Question.subject == reference_question.subject,
        Question.chapter == reference_question.chapter,
        Question.section_type == reference_question.section_type,
        Question.id.notin_(paper_question_id_to_exclude),
        Question.id != reference_question.id,
    )

    if reference_question.difficulty:
        query = query.filter(Question.difficulty == reference_question.difficulty)

    # Return random selection so teacher sees variety each time
    candidates = query.limit(count * 3).all()
    random.shuffle(candidates)
    return candidates[:count]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _select_with_distribution(
    pool: list[Question],
    count: int,
    difficulty_dist: dict[str, float],
    type_dist: dict[str, float],
    rng: random.Random,
) -> list[Question]:
    """
    Select `count` questions from `pool` respecting difficulty + type distributions.

    Strategy:
      - Calculate target counts per difficulty tier
      - For each tier, pick from that bucket (shuffled with seed)
      - Remaining questions from over-supplied tiers go into a leftovers pool
      - Any shortfall (tier had fewer questions than its target) is filled
        from leftovers so the final count always equals `count` when enough
        total questions exist.

    Bug fixed: the previous version had a dead variable `leftovers_needed`
    and an `else:` guard that prevented leftovers from being collected when
    a bucket was deficient. This caused the returned list to be shorter than
    `count` even when the pool had enough questions overall.
    """
    if not pool or count == 0:
        return []

    # Group by difficulty
    by_difficulty: dict[str, list[Question]] = {"easy": [], "medium": [], "hard": []}
    for q in pool:
        tier = q.difficulty or "medium"
        if tier in by_difficulty:
            by_difficulty[tier].append(q)

    # Shuffle each bucket with seed for reproducibility
    for bucket in by_difficulty.values():
        rng.shuffle(bucket)

    # Calculate targets
    targets = {
        tier: round(frac * count)
        for tier, frac in difficulty_dist.items()
    }
    # Fix rounding to ensure sum == count
    diff = count - sum(targets.values())
    if diff != 0:
        # Add/subtract remainder from "medium" bucket
        targets["medium"] = targets.get("medium", 0) + diff

    # Pick from each bucket; ALL surplus goes into leftovers regardless of
    # whether the bucket met its target (fixes the dead-variable bug).
    selected: list[Question] = []
    leftovers: list[Question] = []

    for tier, target in targets.items():
        bucket = by_difficulty.get(tier, [])
        selected.extend(bucket[:target])
        # Surplus questions (beyond target) become candidates for filling
        # shortfalls from other tiers — always collected, not guarded.
        leftovers.extend(bucket[target:])

    # Fill any shortfall (caused by under-supplied tiers) from leftovers
    while len(selected) < count and leftovers:
        selected.append(leftovers.pop(0))

    return selected[:count]
