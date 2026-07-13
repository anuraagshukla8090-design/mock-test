"""
full_paper.py  —  FullPaperBuilder  (v2, complete rewrite)
===========================================================

Handles JEE Main / NEET full-paper PDFs (MathonGo layout) where:
  • Questions numbered Q1.–Q75. (or 1.–90.) with NO subject headers
  • MCQ, Numerical/Integer, Assertion-Reason and Match-type questions
  • Answer key is a SEPARATE section at the very end of the document
  • MathonGo watermarks and page headers appear on every page

5-Stage deterministic pipeline
──────────────────────────────
  Stage 1 · FILTER   – classify every block as noise, content, or key
  Stage 2 · SEGMENT  – find answer-key boundary; split body vs key blocks
  Stage 3 · GROUP    – scan body blocks; bucket into per-question RawQuestion objects
  Stage 4 · BUILD    – convert each RawQuestion → Question (stem, options, images, type)
  Stage 5 · MERGE    – parse key blocks into answer_map; merge into Question objects

Option collection strategy (Stage 4)
──────────────────────────────────────
Rather than joining all text then parsing once, options are collected
PER BLOCK from multiple sources and merged:

  source_a  inline markers     "(1) text (2) text" inside any text block
  source_b  equation arrays    $$\\begin{array}…\\end{array}$$ blocks
  source_c  merged markers     "(13) $a$ $b$" or "(24) $a$ $b$" blocks
  source_d  embedded arrays    text block starting with "( $\\begin{array}…"

This naturally handles options scattered across separate blocks.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.services.question_builder.abstract_builder import AbstractBuilder
from app.services.question_builder.base import (
    NUM_TO_LETTER,
    LETTER_NORM,
    OPTION_MARKER_RE,
    Question,
    link_images_to_question,
    split_options_text,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants & compiled patterns
# ─────────────────────────────────────────────────────────────────────────────

# Question start: "Q1.", "Q 1.", "Q.1." — Q-prefix variant
_Q_PREFIX_RE = re.compile(r"^\s*[Qq]\.?\s*(\d{1,3})\s*[\.\)]\s*")

# Question start: "1. text" — plain number, requires following non-space char
_Q_PLAIN_RE = re.compile(r"^\s*(\d{1,3})\s*[\.\)]\s+\S")

# Answer-key entry: "1.(4)"  "21.(34)"  "22.(2035)" — spaces inside allowed
_ANS_ENTRY_RE = re.compile(r"\b(\d{1,3})\s*\.\s*\(\s*([^)]{1,8})\s*\)")

# Section header: "SECTION-A", "Section B"
_SECTION_RE = re.compile(r"\bSECTION[\s\-]+([A-Za-z])\b", re.IGNORECASE)

# Known answer-key header phrases (lowercased for comparison)
_ANS_KEY_HEADERS: frozenset[str] = frozenset([
    "answer key", "answer keys", "ans key", "ans. key",
    "answers", "answer sheet", "solution key",
])

# MathonGo watermark patterns
_WATERMARK_RES: list[re.Pattern] = [
    re.compile(r"mathon\s*go", re.IGNORECASE),
    re.compile(r"^m\s*a\s*t\s*h\s*o", re.IGNORECASE),
]

# Inline watermark (appended mid-block by MinerU)
_WATERMARK_INLINE_RE = re.compile(r"\bmathon\s*go\b", re.IGNORECASE)

# Page-header line patterns (short blocks, appear on every page)
_HEADER_RES: list[re.Pattern] = [
    re.compile(r"\d{4}\s*\(\s*\d{1,2}\s*\w+\s*Shift\s*\d+\s*\)", re.IGNORECASE),
    re.compile(r"JEE\s+Main\s+(Previous|January|April|June|July|August|2\d{3})", re.IGNORECASE),
    re.compile(r"Previous\s+Year\s+Paper", re.IGNORECASE),
    re.compile(r"NEET\s+\d{4}", re.IGNORECASE),
    re.compile(r"^TEST\s+PAPER\b", re.IGNORECASE),
    re.compile(r"^TIME\s*:", re.IGNORECASE),
    re.compile(r"JEE\s+(MAIN|ADVANCED)\s+EXAMINA", re.IGNORECASE),
    re.compile(r"HELD\s+ON\s+\w+day", re.IGNORECASE),
    re.compile(r"^JEE\s+Main\s+\d{4}\s+\w+$", re.IGNORECASE),
]

# Merged option-marker pattern: "(13)" or "(24)" at block start
# These are MinerU OCR artifacts from 2-column option grids
_MERGED_MARKER_RE = re.compile(r"^\s*\((13|24)\)\s*(.*)", re.DOTALL)

# Minimum length for a block to be considered meaningful text
_MIN_TEXT_LEN = 4

# MCQ answer normalisation table
_MCQ_ANS_MAP: dict[str, str] = {
    "1": "A", "2": "B", "3": "C", "4": "D",
    "a": "A", "b": "B", "c": "C", "d": "D",
    "A": "A", "B": "B", "C": "C", "D": "D",
}

# ── Equation-block option patterns ───────────────────────────────────────────

# Match a MinerU equation-block cell: "{{ 1) content }}" or "{{ (1) content }}"
# or "{{ \left(1\right) content }}"
# NOTE: \left comes BEFORE (, and \right comes BEFORE the closing )
_CELL_OPT_RE = re.compile(
    r"\{\s*\{\s*"                                          # opening {{ with spaces
    r"(?:\\left\s*)?\(?\s*([1-4])\s*(?:\\right\s*)?\)\s*" # (N), N), or \left(N\right)
    r"(.*?)"                                               # option content (non-greedy)
    r"\s*\}\s*\}",                                         # closing }}
    re.DOTALL,
)


# ─────────────────────────────────────────────────────────────────────────────
# Internal data structure
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _RawQuestion:
    """Accumulates MinerU blocks for one question before parsing."""
    number: int
    blocks: list[dict] = field(default_factory=list)
    section_label: str | None = None
    source_page: int | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _PreparedBlock:
    """A source block retained by the filter stage, with stable provenance."""

    source_index: int
    block: dict


@dataclass
class _FilterResult:
    """Output of the filter stage; issues are kept for the ingestion report."""

    blocks: list[_PreparedBlock]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _SegmentResult:
    """The body/key partition selected by the segment stage."""

    body: list[_PreparedBlock]
    answer_key: list[_PreparedBlock]
    boundary_source_index: int | None
    key_img_path: str | None = None  # Set when the key is an image block (LayoutLMv3 mode)


# ─────────────────────────────────────────────────────────────────────────────
# FullPaperBuilder
# ─────────────────────────────────────────────────────────────────────────────

class FullPaperBuilder(AbstractBuilder):
    """
    Parses JEE Main / NEET full-paper PDFs (MathonGo layout).

    Design decisions:
    - subject=None on all questions; filled later by the metadata LLM
    - Answer key is parsed from document tail, never from fixed page numbers
    - Question detection handles both "Q1." and "1." number formats
    - All noise (watermarks, headers, page numbers) filtered deterministically
    - Options are collected per-block and merged, not by joining all text at once
    - INTEGER vs MCQ determined by option presence only, never from the answer key
    """

    def __init__(self, blocks: list[dict], images_dir: Path) -> None:
        super().__init__(blocks, images_dir)
        self.report: dict = {}
        self.stage_warnings: list[str] = []

    # ── Main entry point ──────────────────────────────────────────────────────

    def build(self) -> list[Question]:
        logger.info("FullPaperBuilder: starting — %d raw blocks", len(self.blocks))

        # Stage 1: retain parseable blocks and record why text was discarded.
        filtered = _filter_blocks(self.blocks)
        self.stage_warnings = filtered.warnings

        # Stage 2: segment the retained reading order into paper body and key.
        segment = _segment_blocks(filtered.blocks)
        body_blocks = [item.block for item in segment.body]
        key_blocks = [item.block for item in segment.answer_key]
        key_boundary_warning: str | None = None
        if not key_blocks and not segment.key_img_path:
            key_boundary_warning = (
                "answer-key boundary not found in MinerU text; the answer-key page "
                "may have been emitted as an image block"
            )
            self.stage_warnings.append(key_boundary_warning)
        elif not key_blocks and segment.key_img_path:
            logger.info(
                "FullPaperBuilder: answer key is an image block — will run OCR fallback on %s",
                segment.key_img_path,
            )

        # Stage 3: Group body blocks into per-question buckets
        raw_questions = _group_into_questions(body_blocks)
        logger.info("FullPaperBuilder: %d raw question groups", len(raw_questions))

        # Stage 4: Build Question objects from each bucket
        questions: list[Question] = []
        seen: set[int] = set()
        duplicates: set[int] = set()

        for rq in raw_questions:
            q = _build_question(rq, self.images_dir)
            if q is None:
                continue
            if q.question_number in seen:
                duplicates.add(q.question_number)
                q.warnings.append(f"Q{q.question_number}: duplicate question number detected")
                self.stage_warnings.extend(q.warnings)
                # Do not persist a second question with the same source number.
                # This preserves the first reading-order group and exposes the
                # conflicting OCR as a review warning instead of corrupting the
                # question bank with a duplicate primary business key.
                continue
            seen.add(q.question_number)
            questions.append(q)

        # Stage 5: Parse answer key and merge into questions
        answer_map = _parse_answer_key(key_blocks)

        # Stage 5b: OCR fallback — triggered when LayoutLMv3 emits the answer key
        # page as a type=table or type=image block with no text/html (only img_path).
        if not answer_map and segment.key_img_path:
            logger.info("FullPaperBuilder: running OCR fallback on answer key image")
            try:
                from app.services.mineru_runner import run_ocr_on_image
                ocr_text = run_ocr_on_image(self.images_dir / Path(segment.key_img_path).name)
                if ocr_text:
                    answer_map = _parse_answer_key_from_text(ocr_text)
                    logger.info(
                        "FullPaperBuilder: OCR fallback extracted %d answers", len(answer_map)
                    )
                else:
                    logger.warning("FullPaperBuilder: OCR fallback returned empty text")
            except Exception as _ocr_exc:
                logger.warning("FullPaperBuilder: OCR fallback failed: %s", _ocr_exc)

        logger.info("FullPaperBuilder: %d answers in key", len(answer_map))

        _merge_answers(questions, answer_map)
        validation_warnings = _validate_questions(questions, answer_map)
        self.stage_warnings.extend(validation_warnings)

        # The current ingestion contract stores warnings from Question objects,
        # not builder reports. Attach document-level issues once so they remain
        # visible to teacher review without changing that public contract.
        if questions:
            if key_boundary_warning:
                questions[0].warnings.append(key_boundary_warning)
            questions[0].warnings.extend(validation_warnings)

        # Detect gaps in question numbering
        missing: set[int] = set()
        if seen:
            expected = set(range(min(seen), max(seen) + 1))
            missing = expected - seen
            if missing:
                logger.warning("FullPaperBuilder: missing Q numbers: %s", sorted(missing))

        self._generate_report(questions, answer_map, seen, missing, duplicates)
        return sorted(questions, key=lambda q: q.question_number)

    @classmethod
    def can_handle(cls, blocks: list[dict]) -> bool:
        """
        Auto-detect: requires Q-prefix question numbers AND an answer key header
        somewhere in the last 25% of text blocks.
        """
        text_blocks = [b for b in blocks if b.get("type") == "text"]
        has_q_prefix = any(
            _Q_PREFIX_RE.match(b.get("text", ""))
            for b in text_blocks[:50]
        )
        tail = text_blocks[int(len(text_blocks) * 0.75):]
        has_key = any(_is_answer_key_header(b.get("text", "")) for b in tail)
        return has_q_prefix and has_key

    def _generate_report(
        self,
        questions: list[Question],
        answer_map: dict[int, str],
        seen: set[int],
        missing: set[int],
        duplicates: set[int],
    ) -> None:
        mcq     = [q for q in questions if q.section_type == "mcq"]
        integer = [q for q in questions if q.section_type == "integer"]
        no_ans  = [q for q in questions if not q.answer]

        self.report = {
            "total_extracted":          len(questions),
            "mcq_count":                len(mcq),
            "integer_count":            len(integer),
            "with_diagram":             sum(1 for q in questions if q.images),
            "no_answer":                len(no_ans),
            "answer_key_size":          len(answer_map),
            "missing_question_numbers": sorted(missing),
            "duplicate_question_numbers": sorted(duplicates),
            "stage_warnings": list(self.stage_warnings),
        }

        logger.info("FullPaperBuilder report:")
        logger.info("  Total extracted : %d", self.report["total_extracted"])
        logger.info("  MCQ             : %d", self.report["mcq_count"])
        logger.info("  Integer/NAT     : %d", self.report["integer_count"])
        logger.info("  With diagram    : %d", self.report["with_diagram"])
        logger.info("  No answer       : %d", self.report["no_answer"])
        logger.info("  Answer key size : %d", self.report["answer_key_size"])
        if duplicates:
            logger.warning("  Duplicate Q#s   : %s", sorted(duplicates))
        if missing:
            logger.warning("  Missing Q#s     : %s", sorted(missing))


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Find answer-key boundary
# ─────────────────────────────────────────────────────────────────────────────

def _filter_blocks(blocks: list[dict]) -> _FilterResult:
    """Filter deterministic noise while preserving source order and provenance.

    This stage does not repair OCR. Images and equations are always retained as
    evidence for grouping and validation, even when they carry no text.
    """
    retained: list[_PreparedBlock] = []
    warnings: list[str] = []
    for source_index, block in enumerate(blocks):
        if block.get("type") == "text" and _is_noise(block):
            warnings.append(
                "block "
                f"{source_index} (page {block.get('page_idx')}): "
                "discarded deterministic noise"
            )
            continue
        retained.append(_PreparedBlock(source_index=source_index, block=block))
    return _FilterResult(blocks=retained, warnings=warnings)


def _segment_blocks(blocks: list[_PreparedBlock]) -> _SegmentResult:
    """Split filtered blocks at the first deterministic answer-key boundary."""
    boundary, key_img_path = _find_answer_key_boundary([item.block for item in blocks])
    return _SegmentResult(
        body=blocks[:boundary],
        answer_key=blocks[boundary:],
        boundary_source_index=(
            blocks[boundary].source_index if boundary < len(blocks) else None
        ),
        key_img_path=key_img_path,
    )


def _find_answer_key_boundary(blocks: list[dict]) -> tuple[int, str | None]:
    """
    Scan backwards for the first answer-key section header.
    Falls back to density detection (3+ N.(x) entries in one block) in the last 15%.

    Returns:
        (boundary_index, key_img_path)
        - boundary_index: index into blocks where answer key starts.
          len(blocks) means no text-based key found.
        - key_img_path: relative img_path string if the key was found as a
          type=table or type=image block with no text (LayoutLMv3 mode).
          None if the key was found as parseable text blocks.
    """
    for i in range(len(blocks) - 1, -1, -1):
        b = blocks[i]
        btype = b.get("type")
        if btype not in ("text", "table"):
            continue
        text_content = b.get("text", "") or b.get("html", "")
        clean_text = re.sub(r"<[^>]+>", " ", text_content)
        if _is_answer_key_header(clean_text.strip()):
            logger.info(
                "FullPaperBuilder: answer key header at block %d: %r",
                i, clean_text[:60],
            )
            return i, None

    # Fallback: dense cluster of answer entries in the tail
    tail_start = int(len(blocks) * 0.85)
    for i in range(tail_start, len(blocks)):
        b = blocks[i]
        btype = b.get("type")
        if btype not in ("text", "table"):
            continue
        text_content = b.get("text", "") or b.get("html", "")
        clean_text = re.sub(r"<[^>]+>", " ", text_content)
        if len(_ANS_ENTRY_RE.findall(clean_text)) >= 3:
            logger.info("FullPaperBuilder: answer key detected by density at block %d", i)
            return i, None

    # ── LayoutLMv3 image fallback ─────────────────────────────────────────────
    # LayoutLMv3 often emits the answer key page as a type=table block with
    # only img_path (no text/html), or as a bare type=image on the last page.
    # Scan the last 5 blocks for such a candidate.
    for i in range(len(blocks) - 1, max(len(blocks) - 6, -1), -1):
        b = blocks[i]
        btype = b.get("type")
        img_path = b.get("img_path", "")
        if not img_path:
            continue
        text_content = (b.get("text", "") or b.get("html", "") or "").strip()
        if btype in ("table", "image") and not text_content:
            logger.info(
                "FullPaperBuilder: answer key detected as image block at index %d: %s",
                i, img_path,
            )
            return i, img_path

    logger.warning(
        "FullPaperBuilder: no answer key section found — questions will have answer=None"
    )
    return len(blocks), None


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: Group blocks into per-question buckets
# ─────────────────────────────────────────────────────────────────────────────

def _group_into_questions(blocks: list[dict]) -> list[_RawQuestion]:
    """
    Sequential forward scan through body blocks.
    A block that starts a new question number opens a new _RawQuestion bucket.
    All subsequent blocks belong to that bucket until the next question start.

    Noise blocks (watermarks, page headers) are silently discarded.
    Images and equations are always forwarded to the current question.
    """
    raw: dict[int, _RawQuestion] = {}
    order: list[int] = []
    groups: list[_RawQuestion] = []
    current: _RawQuestion | None = None
    current_section: str | None = None

    for block in blocks:
        btype = block.get("type", "")
        text  = block.get("text", "").strip()

        # Always forward non-text blocks to the current question
        if btype in ("image", "equation") or (btype == "table" and block.get("img_path")):
            if current is not None:
                current.blocks.append(block)
            continue

        if btype != "text":
            continue

        # Discard noise text blocks
        if _is_noise(block):
            continue

        # Detect section-label blocks (short, like "SECTION-A")
        sec = _SECTION_RE.search(text)
        if sec and len(text) < 40:
            current_section = f"SECTION-{sec.group(1).upper()}"
            # Don't skip — the section label might share a block with a question

        # Detect question start
        q_num = _parse_question_number(text)
        if q_num is not None:
            if q_num in raw:
                # Duplicate question number — add block to existing bucket
                rq = _RawQuestion(
                    number=q_num,
                    section_label=current_section,
                    source_page=block.get("page_idx"),
                )
                rq.warnings.append(f"Q{q_num}: duplicate question start detected")
                rq.blocks.append(block)
                groups.append(rq)
                current = rq
            else:
                rq = _RawQuestion(
                    number=q_num,
                    section_label=current_section,
                    source_page=block.get("page_idx"),
                )
                rq.blocks.append(block)
                raw[q_num] = rq
                order.append(q_num)
                groups.append(rq)
                current = rq
            continue

        # Continuation block — belongs to current question
        if current is not None:
            current.blocks.append(block)
        # else: preamble before first question — discard silently

    return groups


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4: Build a Question from a _RawQuestion
# ─────────────────────────────────────────────────────────────────────────────

def _build_question(rq: _RawQuestion, images_dir: Path) -> Question | None:
    """
    Convert a _RawQuestion (raw MinerU blocks) into a Question object.

    Option collection strategy
    ──────────────────────────
    Options are gathered from every block independently, then merged:
      • Each text block is scanned for inline option markers (1)(2)(3)(4)
      • Each equation block is checked for a LaTeX option array
      • Text blocks starting with "(13)" or "(24)" are split as merged markers
      • Text blocks starting with "( $\\begin{array}" have their embedded array parsed

    This handles all observed MinerU output patterns without joining text blocks.

    Stem reconstruction
    ───────────────────
    For each text block:
      - If the block contains ONLY option markers (and no preamble text),
        its text is NOT added to the stem parts.
      - If the block contains stem text followed by options, only the
        pre-option portion is added to the stem.
      - Pure stem blocks are added in full.
    """
    stem_parts: list[str]   = []
    all_options: dict[str, str] = {}
    image_blocks: list[dict] = []
    warnings = list(rq.warnings)

    for block in rq.blocks:
        btype = block.get("type", "")

        # ── Image blocks ──────────────────────────────────────────────────────
        if btype == "image" or (btype == "table" and block.get("img_path")):
            image_blocks.append(block)
            continue

        # ── Equation blocks ───────────────────────────────────────────────────
        if btype == "equation":
            eq_text = block.get("text", "").strip()
            if not eq_text:
                continue
            eq_opts = _parse_equation_block_options(eq_text)
            if eq_opts:
                # This equation block is an option array — extract and skip stem
                _merge_option_candidates(all_options, eq_opts, warnings, rq.number, "equation")
            else:
                # This is a formula belonging to the stem
                stem_parts.append(eq_text)
            continue

        if btype != "text":
            continue

        # ── Text blocks ───────────────────────────────────────────────────────
        raw_text = block.get("text", "")
        t = _normalize_text_block(raw_text)
        if not t:
            continue

        # Pattern: embedded LaTeX array inside a text block
        # "( $\begin{array}...  \end{array}$ )"
        embedded = _parse_embedded_array(t)
        if embedded:
            _merge_option_candidates(all_options, embedded, warnings, rq.number, "embedded array")
            continue

        # Pattern: merged option markers "(13) $val_a$ $val_c$"
        merged = _parse_merged_marker_block(t)
        if merged is not None:
            # merged == {} means block was a merged marker but unrecoverable
            _merge_option_candidates(all_options, merged, warnings, rq.number, "merged marker")
            continue

        # Normal text block: collect any inline options AND stem text
        block_opts = _collect_inline_options(t)
        _merge_option_candidates(all_options, block_opts, warnings, rq.number, "text block")

        # Add pre-option text to stem (or the whole block if no options found)
        stem_fragment = _extract_stem_fragment(t)
        if stem_fragment:
            stem_parts.append(stem_fragment)

    if not stem_parts:
        logger.warning("Q%d: no text content — skipping", rq.number)
        return None

    # Strip question number prefix from first stem part only
    stem_parts[0] = _strip_q_prefix(stem_parts[0])

    stem = "\n".join(stem_parts).strip()
    if not stem:
        logger.warning("Q%d: empty stem after prefix strip — skipping", rq.number)
        return None

    # Classify: MCQ if any options collected, integer otherwise
    section_type = "mcq" if all_options else "integer"

    # Warn about partial option recovery
    if all_options and len(all_options) < 4:
        warnings.append(
            f"Q{rq.number}: options_missing — recovered {len(all_options)}/4 options "
            f"(PDF OCR may have dropped the rest)"
        )

    images = link_images_to_question(image_blocks, images_dir)
    linked_image_names = {image["filename"] for image in images}
    for image_block in image_blocks:
        filename = Path(image_block.get("img_path", "")).name
        if filename and filename not in linked_image_names:
            warnings.append(
                f"Q{rq.number}: MinerU image {filename!r} could not be linked"
            )

    return Question(
        question_number=rq.number,
        stem_md=stem,
        options=all_options,
        answer="",          # filled by Stage 5
        section_type=section_type,
        section_label=rq.section_label,
        images=images,
        source_page=rq.source_page,
        subject=None,       # filled by metadata LLM (detect_subject=True)
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 helpers — option collection
# ─────────────────────────────────────────────────────────────────────────────

def _merge_option_candidates(
    options: dict[str, str],
    candidates: dict[str, str],
    warnings: list[str],
    question_number: int,
    source: str,
) -> None:
    """Merge options without silently replacing conflicting OCR output."""
    for label, value in candidates.items():
        existing = options.get(label)
        if existing is None:
            options[label] = value
        elif existing != value:
            warnings.append(
                f"Q{question_number}: conflicting option {label} from {source}; "
                "kept first reading-order value"
            )


def _collect_inline_options(text: str) -> dict[str, str]:
    """
    Collect all inline option markers from a text block.
    Uses split_options_text to handle "(1) foo (2) bar" patterns.
    Returns {} if no options found.
    """
    # Find all option marker positions
    positions = [(m.start(), m.group(1)) for m in OPTION_MARKER_RE.finditer(text)]
    if not positions:
        return {}

    options: dict[str, str] = {}
    for i, (start, label) in enumerate(positions):
        content_start = start + len(f"({label})")
        content_end   = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        content = text[content_start:content_end].strip()
        key = NUM_TO_LETTER.get(label, LETTER_NORM.get(label, label.upper()))
        if content:
            options[key] = content
    return options


def _extract_stem_fragment(text: str) -> str:
    """
    Return the stem portion of a text block (everything before the first option marker).
    If no option marker is found, returns the full text.
    Returns "" if the block starts immediately with an option marker (options-only block).
    """
    first = OPTION_MARKER_RE.search(text)
    if first is None:
        return text.strip()
    pre = text[:first.start()].strip()
    return pre   # may be "" for blocks that start with "(1) ..."


def _parse_merged_marker_block(text: str) -> dict[str, str] | None:
    """
    Handle MinerU's merged option markers: "(13) $val_a$ $val_c$" or "(24) $val_b$ $val_d$".

    MinerU OCRs a 2-column option grid as a single text block, merging option
    number labels (1)(3) → (13) and (2)(4) → (24).

    Returns:
      None       — text does NOT start with a merged marker (treat as normal)
      {}         — text IS a merged marker but content cannot be split (warning logged)
      {A,C}/{B,D} — successfully extracted option pair
    """
    m = _MERGED_MARKER_RE.match(text)
    if m is None:
        return None

    pair = m.group(1)   # "13" or "24"
    rest = m.group(2).strip()
    d1, d2 = ("1", "3") if pair == "13" else ("2", "4")

    # Split on $...$ boundaries (most reliable separator for math options)
    dollar_exprs = re.findall(r"\$[^$]+\$", rest)
    if len(dollar_exprs) >= 2:
        return {
            NUM_TO_LETTER[d1]: dollar_exprs[0].strip(),
            NUM_TO_LETTER[d2]: dollar_exprs[1].strip(),
        }

    # Fallback: split on double-space or newline
    parts = re.split(r"\s{2,}|\n", rest, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return {
            NUM_TO_LETTER[d1]: parts[0].strip(),
            NUM_TO_LETTER[d2]: parts[1].strip(),
        }

    logger.warning(
        "FullPaperBuilder: merged marker %r has no recoverable split — options may be missing",
        text[:80],
    )
    return {}


def _parse_embedded_array(text: str) -> dict[str, str]:
    """
    Handle a text block that contains an embedded LaTeX array.

    MinerU sometimes places option arrays inside type='text' blocks (not equation):
      "( $\\begin{array}{c}{{ 2) 22\\pi^2 }} \\\\ {{ 4) 18\\pi^2 }}\\end{array}$ )"

    The block starts with a bare "(" followed immediately by "$\\begin{array}".
    We detect this pattern, extract the embedded $...$ content, and parse it as
    an equation block.

    Returns {} if the pattern is not detected or parsing fails.
    """
    stripped = text.strip()
    if not re.match(r"^\(\s*\$\s*\\begin", stripped):
        return {}

    # Extract the content between the outermost $ signs
    start = text.find("$")
    end   = text.rfind("$")
    if start == -1 or end <= start:
        return {}

    # Wrap in $$ to satisfy the equation-block parser's guard
    embedded = "$$" + text[start + 1:end] + "$$"
    return _parse_equation_block_options(embedded)


def _parse_equation_block_options(eq_text: str) -> dict[str, str]:
    """
    Extract options from a MinerU equation block containing a LaTeX array.

    MinerU wraps 2-column option grids as LaTeX arrays:
      $$\\begin{array}{c}{{ 1) 3\\pi+8 }} \\\\ {{ 3) 3\\pi-8 }}\\end{array}$$

    Processing:
      1. Guard: must contain \\begin (1 actual backslash)
      2. Strip $$ wrapper and \\begin{array}...\\end{array} frame
      3. Split on LaTeX row separator \\\\ (2 actual backslashes) and & (columns)
      4. Match each cell against _CELL_OPT_RE to extract (N) + content

    Returns {} if:
      - No \\begin{array} present (plain formula — belongs to stem)
      - Fewer than 2 options extracted (false-positive guard)
    """
    # Guard: 1 actual backslash + "begin" in the content string
    if "\\" + "begin" not in eq_text:
        return {}

    text = eq_text.replace("$$", " ")
    # Strip \begin{array}{format} — handles MinerU's spaced braces
    text = re.sub(r"\\begin\s*\{\s*array\s*\}\s*(?:\{[^}]*\})?\s*", " ", text)
    text = re.sub(r"\\end\s*\{\s*array\s*\}", " ", text)
    # Split on LaTeX row separator (2 backslashes in content) and column separator
    cells = re.split(r"\\\\|&", text)

    options: dict[str, str] = {}
    for cell in cells:
        cell = cell.strip()
        if not cell:
            continue
        m = _CELL_OPT_RE.search(cell)
        if m:
            num_str = m.group(1)
            content = m.group(2).strip()
            letter  = NUM_TO_LETTER.get(num_str, num_str)
            if content:
                options[letter] = content

    # Require at least 2 options — a single match is likely a false positive
    return options if len(options) >= 2 else {}


# ─────────────────────────────────────────────────────────────────────────────
# Stage 5: Parse answer key and merge
# ─────────────────────────────────────────────────────────────────────────────

def _parse_answer_key(key_blocks: list[dict]) -> dict[int, str]:
    """
    Extract {question_number: raw_answer_string} from the answer-key blocks.
    Handles both MCQ answers (1–4) and integer/NAT answers (any number string).
    First occurrence wins (in case of duplicate entries).
    """
    answer_map: dict[int, str] = {}
    for block in key_blocks:
        btype = block.get("type")
        if btype not in ("text", "table"):
            continue
        
        text_content = block.get("text", "") or block.get("html", "")
        # Strip HTML tags so regex matches cleanly
        clean_text = re.sub(r"<[^>]+>", " ", text_content)
        
        for q_str, raw_ans in _ANS_ENTRY_RE.findall(clean_text):
            q_num = int(q_str)
            raw   = raw_ans.strip()
            if q_num not in answer_map and raw:
                answer_map[q_num] = raw
    return answer_map


def _parse_answer_key_from_text(text: str) -> dict[int, str]:
    """
    Parse a raw OCR text string (not a list of blocks) using the same
    _ANS_ENTRY_RE pattern used by _parse_answer_key().

    Called by the OCR fallback path when the answer key was emitted as an
    image by LayoutLMv3 and PaddleOCR returns a flat string like:
      "1.(4) 2.(3) 3.(2) ... 75.(20)"

    Returns {question_number: raw_answer_string} identical in shape to
    _parse_answer_key().
    """
    answer_map: dict[int, str] = {}
    for q_str, raw_ans in _ANS_ENTRY_RE.findall(text):
        q_num = int(q_str)
        raw = raw_ans.strip()
        if q_num not in answer_map and raw:
            answer_map[q_num] = raw
    return answer_map


def _merge_answers(questions: list[Question], answer_map: dict[int, str]) -> None:
    """
    Mutate each Question in-place: set answer from the answer_map.
    MCQ answers are normalized to A/B/C/D.
    Integer answers are kept as raw strings.
    """
    for q in questions:
        raw = answer_map.get(q.question_number)
        if not raw:
            q.warnings.append(f"Q{q.question_number}: answer not found in answer key")
            continue

        if q.section_type == "mcq":
            normalized = _MCQ_ANS_MAP.get(raw.strip(), raw.strip().upper())
            q.answer = normalized
            if normalized not in {"A", "B", "C", "D"}:
                q.warnings.append(
                    f"Q{q.question_number}: unrecognised MCQ answer key value {raw!r}"
                )
        else:
            q.answer = raw.strip()


def _validate_questions(questions: list[Question], answer_map: dict[int, str]) -> list[str]:
    """Attach deterministic consistency warnings without changing extracted data."""
    question_numbers = {question.question_number for question in questions}
    for question in questions:
        if question.section_type == "mcq":
            expected = {"A", "B", "C", "D"}
            missing = expected - set(question.options)
            if missing and not any("options_missing" in w for w in question.warnings):
                question.warnings.append(
                    f"Q{question.question_number}: options_missing — missing {sorted(missing)}"
                )
    return [
        f"answer key contains Q{question_number} with no built question"
        for question_number in sorted(set(answer_map) - question_numbers)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Noise filter
# ─────────────────────────────────────────────────────────────────────────────

def _is_noise(block: dict) -> bool:
    """
    Return True if this text block should be discarded entirely.

    Rules (in order — first match wins):
      1. Empty or too short
      2. Pure digits (page numbers: "3", "14")
      3. Matches a watermark pattern
      4. Short AND matches a page-header pattern AND is NOT a question start
    """
    text = block.get("text", "").strip()

    if len(text) < _MIN_TEXT_LEN:
        return True

    if re.match(r"^\d{1,4}$", text):
        return True

    if any(p.search(text) for p in _WATERMARK_RES):
        return True

    # Only filter header patterns if the block is short (they're brief headings)
    # and doesn't start a question (rare but possible edge case)
    if len(text) < 100 and any(p.search(text) for p in _HEADER_RES):
        if _parse_question_number(text) is None:
            return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Text normalization
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text_block(text: str) -> str:
    """
    Light, deterministic cleanup applied to every text block before parsing.
    Strips inline watermark tokens and collapses excess whitespace.
    Does NOT perform option-marker normalization (that is context-sensitive).
    """
    text = text.strip()
    if not text:
        return text
    text = _WATERMARK_INLINE_RE.sub(" ", text)
    text = re.sub(r" {2,}", " ", text).strip()
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Question number helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_question_number(text: str) -> int | None:
    """
    Return the question number if this text starts a new question, else None.
    Handles:
      "Q1."  "Q 1."  "Q.1."  — Q-prefix
      "1. text"  "26. text"  — plain number with following content
    """
    m = _Q_PREFIX_RE.match(text)
    if m:
        return int(m.group(1))
    m = _Q_PLAIN_RE.match(text)
    if m:
        return int(m.group(1))
    return None


def _strip_q_prefix(text: str) -> str:
    """Remove leading 'Q1.' or '1. ' from the first stem part."""
    stripped = _Q_PREFIX_RE.sub("", text, count=1).strip()
    if stripped != text.strip():
        return stripped
    # Plain number prefix
    return re.sub(r"^\s*\d{1,3}\s*[\.\)]\s*", "", text, count=1).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Answer-key header detection
# ─────────────────────────────────────────────────────────────────────────────

def _is_answer_key_header(text: str) -> bool:
    """Return True if text looks like an ANSWER KEYS section header."""
    norm = text.strip().lower()
    if norm in _ANS_KEY_HEADERS:
        return True
    for h in _ANS_KEY_HEADERS:
        if h in norm:
            return True
    return False
