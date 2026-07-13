"""
tests/test_full_paper_builder.py
Tests for the FullPaperBuilder v2 pipeline.

Run with:  .venv\\Scripts\\python -m pytest tests/test_full_paper_builder.py -v
"""
from __future__ import annotations

import pytest
from pathlib import Path

from app.services.question_builder.full_paper import (
    FullPaperBuilder,
    _is_noise,
    _is_answer_key_header,
    _parse_question_number,
    _strip_q_prefix,
    _collect_inline_options,
    _extract_stem_fragment,
    _parse_merged_marker_block,
    _parse_embedded_array,
    _parse_equation_block_options,
    _parse_answer_key,
    _find_answer_key_boundary,
    _group_into_questions,
    _normalize_text_block,
    _merge_answers,
    _filter_blocks,
    _segment_blocks,
    _merge_option_candidates,
    _validate_questions,
)
from app.services.question_builder.base import Question


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def txt(text: str, page: int = 0) -> dict:
    return {"type": "text", "text": text, "page_idx": page}

def img(filename: str = "test.jpg", page: int = 0) -> dict:
    return {"type": "image", "img_path": f"/fake/{filename}", "text": "", "page_idx": page}

def eq(text: str, page: int = 0) -> dict:
    return {"type": "equation", "text": text, "page_idx": page}


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Noise filter
# ─────────────────────────────────────────────────────────────────────────────

class TestIsNoise:
    def test_empty_block(self):
        assert _is_noise(txt("")) is True

    def test_too_short(self):
        assert _is_noise(txt("hi")) is True

    def test_page_number_only(self):
        assert _is_noise(txt("12")) is True
        assert _is_noise(txt("1")) is True

    def test_watermark_mathongo(self):
        assert _is_noise(txt("MathonGo")) is True
        assert _is_noise(txt("mathongo")) is True

    def test_page_header_jee(self):
        assert _is_noise(txt("2025 (22 Jan Shift 1) JEE Main 2025 January")) is True

    def test_page_header_previous(self):
        assert _is_noise(txt("JEE Main Previous Year Paper")) is True

    def test_real_question_not_noise(self):
        assert _is_noise(txt("Q1. Let a_1, a_2, a_3 be a G.P.")) is False

    def test_normal_text_not_noise(self):
        assert _is_noise(txt("(1) 3 + e  (2) 3 - e  (3) e + 1  (4) e - 1")) is False

    def test_continuation_not_noise(self):
        assert _is_noise(txt("Choose the correct answer from the options given below:")) is False


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Answer-key boundary detection
# ─────────────────────────────────────────────────────────────────────────────

class TestAnswerKeyBoundary:
    def test_finds_answer_keys_header(self):
        blocks = [
            txt("Q1. What is 1+1?"),
            txt("(1) 1  (2) 2  (3) 3  (4) 4"),
            txt("ANSWER KEYS"),
            txt("1.(2) 2.(3)"),
        ]
        idx = _find_answer_key_boundary(blocks)
        assert idx == 2  # index of "ANSWER KEYS" block

    def test_finds_answer_key_variant(self):
        blocks = [
            txt("Q1. stem"),
            txt("(1) a  (2) b"),
            txt("ANSWER KEY  2025"),
            txt("1.(1)"),
        ]
        idx = _find_answer_key_boundary(blocks)
        assert idx == 2

    def test_density_fallback(self):
        # No header but dense answer entries in tail
        blocks = [txt("Q1. stem")] * 10 + [txt("1.(2) 2.(3) 3.(4) 4.(1)")]
        idx = _find_answer_key_boundary(blocks)
        assert idx == 10  # the dense entry block

    def test_no_key_returns_len(self):
        blocks = [txt("Q1. stem"), txt("(1) a  (2) b")]
        idx = _find_answer_key_boundary(blocks)
        assert idx == len(blocks)

    def test_is_answer_key_header_exact(self):
        assert _is_answer_key_header("ANSWER KEYS") is True
        assert _is_answer_key_header("answer key") is True
        assert _is_answer_key_header("ANSWER KEYS  2025 (22 Jan Shift 1)") is True

    def test_is_answer_key_header_false(self):
        assert _is_answer_key_header("Q1. stem text") is False
        assert _is_answer_key_header("(1) option A") is False


