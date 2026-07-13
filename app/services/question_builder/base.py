from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
# ─────────────────────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────────────────────
# Matches question starters like "51." or "1." at the beginning of a text block
QUESTION_NUMBER_RE = re.compile(r"^\s*(\d{1,3})\.\s+")
# Matches option markers like "(1)", "(2)", "(A)", "(B)" etc.
OPTION_MARKER_RE = re.compile(r"\(\s*([1-4A-Da-d])\s*\)")
# Matches answer lines like "Ans. (4)", "Ans. (D)", "Ans.  (B)"
ANSWER_RE = re.compile(r"Ans\.?\s*\(\s*([1-4A-Da-d])\s*\)", re.IGNORECASE)
# Maps numeric option labels to letter keys
NUM_TO_LETTER = {"1": "A", "2": "B", "3": "C", "4": "D"}
LETTER_NORM = {"a": "A", "b": "B", "c": "C", "d": "D",
               "A": "A", "B": "B", "C": "C", "D": "D"}
# Ad / banner keywords found in ALLEN PDFs — used by post_processor too
AD_KEYWORDS: set[str] = {
    "JOIN LEADER COURSE",
    "ALLEN Scholarship",
    "ASAT",
    "SHOP NOW",
    "DON'T PREPARE HARDER",
    "Leader Online Course",
    "Leader Self-Study",
    "ALLEN Thank You",
    "Join the journey",
    "scholarshipwth",
    "MAINPYQ",
}
# ─────────────────────────────────────────────────────────────────────────────
# Question dataclass
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Question:
    """
    Universal question representation produced by all builders.
    Every field maps 1:1 to a column in the questions table.
    """
    question_number: int
    stem_md: str                              # Markdown with inline $latex$
    options: dict[str, str]                   # {"A": "...", "B": "..."}  or {}
    answer: str                               # "A" / "B" / "C" / "D" or integer string
    section_type: str = "mcq"                 # "mcq" | "integer"
    section_label: str | None = None          # "SECTION-A" | "SECTION-B"
    images: list[dict] = field(default_factory=list)
    # [{"filename": "abc.jpg", "position": "stem"}]
    source_page: int | None = None
    subject: str | None = None                # Detected from PDF headers
    warnings: list[str] = field(default_factory=list)
# ─────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────────────────────────────────────────
def is_question_start(block: dict) -> tuple[bool, int | None]:
    """
    Returns (True, question_number) if this block starts a new question,
    (False, None) otherwise.
    """
    if block.get("type") != "text":
        return False, None
    text = block.get("text", "").strip()
    m = QUESTION_NUMBER_RE.match(text)
    if m:
        return True, int(m.group(1))
    return False, None
def is_answer_block(block: dict) -> bool:
    """True if block contains an answer line like 'Ans. (4)'."""
    if block.get("type") != "text":
        return False
    return bool(ANSWER_RE.search(block.get("text", "")))
def extract_answer(text: str) -> str | None:
    """Extract and normalize the answer letter from a text string."""
    m = ANSWER_RE.search(text)
    if not m:
        return None
    raw = m.group(1).strip()
    # Normalize: "4" → "D", "d" → "D"
    if raw in NUM_TO_LETTER:
        return NUM_TO_LETTER[raw]
    return LETTER_NORM.get(raw, raw.upper())
def split_options_text(text: str) -> dict[str, str]:
    """
    Split a text block containing inline options into a dict.
    Handles patterns like:
      "(1) foo (2) bar (3) baz (4) qux"
      "(A) foo (B) bar (C) baz (D) qux"
    Returns {} if no options found.
    """
    # Find all option positions
    positions = [(m.start(), m.group(1)) for m in OPTION_MARKER_RE.finditer(text)]
    if len(positions) < 2:
        return {}
    options: dict[str, str] = {}
    for i, (start, label) in enumerate(positions):
        # Content starts after the "(X)" marker
        content_start = start + len(f"({label})")
        content_end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        content = text[content_start:content_end].strip()
        key = NUM_TO_LETTER.get(label, LETTER_NORM.get(label, label.upper()))
        options[key] = content
    return options
def parse_latex_array_options(latex: str) -> dict[str, str]:
    r"""
    Parse a LaTeX array of options into a dict.
    Handles MinerU's spaced brace syntax (``\begin { array } { c }``) as well
    as the compact form (``\begin{array}{c}``). Also handles both the
    ``(1) text`` and ``1) text`` (no leading paren) option formats.
    Returns {} if the structure is not recognized or no options are found.
    """
    if "\\begin" not in latex:
        return {}
    inner = latex
    # Strip $$ wrappers (MinerU wraps arrays in $$...$$)
    inner = inner.replace("$$", " ")
    # Strip \begin{array}{format} — handles spaces between tokens (MinerU output)
    # e.g. "\begin { array } { c }" or "\begin{array}{cc}"
    inner = re.sub(r"\\begin\s*\{\s*array\s*\}\s*(?:\{[^}]*\})?\s*", " ", inner)
    inner = re.sub(r"\\end\s*\{\s*array\s*\}", " ", inner)
    # Replace LaTeX row separator \\ and column separator & with spaces
    # In the actual string, \\ is 2 backslashes (JSON \\\\ → Python \\)
    inner = inner.replace("\\\\", " ").replace("&", " ")
    # Strip MinerU cell wrappers {{ content }} left after array stripping.
    # These appear when equation blocks have the form: {{ (1) text }} \\\\ {{ (2) text }}
    # After removing the array frame, we're left with braces that block option parsing.
    inner = re.sub(r"\{\s*\{", " ", inner)
    inner = re.sub(r"\}\s*\}", " ", inner)
    # Try standard option format: (1), (2), (A), (B) …
    result = split_options_text(inner)
    if result:
        return result
    # Fallback: normalize "N) " → "(N) " for the no-leading-paren format
    # Use a negative lookbehind to avoid matching digits inside expressions
    normalized = re.sub(r"(?<!\()([1-4])\)\s", r"(\1) ", inner)
    return split_options_text(normalized)
def strip_latex_for_search(text: str) -> str:
    """
    Remove LaTeX markup to produce a plain-text version suitable for
    PostgreSQL full-text search. This is intentionally lossy.
    """
    # Remove display equations $$...$$
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)
    # Remove inline equations $...$
    text = re.sub(r"\$[^$]+\$", " ", text)
    # Remove LaTeX commands like \mathrm{...}
    text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    # Remove remaining braces and special chars
    text = re.sub(r"[{}\\^_]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text
def link_images_to_question(
    image_blocks: list[dict],
    images_dir: Path,
) -> list[dict]:
    """
    Convert MinerU image blocks to the Question.images format.
    Only includes images whose files actually exist on disk.
    """
    result = []
    for block in image_blocks:
        img_path = block.get("img_path", "")
        filename = Path(img_path).name
        full_path = images_dir / filename
        if full_path.exists():
            result.append({"filename": filename, "position": "stem"})
    return result
