from __future__ import annotations

import re

from app.services.question_builder.base import AD_KEYWORDS


def clean_content_blocks(blocks: list[dict]) -> list[dict]:
    """
    Run the full post-processing cleaning pipeline on raw MinerU content blocks.
    Each step is a pure function: list[dict] → list[dict].
    Order matters — ad pages must be removed before other filters run.
    """
    pipeline = [
        _remove_empty_blocks,
        _remove_ad_pages,
        _remove_watermark_banners,
        _remove_garbled_ocr,
        _deduplicate_consecutive_answers,
    ]
    result = blocks
    for fn in pipeline:
        result = fn(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Filter functions (all pure, no side effects)
# ─────────────────────────────────────────────────────────────────────────────

def _remove_empty_blocks(blocks: list[dict]) -> list[dict]:
    """Drop blocks with empty or whitespace-only text content."""
    result = []
    for b in blocks:
        if b.get("type") == "text":
            if not b.get("text", "").strip():
                continue
        result.append(b)
    return result


def _remove_ad_pages(blocks: list[dict]) -> list[dict]:
    """
    Identify page indexes that contain advertising content (ALLEN ads, etc.)
    and drop ALL blocks on those pages.

    Detection: a text block on that page contains one of the AD_KEYWORDS.
    """
    ad_page_indices: set[int] = set()
    for b in blocks:
        if b.get("type") == "text":
            text = b.get("text", "")
            if any(kw.lower() in text.lower() for kw in AD_KEYWORDS):
                page_idx = b.get("page_idx")
                if page_idx is not None:
                    ad_page_indices.add(page_idx)

    if not ad_page_indices:
        return blocks
    return [b for b in blocks if b.get("page_idx") not in ad_page_indices]


_BANNER_TEXTS = {
    "TEST PAPER WITH ANSWER KEY",
    "TIME : 9:00 AM  TO  12:00 NOON",
    "TIME: 9:00 AM TO 12:00 NOON",
}


def _remove_watermark_banners(blocks: list[dict]) -> list[dict]:
    """
    Drop header/banner blocks that MinerU picks up from page headers
    (e.g. "TEST PAPER WITH ANSWER KEY" that appears mid-document).
    These are identified by being text_level headers whose content
    matches known banner strings.
    """
    result = []
    for b in blocks:
        if b.get("type") == "text" and b.get("text_level"):
            text = b.get("text", "").strip()
            if any(banner in text for banner in _BANNER_TEXTS):
                continue
        result.append(b)
    return result


_HIGH_NONASCII_RE = re.compile(r"[^\x00-\x7F\$\\{}\[\]^_]")


def _remove_garbled_ocr(blocks: list[dict]) -> list[dict]:
    """
    Drop text blocks where more than 40% of characters are non-ASCII
    and non-LaTeX characters. These are garbled OCR artifacts from
    stylized ad pages (e.g. "H LE KT", "S 身 Z", "O # # 广").

    LaTeX characters ($, \\, {, }, ^, _) are excluded from the count
    because many valid blocks are predominantly LaTeX.
    """
    result = []
    for b in blocks:
        if b.get("type") != "text":
            result.append(b)
            continue
        text = b.get("text", "")
        if not text.strip():
            continue
        non_ascii_count = len(_HIGH_NONASCII_RE.findall(text))
        ratio = non_ascii_count / max(len(text), 1)
        if ratio > 0.40:
            continue
        result.append(b)
    return result


_ANS_RE = re.compile(r"Ans\.?\s*\(\s*[1-4A-Da-d]\s*\)", re.IGNORECASE)


def _deduplicate_consecutive_answers(blocks: list[dict]) -> list[dict]:
    """
    MinerU sometimes emits two consecutive answer blocks for the same question
    (a reading-order artifact). Keep only the latter when two answer-only
    blocks appear back-to-back.
    """
    result = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if (
            b.get("type") == "text"
            and _ANS_RE.fullmatch(b.get("text", "").strip())
            and i + 1 < len(blocks)
            and blocks[i + 1].get("type") == "text"
            and _ANS_RE.fullmatch(blocks[i + 1].get("text", "").strip())
        ):
            # Skip current, keep next
            i += 1
            continue
        result.append(b)
        i += 1
    return result