class TestFilterAndSegmentStages:
    def test_filter_retains_source_provenance(self):
        result = _filter_blocks([txt("MathonGo", page=3), txt("Q1. stem", page=3)])
        assert [item.source_index for item in result.blocks] == [1]
        assert result.blocks[0].block["text"] == "Q1. stem"
        assert result.warnings

    def test_segment_uses_filtered_order_and_reports_original_boundary(self):
        filtered = _filter_blocks([
            txt("MathonGo"),
            txt("Q1. stem"),
            txt("ANSWER KEYS"),
            txt("1.(2)"),
        ])
        segment = _segment_blocks(filtered.blocks)
        assert len(segment.body) == 1
        assert len(segment.answer_key) == 2
        assert segment.boundary_source_index == 2


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: Question number parsing & grouping
# ─────────────────────────────────────────────────────────────────────────────

class TestParseQuestionNumber:
    def test_q_prefix(self):
        assert _parse_question_number("Q1. stem") == 1
        assert _parse_question_number("Q 12. stem") == 12
        assert _parse_question_number("Q.1. stem") == 1

    def test_plain_number(self):
        assert _parse_question_number("26. Some question text") == 26
        assert _parse_question_number("1. text") == 1

    def test_no_match(self):
        assert _parse_question_number("(1) option text") is None
        assert _parse_question_number("Choose the correct answer") is None
        assert _parse_question_number("SECTION-A") is None

    def test_q_prefix_no_text_required(self):
        # Q-prefix questions sometimes have just "Q57." with nothing after
        assert _parse_question_number("Q57.") == 57
        assert _parse_question_number("Q57. ") == 57


