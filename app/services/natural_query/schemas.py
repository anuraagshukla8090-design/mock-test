"""
Pydantic models for every stage of the natural query pipeline.

Flow:
  RawBlueprint (LLM output)
  → ValidatedBlueprint (post BlueprintValidator)
  → ResolvedBlueprint  (post SyllabusResolver — chapters are concrete lists)
  → CandidateSet       (post CandidatePreview)
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


# ── Chapter filter modes ──────────────────────────────────────────────────────

class ChapterFilterMode(str, Enum):
    exact   = "exact"    # single chapter
    upto    = "upto"     # all chapters up to AND INCLUDING the named chapter
    from_   = "from"     # from chapter onwards (inclusive)
    between = "between"  # from chapter_from to chapter_to (both inclusive)
    after   = "after"    # all chapters AFTER the named one (exclusive)
    all_    = "all"      # no chapter filter — use all chapters for exam+subject


# ── Stage 1 output: what the LLM returns ─────────────────────────────────────

class RawBlueprint(BaseModel):
    """
    Direct parse of the LLM JSON response.
    Not yet validated for cross-field consistency.
    """
    exam_name: str
    subject: str

    # Chapter filter — only the field matching the mode is non-null
    chapter_filter_mode: ChapterFilterMode = ChapterFilterMode.all_
    chapter: str | None = None        # mode=exact
    chapter_upto: str | None = None   # mode=upto
    chapter_from: str | None = None   # mode=from, between
    chapter_to: str | None = None     # mode=between (end)
    chapter_after: str | None = None  # mode=after

    # Chapters to exclude after range expansion
    exclude_chapters: list[str] = []

    # How many questions to generate
    question_count: int = 30

    # Optional filters
    difficulty: str | None = None
    difficulty_distribution: dict[str, int] | None = None
    question_type: str | None = None
    section_type: str | None = None
    has_formula: bool | None = None
    has_diagram: bool | None = None
    concepts: list[str] = []

    # V1 default = "any" (OR semantics). "all" = AND semantics (V2).
    concept_match_mode: Literal["any", "all"] = "any"


# ── Stage 2 output: validated blueprint ──────────────────────────────────────

class ValidatedBlueprint(RawBlueprint):
    """
    RawBlueprint after cross-field validation by BlueprintValidator.
    If this model is constructed, all fields are internally consistent.
    """

    @model_validator(mode="after")
    def _check_mode_fields(self) -> "ValidatedBlueprint":
        mode = self.chapter_filter_mode
        if mode == ChapterFilterMode.exact and not self.chapter:
            raise ValueError("chapter_filter_mode='exact' requires 'chapter' field")
        if mode == ChapterFilterMode.upto and not self.chapter_upto:
            raise ValueError("chapter_filter_mode='upto' requires 'chapter_upto' field")
        if mode == ChapterFilterMode.from_ and not self.chapter_from:
            raise ValueError("chapter_filter_mode='from' requires 'chapter_from' field")
        if mode == ChapterFilterMode.between and not (self.chapter_from and self.chapter_to):
            raise ValueError(
                "chapter_filter_mode='between' requires both "
                "'chapter_from' and 'chapter_to' fields"
            )
        if mode == ChapterFilterMode.after and not self.chapter_after:
            raise ValueError("chapter_filter_mode='after' requires 'chapter_after' field")
        return self

    @field_validator("question_count")
    @classmethod
    def _check_count(cls, v: int) -> int:
        if not (1 <= v <= 200):
            raise ValueError("question_count must be between 1 and 200")
        return v

    @field_validator("difficulty")
    @classmethod
    def _check_difficulty(cls, v: str | None) -> str | None:
        if v is not None and v not in ("easy", "medium", "hard"):
            raise ValueError(f"difficulty must be 'easy', 'medium', or 'hard', got '{v}'")
        return v

    @field_validator("section_type")
    @classmethod
    def _check_section_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("mcq", "integer"):
            raise ValueError(f"section_type must be 'mcq' or 'integer', got '{v}'")
        return v

    @model_validator(mode="after")
    def _check_distribution(self) -> "ValidatedBlueprint":
        dist = self.difficulty_distribution
        if dist is not None:
            total = sum(dist.values())
            if total != self.question_count:
                raise ValueError(
                    f"difficulty_distribution values sum to {total} "
                    f"but question_count is {self.question_count}"
                )
            for key in dist:
                if key not in ("easy", "medium", "hard"):
                    raise ValueError(
                        f"difficulty_distribution key '{key}' invalid — "
                        "use 'easy', 'medium', 'hard'"
                    )
        return self


# ── Stage 3 output: resolved blueprint (chapters are concrete lists) ──────────

class ResolvedBlueprint(BaseModel):
    """
    Output of SyllabusResolver.
    Chapter boundary names are replaced with ordered concrete chapter lists.
    """
    exam_name: str
    subject: str

    # Ordered list of chapter_name strings from the syllabus table.
    # Empty = no chapter filter (mode=all_ with no exclusions).
    resolved_chapters: list[str]

    # Chapters to exclude from SQL filter (already resolved via alias/fuzzy).
    excluded_chapters: list[str]

    chapter_filter_mode: ChapterFilterMode

    # Counts and filters
    question_count: int
    difficulty: str | None
    difficulty_distribution: dict[str, int] | None
    question_type: str | None
    section_type: str | None
    has_formula: bool | None
    has_diagram: bool | None
    concepts: list[str]
    concept_match_mode: Literal["any", "all"]

    # Debug / display
    chapter_range_description: str
    resolver_warnings: list[str]


# ── Stage 5 output: candidate preview ────────────────────────────────────────

class QuestionPreview(BaseModel):
    """Lightweight question summary for candidate preview."""
    id: str
    question_number: int | None
    chapter: str | None
    difficulty: str | None
    question_type: str | None
    stem_preview: str   # first ~120 chars of raw_text (LaTeX stripped)


class CandidateSet(BaseModel):
    """
    Result of CandidatePreview.
    Tells the caller how many questions are available and shows 5 samples.
    """
    total_available: int
    by_chapter: dict[str, int]
    by_difficulty: dict[str, int]
    by_section_type: dict[str, int]
    by_question_type: dict[str, int]
    sample_questions: list[QuestionPreview]
    can_generate: bool
    shortage: int                   # 0 if can_generate, else deficit
    resolved_blueprint: ResolvedBlueprint


# ── API I/O ───────────────────────────────────────────────────────────────────

class SyllabusQueryRequest(BaseModel):
    prompt: str


class SyllabusQueryResponse(BaseModel):
    """
    Returned by POST /api/papers/syllabus-query.
    If can_generate is True, a draft Paper was immediately created.
    If can_generate is False, paper_id is None and no paper was created.
    """
    paper_id: str | None
    candidates: CandidateSet
    paper: dict | None = None   # PaperResponse-like dict when paper_id is set
