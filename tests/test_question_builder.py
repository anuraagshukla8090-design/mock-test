"""
Tests for InlineAnswerBuilder and utility functions.
Run: .venv/Scripts/pytest tests/ -v
"""
from __future__ import annotations

from pathlib import Path
import pytest

from app.services.question_builder.base import (
    split_options_text,
    extract_answer,
    is_question_start,
    strip_latex_for_search,
    parse_latex_array_options,
)
from app.services.question_builder.inline_answer import InlineAnswerBuilder


def _make_blocks(items: list[tuple[str, str]]) -> list[dict]:
    """Quick helper: list of (type, content) tuples → block dicts."""
    result = []
    for i, (btype, content) in enumerate(items):
        if btype == "text":
            result.append({"type": "text", "text": content, "page_idx": 0})
        elif btype == "equation":
            result.append({"type": "equation", "text": content, "page_idx": 0})
        elif btype == "image":
            result.append({"type": "image", "img_path": content, "page_idx": 0})
    return result


class TestSplitOptions:
    def test_numeric_options(self):
        text = "(1) 5 m/s (2) 10 m/s (3) 15 m/s (4) 20 m/s"
        opts = split_options_text(text)
        assert opts == {"A": "5 m/s", "B": "10 m/s", "C": "15 m/s", "D": "20 m/s"}

    def test_letter_options(self):
        text = "(A) foo (B) bar (C) baz (D) qux"
        opts = split_options_text(text)
        assert set(opts.keys()) == {"A", "B", "C", "D"}

    def test_no_options(self):
        assert split_options_text("random text without options") == {}

    def test_partial_options_returns_empty(self):
        # Only one option marker → not a real option block
        assert split_options_text("(1) single option only") == {}


class TestExtractAnswer:
    def test_numeric_answer(self):
        assert extract_answer("Ans. (4)") == "D"
        assert extract_answer("Ans. (1)") == "A"
        assert extract_answer("Ans. (3)") == "C"

    def test_letter_answer(self):
        assert extract_answer("Ans. (B)") == "B"
        assert extract_answer("Ans. (d)") == "D"

    def test_no_answer(self):
        assert extract_answer("Some random text") is None

    def test_answer_in_longer_text(self):
        assert extract_answer("This is Q51. Ans. (2) confirmed.") == "B"


class TestIsQuestionStart:
    def test_detects_question_start(self):
        block = {"type": "text", "text": "51. A block slides on a frictionless..."}
        is_q, num = is_question_start(block)
        assert is_q is True
        assert num == 51

    def test_ignores_non_text(self):
        block = {"type": "image", "img_path": "a.jpg"}
        is_q, num = is_question_start(block)
        assert is_q is False
        assert num is None

    def test_ignores_option_text(self):
        block = {"type": "text", "text": "(1) Option A text"}
        is_q, num = is_question_start(block)
        assert is_q is False


class TestStripLatexForSearch:
    def test_strips_display_math(self):
        result = strip_latex_for_search("The value of $$E = mc^2$$ is")
        assert "$$" not in result
        assert "The value of" in result

    def test_strips_inline_math(self):
        result = strip_latex_for_search("Given $v = u + at$, find v.")
        assert "$" not in result
        assert "find v." in result


class TestInlineAnswerBuilderCanHandle:
    def test_detects_inline_layout(self):
        # 3 questions each with answer within 5 blocks
        blocks = _make_blocks([
            ("text", "51. What is the SI unit of force?"),
            ("text", "(1) Joule (2) Newton (3) Pascal (4) Watt"),
            ("text", "Ans. (2)"),
            ("text", "52. What is the speed of light?"),
            ("text", "(1) 3e6 m/s (2) 3e8 m/s (3) 3e10 m/s (4) 3e4 m/s"),
            ("text", "Ans. (2)"),
        ])
        assert InlineAnswerBuilder.can_handle(blocks) is True

    def test_rejects_no_answers(self):
        blocks = _make_blocks([
            ("text", "51. What is force?"),
            ("text", "(1) A (2) B (3) C (4) D"),
            ("text", "52. Define Newton's law."),
            ("text", "(1) P (2) Q (3) R (4) S"),
        ])
        assert InlineAnswerBuilder.can_handle(blocks) is False


class TestInlineAnswerBuilderBuild:
    def test_builds_questions(self, tmp_path: Path):
        blocks = _make_blocks([
            ("text", "51. A ball is thrown vertically upward with initial velocity 20 m/s."),
            ("text", "(1) 10 m (2) 20 m (3) 30 m (4) 40 m"),
            ("text", "Ans. (2)"),
            ("text", "52. What is Newton's second law?"),
            ("text", "(1) F=ma (2) F=mv (3) F=ma2 (4) F=m/a"),
            ("text", "Ans. (1)"),
        ])
        builder = InlineAnswerBuilder(blocks, tmp_path)
        questions = builder.build()
        assert len(questions) == 2
        assert questions[0].question_number == 51
        assert questions[0].answer == "B"
        assert questions[1].question_number == 52
        assert questions[1].answer == "A"
        # Options extracted
        assert "A" in questions[0].options
        assert "D" in questions[0].options

    def test_skips_question_without_answer(self, tmp_path: Path):
        blocks = _make_blocks([
            ("text", "51. Question with no answer below."),
            ("text", "(1) A (2) B (3) C (4) D"),
            # No Ans. block
            ("text", "52. Another question."),
            ("text", "(1) A (2) B (3) C (4) D"),
            ("text", "Ans. (3)"),
        ])
        builder = InlineAnswerBuilder(blocks, tmp_path)
        questions = builder.build()
        # Only Q52 should make it through (Q51 has no answer)
        assert len(questions) == 1
        assert questions[0].question_number == 52

    def test_sorted_by_question_number(self, tmp_path: Path):
        # Deliberately out of order (simulating MinerU reading-order bug)
        blocks = _make_blocks([
            ("text", "53. Question 53"),
            ("text", "(1) A (2) B (3) C (4) D"),
            ("text", "Ans. (1)"),
            ("text", "51. Question 51"),
            ("text", "(1) A (2) B (3) C (4) D"),
            ("text", "Ans. (2)"),
        ])
        builder = InlineAnswerBuilder(blocks, tmp_path)
        questions = builder.build()
        assert questions[0].question_number == 51
        assert questions[1].question_number == 53