class TestGroupIntoQuestions:
    def test_basic_grouping(self):
        blocks = [
            txt("Q1. First question stem"),
            txt("(1) a  (2) b  (3) c  (4) d"),
            txt("Q2. Second question stem"),
            txt("(1) x  (2) y  (3) z  (4) w"),
        ]
        groups = _group_into_questions(blocks)
        assert len(groups) == 2
        assert groups[0].number == 1
        assert groups[1].number == 2
        assert len(groups[0].blocks) == 2
        assert len(groups[1].blocks) == 2

    def test_image_forwarded_to_current(self):
        blocks = [
            txt("Q1. stem"),
            img("diagram.jpg"),
            txt("(1) a  (2) b"),
        ]
        groups = _group_into_questions(blocks)
        assert len(groups) == 1
        block_types = [b["type"] for b in groups[0].blocks]
        assert "image" in block_types

    def test_noise_discarded(self):
        blocks = [
            txt("Q1. stem"),
            txt("MathonGo"),           # noise
            txt("2025 (22 Jan Shift 1) JEE Main 2025 January"),  # noise
            txt("(1) a  (2) b"),
        ]
        groups = _group_into_questions(blocks)
        assert len(groups) == 1
        # Only 2 real blocks should remain: Q1 start + options
        text_blocks = [b for b in groups[0].blocks if b["type"] == "text"]
        assert len(text_blocks) == 2

    def test_q_prefix_only_block(self):
        # "Q57." alone — stem continues in next block
        blocks = [
            txt("Q57."),
            txt("This is the actual question stem."),
            txt("(1) a  (2) b  (3) c  (4) d"),
        ]
        groups = _group_into_questions(blocks)
        assert len(groups) == 1
        assert groups[0].number == 57
        assert len(groups[0].blocks) == 3

    def test_preamble_discarded(self):
        # Text before first question is ignored
        blocks = [
            txt("JEE Main 2025 Full Paper"),  # noise — filtered
            txt("Instructions: Read carefully"),  # preamble — no current question yet
            txt("Q1. stem"),
        ]
        groups = _group_into_questions(blocks)
        assert len(groups) == 1

    def test_duplicate_start_does_not_merge_two_source_groups(self):
        groups = _group_into_questions([
            txt("Q1. first OCR reading"),
            txt("Q1. second OCR reading"),
            txt("(1) a (2) b (3) c (4) d"),
        ])
        assert len(groups) == 2
        assert "first OCR reading" in groups[0].blocks[0]["text"]
        assert "second OCR reading" in groups[1].blocks[0]["text"]
        assert any("duplicate" in warning for warning in groups[1].warnings)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4: Option collection helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestCollectInlineOptions:
    def test_all_four_inline(self):
        opts = _collect_inline_options("(1) alpha  (2) beta  (3) gamma  (4) delta")
        assert opts == {"A": "alpha", "B": "beta", "C": "gamma", "D": "delta"}

    def test_two_options_in_block(self):
        opts = _collect_inline_options("(1) $3\\pi + 8$  (3) $3\\pi - 8$")
        assert "A" in opts
        assert "C" in opts
        assert "B" not in opts

    def test_no_options(self):
        opts = _collect_inline_options("This is a pure stem block with no markers.")
        assert opts == {}

    def test_conflicting_option_does_not_overwrite_first_reading(self):
        options = {"A": "first reading"}
        warnings: list[str] = []
        _merge_option_candidates(
            options, {"A": "different OCR reading"}, warnings, 1, "text block"
        )
        assert options == {"A": "first reading"}
        assert any("conflicting option A" in warning for warning in warnings)

    def test_letter_markers(self):
        opts = _collect_inline_options("(A) first  (B) second  (C) third  (D) fourth")
        assert opts == {"A": "first", "B": "second", "C": "third", "D": "fourth"}

    def test_with_latex(self):
        opts = _collect_inline_options(
            "(1) $\\Delta U < 0$ (2) $\\Delta U > 0$ (3) $q = 0$ (4) $w > 0$"
        )
        assert len(opts) == 4


class TestExtractStemFragment:
    def test_pure_stem(self):
        assert _extract_stem_fragment("This is the question stem.") == "This is the question stem."

    def test_stem_before_options(self):
        result = _extract_stem_fragment("The answer is (1) true  (2) false")
        assert result == "The answer is"

    def test_options_only_returns_empty(self):
        # Block starts immediately with option marker — no stem prefix
        result = _extract_stem_fragment("(1) option A  (2) option B")
        assert result == ""

    def test_full_question_block(self):
        text = "Q1. The area of the region inside the circle is (1) $\\pi$ (2) $2\\pi$ (3) $3\\pi$ (4) $4\\pi$"
        result = _extract_stem_fragment(text)
        # Should return everything before "(1)"
        assert "(1)" not in result
        assert "The area" in result


class TestParseMergedMarkerBlock:
    def test_merged_13_with_dollars(self):
        result = _parse_merged_marker_block("(13) $x^2 + 1$  $x^2 - 1$")
        assert result is not None
        assert result.get("A") == "$x^2 + 1$"
        assert result.get("C") == "$x^2 - 1$"

    def test_merged_24_with_dollars(self):
        result = _parse_merged_marker_block("(24) $\\frac{a}{2}$  $\\frac{a}{4}$")
        assert result is not None
        assert result.get("B") == "$\\frac{a}{2}$"
        assert result.get("D") == "$\\frac{a}{4}$"

    def test_not_merged_marker(self):
        # Normal option block — should return None
        result = _parse_merged_marker_block("(1) first option")
        assert result is None

    def test_merged_marker_no_content(self):
        # Is a marker but can't split — returns {}
        result = _parse_merged_marker_block("(13) unparseable content without boundaries")
        assert result == {} or result is not None  # {} = could not split, not None


