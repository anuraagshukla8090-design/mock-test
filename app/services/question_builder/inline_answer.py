from __future__ import annotations

import re
from pathlib import Path

from app.services.question_builder.abstract_builder import AbstractBuilder
from app.services.question_builder.base import (
    ANSWER_RE,
    QUESTION_NUMBER_RE,
    AD_KEYWORDS,
    Question,
    extract_answer,
    is_answer_block,
    is_question_start,
    link_images_to_question,
    parse_latex_array_options,
    split_options_text,
    strip_latex_for_search,
)

# Section labels detected from PDF headers
_SECTION_RE = re.compile(r"SECTION[-\s]*([A-B])", re.IGNORECASE)
# Subject headers
_SUBJECT_MAP = {
    "PHYSICS": "physics",
    "CHEMISTRY": "chemistry",
    "MATHEMATICS": "maths",
    "MATHS": "maths",
    "MATH": "maths",
    "BIOLOGY": "biology",
}


class InlineAnswerBuilder(AbstractBuilder):
    """
    Handles PDFs where the answer appears immediately after each question
    (within a few content blocks), in the pattern:

        51. [stem text]
        (1) opt_A  (2) opt_B  (3) opt_C  (4) opt_D
        Ans. (4)

    This is the layout of ALLEN JEE Main papers.
    """

    # ── Auto-detection ────────────────────────────────────────────────────────

    @classmethod
    def can_handle(cls, blocks: list[dict]) -> bool:
        """
        Detect inline-answer layout:
        >60% of question starts have an answer block within 5 blocks after them.
        """
        q_positions = [
            i for i, b in enumerate(blocks) if is_question_start(b)[0]
        ]
        if not q_positions:
            return False

        nearby_count = 0
        for qp in q_positions:
            window = blocks[qp + 1 : qp + 6]
            if any(is_answer_block(b) for b in window):
                nearby_count += 1

        return (nearby_count / len(q_positions)) > 0.6

    # ── Main build ────────────────────────────────────────────────────────────

    def build(self) -> list[Question]:
        """Parse all blocks into Question objects."""
        questions: list[Question] = []
        groups = self._split_into_groups()

        for group in groups:
            q = self._parse_group(group)
            if q is not None:
                questions.append(q)

        # Fix MinerU reading-order bugs by sorting on question number
        questions.sort(key=lambda q: q.question_number)
        return questions

    # ── Pre-processing: subject & section tracking ────────────────────────────

    def _split_into_groups(self) -> list[dict]:
        """
        Walk the blocks once to:
          1. Track current subject and section label
          2. Group blocks between question boundaries
          3. Return list of group dicts
        """
        groups = []
        current_subject: str | None = None
        current_section: str | None = None
        current_group: list[dict] | None = None
        current_q_num: int | None = None

        for block in self.blocks:
            btype = block.get("type", "")
            text = block.get("text", "").strip()

            # Detect subject from a header block
            if btype == "text" and block.get("text_level"):
                upper = text.upper()
                for kw, subj in _SUBJECT_MAP.items():
                    if kw in upper:
                        current_subject = subj
                        break
                # Detect section label
                m = _SECTION_RE.search(text)
                if m:
                    current_section = f"SECTION-{m.group(1).upper()}"

            # Detect question boundary
            is_q, q_num = is_question_start(block)
            if is_q and q_num is not None:
                # Save previous group
                if current_group is not None:
                    groups.append({
                        "q_num": current_q_num,
                        "subject": current_subject,
                        "section": current_section,
                        "blocks": current_group,
                    })
                current_group = [block]
                current_q_num = q_num
            elif current_group is not None:
                current_group.append(block)

        # Save last group
        if current_group is not None and current_q_num is not None:
            groups.append({
                "q_num": current_q_num,
                "subject": current_subject,
                "section": current_section,
                "blocks": current_group,
            })

        return groups

    # ── Per-group parsing ─────────────────────────────────────────────────────

    def _parse_group(self, group: dict) -> Question | None:
        """Parse one question group into a Question object."""
        q_num: int = group["q_num"]
        blocks: list[dict] = group["blocks"]
        warnings: list[str] = []

        # Collect blocks by type
        text_blocks = [b for b in blocks if b.get("type") == "text"]
        equation_blocks = [b for b in blocks if b.get("type") == "equation"]
        image_blocks = [b for b in blocks if b.get("type") == "image"]

        # ── Extract answer ────────────────────────────────────────────────────
        answer: str | None = None
        answer_block_idx: int | None = None
        for i, b in enumerate(text_blocks):
            ans = extract_answer(b.get("text", ""))
            if ans is not None:
                answer = ans
                answer_block_idx = i
                break

        if answer is None:
            warnings.append(f"Q{q_num}: No answer found — skipping")
            return None

        # ── Build stem + options from text blocks before the answer ───────────
        pre_answer_texts = [
            b["text"] for b in text_blocks[:answer_block_idx]
            if b.get("text", "").strip()
        ]

        # ── Inject display equations into the stem ────────────────────────────
        # Each display equation block gets wrapped in $$ ... $$ and appended to stem
        display_eq_md = "\n\n".join(
            f"$${eq['text'].strip()}$$"
            for eq in equation_blocks
            if eq.get("text", "").strip()
        )

        # ── Find options ──────────────────────────────────────────────────────
        options: dict[str, str] = {}
        stem_parts: list[str] = []

        for raw in pre_answer_texts:
            # Try to parse options from this text block
            parsed_opts = split_options_text(raw)
            if not parsed_opts:
                # Check for LaTeX array options embedded in text
                array_match = re.search(r"\\begin\{array\}.*?\\end\{array\}", raw, re.DOTALL)
                if array_match:
                    parsed_opts = parse_latex_array_options(array_match.group())

            if parsed_opts and not options:
                options = parsed_opts
                # The stem is everything before the option block in this text
                option_start = raw.find("(1)") if "(1)" in raw else raw.find("(A)")
                if option_start > 0:
                    stem_parts.append(raw[:option_start].strip())
            else:
                stem_parts.append(raw)

        # Build stem markdown
        stem_md = "\n\n".join(p for p in stem_parts if p)
        if display_eq_md:
            stem_md = (stem_md + "\n\n" + display_eq_md).strip()

        if not stem_md:
            warnings.append(f"Q{q_num}: Empty stem — skipping")
            return None

        # ── Link images ───────────────────────────────────────────────────────
        images = link_images_to_question(image_blocks, self.images_dir)

        # ── Determine section type ────────────────────────────────────────────
        # Integer-type questions have no options
        section_type = "integer" if not options else "mcq"

        # ── Source page ───────────────────────────────────────────────────────
        source_page = blocks[0].get("page_idx") if blocks else None

        return Question(
            question_number=q_num,
            stem_md=stem_md,
            options=options,
            answer=answer,
            section_type=section_type,
            section_label=group["section"],
            images=images,
            source_page=source_page,
            subject=group["subject"],
            warnings=warnings,
        )
