"""
Stage 3 — SyllabusResolver

Converts a ValidatedBlueprint into a ResolvedBlueprint by:
  1. Loading syllabus rows for the exam+subject from the DB.
  2. Resolving each boundary chapter name using:
       Exact match → Alias match → RapidFuzz WRatio ≥ 85 → ChapterNotFoundError
  3. Expanding the range to a concrete, ordered list of chapter names.
  4. Resolving exclude_chapters through the same 4-step pipeline.
  5. Subtracting exclusions from the include list.

This service is the ONLY place that knows about syllabus ordering.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.syllabus import Syllabus
from app.services.natural_query.exceptions import (
    ChapterNotFoundError,
    EmptyRangeError,
    SyllabusNotFoundError,
)
from app.services.natural_query.schemas import (
    ChapterFilterMode,
    ResolvedBlueprint,
    ValidatedBlueprint,
)


class SyllabusResolver:
    """
    Resolves chapter boundary names to ordered chapter lists using the DB.
    Completely deterministic — no LLM involvement.
    """

    def resolve(
        self,
        blueprint: ValidatedBlueprint,
        db: Session,
    ) -> ResolvedBlueprint:
        """
        Main entry point. Returns a ResolvedBlueprint.

        Raises:
            SyllabusNotFoundError  — no syllabus rows for exam+subject
            ChapterNotFoundError   — a chapter name cannot be resolved
            EmptyRangeError        — filter mode produces zero chapters
        """
        warnings: list[str] = []

        # Load all syllabus rows (ordered) for this partition
        rows = (
            db.query(Syllabus)
            .filter(
                Syllabus.exam_name == blueprint.exam_name,
                Syllabus.subject == blueprint.subject,
            )
            .order_by(Syllabus.chapter_order)
            .all()
        )

        if not rows:
            raise SyllabusNotFoundError(blueprint.exam_name, blueprint.subject)

        # ── Resolve include range ─────────────────────────────────────────────
        mode = blueprint.chapter_filter_mode
        resolved_chapters, range_description = self._expand_range(
            mode, blueprint, rows, warnings
        )

        # ── Resolve exclude chapters ──────────────────────────────────────────
        excluded_chapters: list[str] = []
        for exc_name in blueprint.exclude_chapters:
            row, warning = self._resolve_chapter_name(exc_name, rows,
                                                       blueprint.exam_name,
                                                       blueprint.subject)
            excluded_chapters.append(row.chapter_name)
            if warning:
                warnings.append(f"[exclude] {warning}")

        # ── Subtract exclusions ───────────────────────────────────────────────
        excluded_set = set(excluded_chapters)
        resolved_chapters = [c for c in resolved_chapters if c not in excluded_set]

        if not resolved_chapters and mode != ChapterFilterMode.all_:
            raise EmptyRangeError(
                f"Chapter filter mode '{mode}' produced no chapters "
                f"after applying {len(excluded_chapters)} exclusion(s)."
            )

        return ResolvedBlueprint(
            exam_name=blueprint.exam_name,
            subject=blueprint.subject,
            resolved_chapters=resolved_chapters,
            excluded_chapters=excluded_chapters,
            chapter_filter_mode=mode,
            question_count=blueprint.question_count,
            difficulty=blueprint.difficulty,
            difficulty_distribution=blueprint.difficulty_distribution,
            question_type=blueprint.question_type,
            section_type=blueprint.section_type,
            has_formula=blueprint.has_formula,
            has_diagram=blueprint.has_diagram,
            concepts=blueprint.concepts,
            concept_match_mode=blueprint.concept_match_mode,
            chapter_range_description=range_description,
            resolver_warnings=warnings,
        )

    # ── Range expansion logic ─────────────────────────────────────────────────

    def _expand_range(
        self,
        mode: ChapterFilterMode,
        blueprint: ValidatedBlueprint,
        rows: list[Syllabus],
        warnings: list[str],
    ) -> tuple[list[str], str]:
        """Returns (resolved_chapter_names, description_string)."""
        total = len(rows)

        if mode == ChapterFilterMode.all_:
            return (
                [r.chapter_name for r in rows],
                f"All {total} chapters",
            )

        if mode == ChapterFilterMode.exact:
            row, w = self._resolve_chapter_name(
                blueprint.chapter, rows,
                blueprint.exam_name, blueprint.subject
            )
            if w:
                warnings.append(w)
            return (
                [row.chapter_name],
                f"Chapter {row.chapter_order} of {total}: '{row.chapter_name}'",
            )

        if mode == ChapterFilterMode.upto:
            row, w = self._resolve_chapter_name(
                blueprint.chapter_upto, rows,
                blueprint.exam_name, blueprint.subject
            )
            if w:
                warnings.append(w)
            selected = [r.chapter_name for r in rows if r.chapter_order <= row.chapter_order]
            return (
                selected,
                f"Chapters 1–{row.chapter_order} of {total} "
                f"(up to '{row.chapter_name}')",
            )

        if mode == ChapterFilterMode.from_:
            row, w = self._resolve_chapter_name(
                blueprint.chapter_from, rows,
                blueprint.exam_name, blueprint.subject
            )
            if w:
                warnings.append(w)
            selected = [r.chapter_name for r in rows if r.chapter_order >= row.chapter_order]
            return (
                selected,
                f"Chapters {row.chapter_order}–{total} of {total} "
                f"(from '{row.chapter_name}')",
            )

        if mode == ChapterFilterMode.after:
            row, w = self._resolve_chapter_name(
                blueprint.chapter_after, rows,
                blueprint.exam_name, blueprint.subject
            )
            if w:
                warnings.append(w)
            selected = [r.chapter_name for r in rows if r.chapter_order > row.chapter_order]
            if not selected:
                raise EmptyRangeError(
                    f"'after' mode on the last chapter "
                    f"'{row.chapter_name}' (#{row.chapter_order}) "
                    f"produces no chapters."
                )
            first = rows[row.chapter_order]  # row after the boundary
            return (
                selected,
                f"Chapters {row.chapter_order + 1}–{total} of {total} "
                f"(after '{row.chapter_name}', exclusive)",
            )

        if mode == ChapterFilterMode.between:
            from_row, w1 = self._resolve_chapter_name(
                blueprint.chapter_from, rows,
                blueprint.exam_name, blueprint.subject
            )
            to_row, w2 = self._resolve_chapter_name(
                blueprint.chapter_to, rows,
                blueprint.exam_name, blueprint.subject
            )
            if w1:
                warnings.append(w1)
            if w2:
                warnings.append(w2)

            lo = min(from_row.chapter_order, to_row.chapter_order)
            hi = max(from_row.chapter_order, to_row.chapter_order)
            selected = [r.chapter_name for r in rows if lo <= r.chapter_order <= hi]
            return (
                selected,
                f"Chapters {lo}–{hi} of {total} "
                f"('{from_row.chapter_name}' to '{to_row.chapter_name}')",
            )

        # Unreachable — mode is an enum
        raise EmptyRangeError(f"Unknown mode: {mode}")

    # ── 4-step chapter name resolution ───────────────────────────────────────

    def _resolve_chapter_name(
        self,
        llm_name: str,
        rows: list[Syllabus],
        exam_name: str,
        subject: str,
    ) -> tuple[Syllabus, str | None]:
        """
        Resolves llm_name to a Syllabus row using:
          1. Exact match (case-insensitive)
          2. Alias match (JSONB aliases, case-insensitive)
          3. RapidFuzz WRatio ≥ 85 (across chapter names + aliases)
          4. ChapterNotFoundError with suggestions

        Returns (matching_row, warning_message_or_None).
        """
        name_lower = llm_name.strip().lower()

        # Step 1 — Exact match
        for row in rows:
            if row.chapter_name.lower() == name_lower:
                return row, None

        # Step 2 — Alias match
        for row in rows:
            for alias in (row.chapter_aliases or []):
                if alias.lower() == name_lower:
                    return row, (
                        f"Matched '{llm_name}' via alias "
                        f"→ '{row.chapter_name}'"
                    )

        # Step 3 — RapidFuzz WRatio ≥ 85
        try:
            from rapidfuzz import process, fuzz

            # Build search corpus: canonical names + aliases
            corpus: dict[str, Syllabus] = {}
            for row in rows:
                corpus[row.chapter_name] = row
                for alias in (row.chapter_aliases or []):
                    # Don't overwrite if alias same as another canonical name
                    if alias not in corpus:
                        corpus[alias] = row

            result = process.extractOne(
                llm_name,
                list(corpus.keys()),
                scorer=fuzz.WRatio,
            )

            if result is not None:
                matched_name, score, _ = result
                if score >= 85:
                    row = corpus[matched_name]
                    return row, (
                        f"Fuzzy matched '{llm_name}' → '{row.chapter_name}' "
                        f"(score: {score})"
                    )
        except ImportError:
            pass  # rapidfuzz not installed; skip to error

        # Step 4 — Error with suggestions
        raise ChapterNotFoundError(
            chapter_name=llm_name,
            exam_name=exam_name,
            subject=subject,
            available_chapters=[r.chapter_name for r in rows],
        )