class TestParseEquationBlockOptions:
    def test_array_with_1_3(self):
        # Q13 pattern: {{ 1) content }} \\ {{ 3) content }}
        eq_text = "$$\n\\begin{array} { c } { { 1 ) 3 \\pi + 8 } } \\\\ { { 3 ) 3 \\pi - 8 } } \\end{array}\n$$"
        result = _parse_equation_block_options(eq_text)
        assert "A" in result
        assert "C" in result

    def test_array_with_left_right(self):
        # Q2 pattern: {{ \left(2\right) content }} \\ {{ \left(4\right) content }}
        eq_text = "$$\n\\begin{array} { l } { { \\left( 2 \\right) 3 + e } } \\\\ { { \\left( 4 \\right) \\frac 3 2 + e } } \\end{array}\n$$"
        result = _parse_equation_block_options(eq_text)
        assert "B" in result
        assert "D" in result

    def test_plain_formula_returns_empty(self):
        # A formula block that is NOT an option array
        eq_text = "$$x^2 + y^2 = r^2$$"
        result = _parse_equation_block_options(eq_text)
        assert result == {}

    def test_single_match_returns_empty(self):
        # Only 1 option found — likely false positive
        eq_text = "$$\\begin{array}{c}{{ 1) only one }}\\end{array}$$"
        result = _parse_equation_block_options(eq_text)
        assert result == {}


class TestParseEmbeddedArray:
    def test_q11_pattern(self):
        # Q11: text block starting with "( $\begin{array}..."
        text = "( $\\begin{array} { c } { { 2 ) 2 2 \\pi ^ { 2 } } } \\\\ { { 4 ) 1 8 \\pi ^ { 2 } } } \\end{array}$ "
        result = _parse_embedded_array(text)
        assert "B" in result
        assert "D" in result

    def test_non_embedded_returns_empty(self):
        assert _parse_embedded_array("(1) some option") == {}
        assert _parse_embedded_array("stem text here") == {}


# ─────────────────────────────────────────────────────────────────────────────
# Stage 5: Answer key parsing
# ─────────────────────────────────────────────────────────────────────────────

class TestParseAnswerKey:
    def test_basic_entries(self):
        blocks = [txt("1.(2) 2.(3) 3.(1) 4.(4)")]
        result = _parse_answer_key(blocks)
        assert result == {1: "2", 2: "3", 3: "1", 4: "4"}

    def test_integer_answers(self):
        blocks = [txt("21.(34) 22.(2035) 23.(7)")]
        result = _parse_answer_key(blocks)
        assert result[21] == "34"
        assert result[22] == "2035"
        assert result[23] == "7"

    def test_spaced_entries_match_mathongo_answer_page(self):
        result = _parse_answer_key([txt("1. (4)   2. (3)   21. (34)   22. (2035)")])
        assert result == {1: "4", 2: "3", 21: "34", 22: "2035"}

    def test_multi_block_key(self):
        blocks = [
            txt("1.(2) 2.(1) 3.(4)"),
            txt("4.(3) 5.(2) 6.(1)"),
        ]
        result = _parse_answer_key(blocks)
        assert len(result) == 6
        assert result[4] == "3"

    def test_first_occurrence_wins(self):
        blocks = [
            txt("1.(2) 2.(3)"),
            txt("1.(4)"),  # duplicate — should not overwrite
        ]
        result = _parse_answer_key(blocks)
        assert result[1] == "2"

    def test_image_blocks_skipped(self):
        blocks = [
            img("chart.jpg"),
            txt("5.(3) 6.(1)"),
        ]
        result = _parse_answer_key(blocks)
        assert len(result) == 2


class TestValidation:
    def test_orphan_answer_key_entry_is_returned_as_stage_warning(self):
        question = Question(1, "stem", {"A": "a", "B": "b", "C": "c", "D": "d"}, "A")
        warnings = _validate_questions([question], {1: "1", 2: "2"})
        assert warnings == ["answer key contains Q2 with no built question"]

    def test_invalid_mcq_answer_is_preserved_and_warned(self):
        question = Question(1, "stem", {"A": "a", "B": "b", "C": "c", "D": "d"}, "")
        _merge_answers([question], {1: "unreadable"})
        assert question.answer == "UNREADABLE"
        assert any("unrecognised MCQ answer" in warning for warning in question.warnings)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4: Strip prefix
