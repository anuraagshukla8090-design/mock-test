"""
Tests for the post-processor cleaning pipeline.
Run: .venv/Scripts/pytest tests/ -v
"""
from __future__ import annotations

import pytest
from app.services.post_processor import (
    clean_content_blocks,
    _remove_empty_blocks,
    _remove_ad_pages,
    _remove_garbled_ocr,
    _deduplicate_consecutive_answers,
)


def _text(t: str, page: int = 0, level: bool = False) -> dict:
    b = {"type": "text", "text": t, "page_idx": page}
    if level:
        b["text_level"] = 1
    return b


class TestRemoveEmptyBlocks:
    def test_removes_whitespace_only(self):
        blocks = [_text("  "), _text("real content"), _text("\n\t")]
        result = _remove_empty_blocks(blocks)
        assert len(result) == 1
        assert result[0]["text"] == "real content"

    def test_keeps_non_text_blocks(self):
        blocks = [{"type": "image", "img_path": "a.jpg"}, _text("")]
        result = _remove_empty_blocks(blocks)
        assert len(result) == 1
        assert result[0]["type"] == "image"


class TestRemoveAdPages:
    def test_removes_entire_page_with_ad_keyword(self):
        blocks = [
            _text("51. What is Newton's first law?", page=0),
            _text("JOIN LEADER COURSE", page=1),          # ad keyword
            _text("Get 50% off today!", page=1),           # same ad page
            _text("52. Explain inertia.", page=2),
        ]
        result = _remove_ad_pages(blocks)
        # Only page 0 and page 2 should remain
        assert all(b["page_idx"] in (0, 2) for b in result)
        assert len(result) == 2

    def test_no_ads_unchanged(self):
        blocks = [_text("Q1. Physics question", page=0)]
        result = _remove_ad_pages(blocks)
        assert len(result) == 1


class TestRemoveGarbledOCR:
    def test_removes_high_nonascii(self):
        # >40% non-ASCII: 5 Chinese chars out of 9 visible chars ≈ 55%
        blocks = [_text("身广无身广无身广Z"), _text("Normal english text")]
        result = _remove_garbled_ocr(blocks)
        assert len(result) == 1
        assert "Normal" in result[0]["text"]

    def test_keeps_latex_heavy_blocks(self):
        # LaTeX blocks can be dollar-sign heavy — should not be filtered
        latex = r"$$\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$"
        blocks = [_text(latex)]
        result = _remove_garbled_ocr(blocks)
        assert len(result) == 1


class TestDeduplicateAnswers:
    def test_removes_first_of_consecutive_answers(self):
        blocks = [
            _text("51. Question text"),
            _text("Ans. (1)"),   # duplicate
            _text("Ans. (1)"),   # keep this one
            _text("52. Next question"),
        ]
        result = _deduplicate_consecutive_answers(blocks)
        ans_blocks = [b for b in result if "Ans." in b["text"]]
        assert len(ans_blocks) == 1

    def test_single_answer_unchanged(self):
        blocks = [_text("Ans. (2)")]
        result = _deduplicate_consecutive_answers(blocks)
        assert len(result) == 1


class TestFullPipeline:
    def test_pipeline_end_to_end(self):
        blocks = [
            _text("51. A block on a frictionless surface...", page=0),
            _text("(1) 5 N (2) 10 N (3) 15 N (4) 20 N", page=0),
            _text("Ans. (2)", page=0),
            _text("JOIN LEADER COURSE", page=1),
            _text("Big discount!", page=1),
            _text("52. Next question", page=2),
            _text("(1) A (2) B (3) C (4) D", page=2),
            _text("Ans. (3)", page=2),
            _text("Ans. (3)", page=2),   # duplicate
        ]
        result = clean_content_blocks(blocks)
        # Ad page 1 gone, no empty, no duplicate answers
        pages = {b.get("page_idx") for b in result}
        assert 1 not in pages
        ans_blocks = [b for b in result if "Ans." in b.get("text", "")]
        assert len(ans_blocks) == 2   # one per question
