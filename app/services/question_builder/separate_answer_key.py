from __future__ import annotations

import re
import logging
from pathlib import Path

from app.services.question_builder.abstract_builder import AbstractBuilder
from app.services.question_builder.base import Question
from app.services.question_builder.inline_answer import InlineAnswerBuilder

logger = logging.getLogger(__name__)

# ── Answer normalization: option number → letter ──────────────────────────────
_MCQ_ANSWER_MAP: dict[str, str] = {
    "1": "A", "2": "B", "3": "C", "4": "D",
}

# Regex: matches "51.(2)" or "51 . ( 2 )" — handles whitespace variation
_ANSWER_KEY_ENTRY_RE = re.compile(
    r"(\d{1,3})\s*[.)]\s*[(\[]?\s*([^)\]\s]+)\s*[)\]]?",
)

# Headers that mark the start of the answer key section
_ANSWER_KEY_HEADERS = frozenset([
    "answer key", "answer keys", "ans key", "ans. key",
    "answers", "answer sheet", "solution key",
])


class SeparateAnswerKeyBuilder(AbstractBuilder):
    """
    Handles PDFs where questions and options appear on early pages,
    and an 'ANSWER KEYS' section appears at the end.

    Algorithm:
      Step 1 — Extract all questions (with options, images, equations).
               answer = None on every question initially.
      Step 2 — Scan the END of the block list for the answer key section.
               Parse entries like '51.(2)' into {51: "2"}.
      Step 3 — Map parsed answers back to questions by question_number.
               MCQ answers are normalized: "1"->"A", "2"->"B", etc.
               Integer answers are stored as-is.
      Step 4 — Return list[Question]; the rest of the pipeline is unchanged.
    """

    def build(self) -> list[Question]:
        # Step 1: Use InlineAnswerBuilder's extraction logic for Q+Options,
        # but we need to strip answers since they don't exist inline here.
        # We reuse InlineAnswerBuilder then clear the answers it may have found.
        inner = _NoAnswerExtractor(self.blocks, self.images_dir)
        questions = inner.build()

        if not questions:
            logger.warning("SeparateAnswerKeyBuilder: no questions extracted")
            return []

        # Step 2: Parse the answer key section from the end of the document
        answer_map = _parse_answer_key_section(self.blocks)
        if not answer_map:
            logger.warning(
                "SeparateAnswerKeyBuilder: no answer key section found — "
                "all questions will have answer=None"
            )

        # Step 3: Map answers to questions
        matched = 0
        for q in questions:
            num = q.question_number
            if num is None:
                continue
            raw = answer_map.get(num)
            if raw is None:
                logger.warning(
                    "SeparateAnswerKeyBuilder: Q%s has no answer in key", num
                )
                q.answer = None
                continue

            # Normalize based on section type
            if q.section_type == "mcq":
                q.answer = _MCQ_ANSWER_MAP.get(raw, raw)  # e.g. "2" -> "B"
            else:
                q.answer = raw  # integer-type: store as-is e.g. "34", "2035"
            matched += 1

        logger.info(
            "SeparateAnswerKeyBuilder: %d questions, %d answers matched",
            len(questions), matched,
        )

        questions.sort(key=lambda q: q.question_number or 0)
        return questions

    @classmethod
    def can_handle(cls, blocks: list[dict]) -> bool:
        """
        Returns True if the document has an answer key section near the end
        but no inline 'Ans.' markers next to questions.
        """
        text_blocks = [b for b in blocks if b.get("type") == "text"]
        if not text_blocks:
            return False

        # Check last 30% of text blocks for an answer key header
        tail = text_blocks[int(len(text_blocks) * 0.7):]
        has_key_section = any(
            b.get("text", "").strip().lower() in _ANSWER_KEY_HEADERS
            or any(h in b.get("text", "").lower() for h in _ANSWER_KEY_HEADERS)
            for b in tail
        )
        if not has_key_section:
            return False

        # Confirm there are no inline 'Ans.' markers in the question section
        head = text_blocks[:int(len(text_blocks) * 0.7)]
        inline_ans = sum(
            1 for b in head
            if re.search(r"\bAns\b\.?\s*[\(\[]", b.get("text", ""))
        )
        return inline_ans < 3  # fewer than 3 inline answers = separate key layout


class _NoAnswerExtractor(InlineAnswerBuilder):
    """
    Thin subclass of InlineAnswerBuilder that clears all answers after
    extraction, since in this layout answers come from the key, not inline.
    """

    def build(self) -> list[Question]:
        questions = super().build()
        for q in questions:
            q.answer = None  # will be filled in by SeparateAnswerKeyBuilder
        return questions


def _parse_answer_key_section(blocks: list[dict]) -> dict[int, str]:
    """
    Scans content blocks from the END backwards to find the answer key section.
    Returns a dict mapping question_number -> raw answer string.

    Handles formats:
      51.(2)      -> {51: "2"}
      51. (2)     -> {51: "2"}
      21.(34)     -> {21: "34"}   (integer-type: raw numeric)
      22.(2035)   -> {22: "2035"}
    """
    answer_map: dict[int, str] = {}
    in_key_section = False

    # Walk blocks in reverse to find the answer key section
    for block in reversed(blocks):
        if block.get("type") != "text":
            continue

        text = block.get("text", "").strip()
        text_lower = text.lower()

        # Detect the answer key header (we're scanning backwards, so
        # we hit entries first, then the header)
        if any(h in text_lower for h in _ANSWER_KEY_HEADERS):
            in_key_section = True
            continue

        # Once we've passed the header going backwards, we stop
        # (everything after the header = question content)
        if in_key_section and _looks_like_question_content(text):
            break

        # Parse answer entries from this block (even before we see header,
        # because entries appear before the header when scanning backwards)
        entries = _ANSWER_KEY_ENTRY_RE.findall(text)
        for q_num_str, raw_ans in entries:
            q_num = int(q_num_str)
            # Only accept if it looks like a real answer (not a question number)
            # Raw answer should be a short value: 1-4 for MCQ, or a number for integer
            if q_num not in answer_map and len(raw_ans) <= 6:
                answer_map[q_num] = raw_ans.strip()

    return answer_map


def _looks_like_question_content(text: str) -> bool:
    """Heuristic: does this text look like a question (not an answer key entry)?"""
    # Questions typically start with a number followed by a period and some text
    if re.match(r"^\d{1,3}\.\s+\S{10,}", text):
        return True
    # Options typically start with (1), (2), (3), (4)
    if re.search(r"\(1\).*\(2\)", text):
        return True
    return False