# ─────────────────────────────────────────────────────────────────────────────

class TestStripQPrefix:
    def test_q_prefix(self):
        assert _strip_q_prefix("Q1. stem text here") == "stem text here"
        assert _strip_q_prefix("Q 12. stem") == "stem"

    def test_plain_prefix(self):
        assert _strip_q_prefix("26. stem text here") == "stem text here"

    def test_no_prefix(self):
        # No prefix — returned unchanged (minus whitespace)
        assert _strip_q_prefix("stem text here") == "stem text here"


# ─────────────────────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeTextBlock:
    def test_strips_watermark(self):
        result = _normalize_text_block("Some content mathonGo extra")
        assert "mathon" not in result.lower()
        assert "Some content" in result

    def test_collapses_spaces(self):
        result = _normalize_text_block("word1   word2    word3")
        assert "  " not in result

    def test_strips_whitespace(self):
        result = _normalize_text_block("  hello world  ")
        assert result == "hello world"


# ─────────────────────────────────────────────────────────────────────────────
# Integration: full pipeline end-to-end
# ─────────────────────────────────────────────────────────────────────────────

class TestFullPipelineIntegration:
    """End-to-end tests using minimal synthetic block sequences."""

    def _build(self, blocks: list[dict]) -> list[Question]:
        return FullPaperBuilder(blocks, Path("/nonexistent")).build()

    def test_single_mcq_all_inline(self):
        blocks = [
            txt("Q1. What is 2+2?"),
            txt("(1) 3  (2) 4  (3) 5  (4) 6"),
            txt("ANSWER KEYS"),
            txt("1.(2)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        q = qs[0]
        assert q.question_number == 1
        assert q.section_type == "mcq"
        assert len(q.options) == 4
        assert q.answer == "B"

    def test_integer_question(self):
        blocks = [
            txt("Q4. Find the value of x if x^2 = 16."),
            txt("ANSWER KEYS"),
            txt("4.(4)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        q = qs[0]
        assert q.section_type == "integer"
        assert q.options == {}
        assert q.answer == "4"

    def test_options_split_across_blocks(self):
        # Pattern C: each option in its own block
        blocks = [
            txt("Q5. Which is correct?"),
            txt("(1) option A"),
            txt("(2) option B"),
            txt("(3) option C"),
            txt("(4) option D"),
            txt("ANSWER KEYS"),
            txt("5.(3)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        q = qs[0]
        assert q.section_type == "mcq"
        assert len(q.options) == 4
        assert q.answer == "C"

    def test_image_associated_correctly(self):
        blocks = [
            txt("Q6. Refer to the diagram below."),
            img("fig1.jpg"),
            txt("(1) alpha  (2) beta  (3) gamma  (4) delta"),
            txt("ANSWER KEYS"),
            txt("6.(1)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        assert qs[0].question_number == 6

    def test_merged_marker_options(self):
        # Pattern F: (13) and (24) merged markers
        blocks = [
            txt("Q7. Select correct."),
            txt("(13) $x^2 + 1$  $x^2 - 1$"),
            txt("(24) $y^2 + 1$  $y^2 - 1$"),
            txt("ANSWER KEYS"),
            txt("7.(2)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        q = qs[0]
        assert q.section_type == "mcq"
        assert "A" in q.options
        assert "C" in q.options
        assert "B" in q.options
        assert "D" in q.options

    def test_stem_only_block_not_classified_as_options(self):
        # Continuation stem should not become options
        blocks = [
            txt("Q8. The sum of the maximum and the"),
            txt("minimum values of the function is"),
            txt("(1) 24  (2) 22  (3) 31  (4) 18"),
            txt("ANSWER KEYS"),
            txt("8.(1)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        q = qs[0]
        assert "minimum values" in q.stem_md
        assert q.section_type == "mcq"

    def test_multiple_questions_answers_correct(self):
        blocks = [
            txt("Q1. First question."),
            txt("(1) a  (2) b  (3) c  (4) d"),
            txt("Q2. Second question."),
            txt("(1) w  (2) x  (3) y  (4) z"),
            txt("Q3. Integer question with no options."),
            txt("ANSWER KEYS"),
            txt("1.(3) 2.(1) 3.(42)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 3

        q1 = next(q for q in qs if q.question_number == 1)
        q2 = next(q for q in qs if q.question_number == 2)
        q3 = next(q for q in qs if q.question_number == 3)

        assert q1.answer == "C"
        assert q2.answer == "A"
        assert q3.section_type == "integer"
        assert q3.answer == "42"

    def test_duplicate_question_number_is_not_returned_twice(self):
        blocks = [
            txt("Q1. First reading."),
            txt("Q1. Conflicting reading."),
            txt("(1) a (2) b (3) c (4) d"),
            txt("ANSWER KEYS"),
            txt("1.(1)"),
        ]
        builder = FullPaperBuilder(blocks, Path("/nonexistent"))
        questions = builder.build()
        assert [question.question_number for question in questions] == [1]
        assert builder.report["duplicate_question_numbers"] == [1]
        assert any("duplicate" in warning for warning in builder.stage_warnings)

    def test_noise_blocks_between_questions(self):
        blocks = [
            txt("Q1. Stem of Q1."),
            txt("(1) a  (2) b  (3) c  (4) d"),
            txt("MathonGo"),                   # noise
            txt("2025 (22 Jan Shift 1) JEE Main 2025 January"),  # noise
            txt("Q2. Stem of Q2."),
            txt("(1) p  (2) q  (3) r  (4) s"),
            txt("ANSWER KEYS"),
            txt("1.(1) 2.(4)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 2
        assert qs[0].answer == "A"
        assert qs[1].answer == "D"

    def test_q_stem_only_block_no_key(self):
        # "Q57." alone on a block — should still create a question
        blocks = [
            txt("Q57."),
            txt("Choose the correct answer from the options given below:"),
            txt("(1) X only  (2) Y only  (3) Both X and Y  (4) Neither"),
            txt("ANSWER KEYS"),
            txt("57.(3)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        q = qs[0]
        assert q.question_number == 57
        assert q.section_type == "mcq"
        assert len(q.options) == 4
        assert q.answer == "C"

    def test_no_answer_key_warning(self):
        blocks = [
            txt("Q1. Stem."),
            txt("(1) a  (2) b  (3) c  (4) d"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        # Answer should be empty and warning emitted
        assert qs[0].answer == ""
        assert any("answer not found" in w for w in qs[0].warnings)

    def test_image_only_answer_page_is_explicitly_reported(self):
        blocks = [
            txt("Q1. Stem."),
            txt("(1) a (2) b (3) c (4) d"),
            img("answer-key-page.jpg", page=14),
        ]
        builder = FullPaperBuilder(blocks, Path("/nonexistent"))
        questions = builder.build()
        assert any("emitted as an image block" in warning for warning in builder.stage_warnings)
        assert any("emitted as an image block" in warning for warning in questions[0].warnings)

    def test_partial_options_warning(self):
        blocks = [
            txt("Q1. Stem."),
            txt("(1) only option A present"),
            txt("ANSWER KEYS"),
            txt("1.(1)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        assert any("options_missing" in w for w in qs[0].warnings)

    def test_answer_not_reclassified_from_key(self):
        # Q with NO options in body — must remain 'integer' even if answer key says "2"
        blocks = [
            txt("Q1. Find the integer value."),
            txt("ANSWER KEYS"),
            txt("1.(2)"),
        ]
        qs = self._build(blocks)
        assert len(qs) == 1
        assert qs[0].section_type == "integer"
        assert qs[0].options == {}
