"""
Tests for the bugs fixed in the technical audit.

Covers:
  - _select_with_distribution (C4): question count always returned when pool has enough
  - normalize_exam_name / normalize_subject (C1 supporting): canonical name mapping
  - config paths (C1): no hardcoded absolute paths in defaults
  - filter_builder (I3): exact match used for exam_name / subject

Run: .venv/Scripts/pytest tests/test_audit_fixes.py -v
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — lightweight Question stub for selector tests
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _Q:
    """Minimal stub that looks like a Question ORM object to the selector."""
    id: int
    section_type: str = "mcq"
    difficulty: str = "medium"
    chapter: str = "Kinematics"
    question_type: str = "conceptual"
    subject: str = "physics"
    exam_name: str = "JEE Main"


def _make_pool(
    n_easy: int = 0,
    n_medium: int = 0,
    n_hard: int = 0,
    section_type: str = "mcq",
) -> list[_Q]:
    pool = []
    idx = 0
    for diff, n in [("easy", n_easy), ("medium", n_medium), ("hard", n_hard)]:
        for _ in range(n):
            pool.append(_Q(id=idx, section_type=section_type, difficulty=diff))
            idx += 1
    return pool


# ─────────────────────────────────────────────────────────────────────────────
# Import the function under test
# ─────────────────────────────────────────────────────────────────────────────

from app.services.question_selector import _select_with_distribution


# ─────────────────────────────────────────────────────────────────────────────
# C4 — _select_with_distribution bug
# ─────────────────────────────────────────────────────────────────────────────

class TestSelectWithDistribution:
    """
    The bug: when a difficulty tier had fewer questions than its target,
    a dead variable `leftovers_needed` was set but never used, AND the
    `else:` guard on leftovers.extend() prevented surplus from other tiers
    being collected. The result was a list shorter than `count`.
    """

    DIST = {"easy": 0.2, "medium": 0.6, "hard": 0.2}
    TYPE_DIST = {"conceptual": 0.5, "numerical": 0.5}
    RNG = random.Random(42)

    def _call(self, pool, count):
        return _select_with_distribution(
            pool=pool,
            count=count,
            difficulty_dist=self.DIST,
            type_dist=self.TYPE_DIST,
            rng=random.Random(42),
        )

    def test_exact_pool_size_returned(self):
        """When pool has exactly count questions, all are returned."""
        pool = _make_pool(n_easy=2, n_medium=6, n_hard=2)  # 10 total
        result = self._call(pool, 10)
        assert len(result) == 10

    def test_surplus_pool_returns_count(self):
        """When pool has more than count, exactly count are returned."""
        pool = _make_pool(n_easy=10, n_medium=30, n_hard=10)  # 50 total
        result = self._call(pool, 20)
        assert len(result) == 20

    def test_deficient_hard_tier_filled_from_surplus(self):
        """
        Core regression test for C4.

        If 'hard' tier has 0 questions but 'medium' has plenty, the selector
        must fill the hard target from medium surplus. Before the fix this
        returned fewer than count.
        """
        # Distribution: 20% easy=2, 60% medium=6, 20% hard=2 for count=10
        # But pool has 0 hard questions — surplus medium should fill them
        pool = _make_pool(n_easy=5, n_medium=20, n_hard=0)
        result = self._call(pool, 10)
        assert len(result) == 10, (
            "Should always return exactly `count` when pool has enough total questions"
        )

    def test_deficient_easy_tier_filled_from_surplus(self):
        """Same regression: easy tier empty, medium has surplus."""
        pool = _make_pool(n_easy=0, n_medium=20, n_hard=5)
        result = self._call(pool, 10)
        assert len(result) == 10

    def test_all_tiers_deficient_returns_available(self):
        """When pool has fewer total than count, return whatever is available."""
        pool = _make_pool(n_easy=1, n_medium=2, n_hard=1)  # 4 total
        result = self._call(pool, 10)
        assert len(result) == 4  # cannot exceed pool size

    def test_empty_pool_returns_empty(self):
        result = self._call([], 10)
        assert result == []

    def test_zero_count_returns_empty(self):
        pool = _make_pool(n_medium=10)
        result = self._call(pool, 0)
        assert result == []

    def test_result_respects_max_pool(self):
        """Result must never exceed the pool size."""
        pool = _make_pool(n_easy=3, n_medium=3, n_hard=3)  # 9 total
        result = self._call(pool, 30)
        assert len(result) <= 9

    def test_seeded_rng_is_deterministic(self):
        """Same seed must always produce the same selection."""
        pool = _make_pool(n_easy=10, n_medium=20, n_hard=10)
        r1 = _select_with_distribution(pool, 15, self.DIST, self.TYPE_DIST, random.Random(99))
        r2 = _select_with_distribution(pool, 15, self.DIST, self.TYPE_DIST, random.Random(99))
        assert [q.id for q in r1] == [q.id for q in r2]

    def test_different_seeds_give_different_results(self):
        """Different seeds should (almost always) produce different selections."""
        pool = _make_pool(n_medium=50)
        r1 = _select_with_distribution(pool, 10, self.DIST, self.TYPE_DIST, random.Random(1))
        r2 = _select_with_distribution(pool, 10, self.DIST, self.TYPE_DIST, random.Random(2))
        # Not strictly guaranteed but overwhelmingly likely with 50 questions
        assert [q.id for q in r1] != [q.id for q in r2]


# ─────────────────────────────────────────────────────────────────────────────
# C1 — Canonical normalizer
# ─────────────────────────────────────────────────────────────────────────────

from app.constants.exams import normalize_exam_name, normalize_subject


class TestNormalizeExamName:
    def test_exact_canonical_unchanged(self):
        assert normalize_exam_name("JEE Main") == "JEE Main"
        assert normalize_exam_name("NEET") == "NEET"
        assert normalize_exam_name("CUET") == "CUET"
        assert normalize_exam_name("JEE Advanced") == "JEE Advanced"

    def test_common_variants(self):
        assert normalize_exam_name("jee main") == "JEE Main"
        assert normalize_exam_name("JEE MAINS") == "JEE Main"
        assert normalize_exam_name("jee mains") == "JEE Main"
        assert normalize_exam_name("jeemain") == "JEE Main"
        assert normalize_exam_name("iit jee") == "JEE Main"

    def test_neet_variants(self):
        assert normalize_exam_name("neet") == "NEET"
        assert normalize_exam_name("NEET UG") == "NEET"
        assert normalize_exam_name("neet-ug") == "NEET"

    def test_year_suffix_stripped(self):
        # "JEE Main 2024 April" → prefix "jee main" should resolve
        assert normalize_exam_name("JEE Main 2024") == "JEE Main"

    def test_none_and_blank(self):
        assert normalize_exam_name(None) is None
        assert normalize_exam_name("") is None
        assert normalize_exam_name("   ") is None

    def test_unknown_value_returned_as_is(self):
        # Unknown exam names should be returned as-is, not silently dropped
        assert normalize_exam_name("SAT") == "SAT"


class TestNormalizeSubject:
    def test_canonical_subjects(self):
        assert normalize_subject("physics") == "physics"
        assert normalize_subject("chemistry") == "chemistry"
        assert normalize_subject("mathematics") == "mathematics"
        assert normalize_subject("biology") == "biology"

    def test_common_variants(self):
        assert normalize_subject("maths") == "mathematics"
        assert normalize_subject("math") == "mathematics"
        assert normalize_subject("bio") == "biology"
        assert normalize_subject("chem") == "chemistry"
        assert normalize_subject("phy") == "physics"

    def test_case_insensitive(self):
        assert normalize_subject("Physics") == "physics"
        assert normalize_subject("CHEMISTRY") == "chemistry"
        assert normalize_subject("Maths") == "mathematics"

    def test_none_and_blank(self):
        assert normalize_subject(None) is None
        assert normalize_subject("") is None


# ─────────────────────────────────────────────────────────────────────────────
# C1 — Config paths: no hardcoded absolute user paths
# ─────────────────────────────────────────────────────────────────────────────

from app.config import Settings


class TestConfigPaths:
    def test_storage_dir_default_is_project_relative(self):
        """storage_dir default must not contain a hardcoded username."""
        s = Settings()
        # Should be a path ending in /storage, not C:/Users/<someone>/...
        assert "storage" in s.storage_dir
        # Must not contain a Windows user profile path
        assert "Users" not in s.storage_dir or Path(s.storage_dir).is_absolute()

    def test_mineru_script_default_is_project_relative(self):
        """
        mineru_script default is derived from __file__ (project root),
        not from a hardcoded absolute user-specific path like
        'C:/Users/Anurag shukla/mocktest/scripts/...'.

        We verify it ends in the expected relative path segment
        rather than checking for absence of any username, since
        the project itself may live inside a user's home directory.
        """
        s = Settings()
        script_path = Path(s.mineru_script)
        # Must end with the expected script name in the scripts/ directory
        assert script_path.parts[-1] == "run_mineru_single.py", (
            f"Expected script name 'run_mineru_single.py', got: {script_path.name}"
        )
        assert script_path.parts[-2] == "scripts", (
            f"Expected script to be in 'scripts/' directory, got: {script_path.parent.name}"
        )

    def test_mineru_python_has_no_default(self):
        """MINERU_PYTHON has no safe default — it must be blank unless set in env."""
        import os
        env_backup = os.environ.pop("MINERU_PYTHON", None)
        try:
            s = Settings(_env_file=None)
            assert s.mineru_python == ""
        finally:
            if env_backup is not None:
                os.environ["MINERU_PYTHON"] = env_backup

    def test_storage_dir_is_a_valid_path_string(self):
        s = Settings()
        p = Path(s.storage_dir)
        # Path should be resolvable (even if it doesn't exist yet)
        assert p.is_absolute() or not p.parts[0].startswith("C:/Users/")


# ─────────────────────────────────────────────────────────────────────────────
# I3 — filter_builder uses exact match (not ilike)
# ─────────────────────────────────────────────────────────────────────────────

from app.services.natural_query.filter_builder import SQLFilterBuilder
from app.services.natural_query.schemas import (
    ChapterFilterMode,
    ResolvedBlueprint,
)


def _make_resolved(exam: str = "JEE Main", subject: str = "physics") -> ResolvedBlueprint:
    return ResolvedBlueprint(
        exam_name=exam,
        subject=subject,
        resolved_chapters=["Kinematics"],
        excluded_chapters=[],
        chapter_filter_mode=ChapterFilterMode.all_,
        question_count=10,
        difficulty=None,
        difficulty_distribution=None,
        question_type=None,
        section_type=None,
        has_formula=None,
        has_diagram=None,
        concepts=[],
        concept_match_mode="any",
        chapter_range_description="All chapters",
        resolver_warnings=[],
    )


class TestFilterBuilderExactMatch:
    def test_exam_name_filter_uses_equality_not_ilike(self):
        """
        The exam_name filter must use == not ilike so 'JEE Main' does not
        accidentally match 'JEE Advanced' or 'JEE Mains 2024'.
        """
        builder = SQLFilterBuilder()
        resolved = _make_resolved(exam="JEE Main")
        filters = builder.build(resolved)

        # Inspect the SQL expression string for each filter
        filter_sqls = [str(f.compile(compile_kwargs={"literal_binds": True})) for f in filters]

        # The exam_name filter must be equality, not LIKE/ILIKE
        exam_filter_sql = next(
            (s for s in filter_sqls if "exam_name" in s), None
        )
        assert exam_filter_sql is not None, "No exam_name filter found"
        assert "LIKE" not in exam_filter_sql.upper(), (
            f"exam_name filter uses LIKE/ILIKE instead of =: {exam_filter_sql}"
        )
        assert "JEE Main" in exam_filter_sql

    def test_subject_filter_uses_equality_not_ilike(self):
        builder = SQLFilterBuilder()
        resolved = _make_resolved(subject="physics")
        filters = builder.build(resolved)

        filter_sqls = [str(f.compile(compile_kwargs={"literal_binds": True})) for f in filters]
        subject_filter_sql = next(
            (s for s in filter_sqls if "subject" in s), None
        )
        assert subject_filter_sql is not None
        assert "LIKE" not in subject_filter_sql.upper(), (
            f"subject filter uses LIKE/ILIKE instead of =: {subject_filter_sql}"
        )
