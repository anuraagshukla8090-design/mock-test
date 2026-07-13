from __future__ import annotations

from pathlib import Path

from app.services.question_builder.abstract_builder import AbstractBuilder
from app.services.question_builder.base import Question
from app.services.question_builder.inline_answer import InlineAnswerBuilder
from app.services.question_builder.separate_answer_key import SeparateAnswerKeyBuilder
from app.services.question_builder.with_solution import WithSolutionBuilder
from app.services.question_builder.full_paper import FullPaperBuilder

# ── Layout registry ───────────────────────────────────────────────────────────
# Maps the layout_type string (from the upload form) to the builder class.
# To add a new layout: create a builder file, import it here, add one entry.
LAYOUT_REGISTRY: dict[str, type[AbstractBuilder]] = {
    "inline_answer":       InlineAnswerBuilder,
    "separate_answer_key": SeparateAnswerKeyBuilder,
    "with_solution":       WithSolutionBuilder,
    "full_paper":          FullPaperBuilder,
}

# Human-readable labels for the upload form dropdown
LAYOUT_LABELS: dict[str, str] = {
    "inline_answer":       "Inline Answer (Q + Options + Ans on same page)",
    "separate_answer_key": "Answer Key at End (answers grouped on last page)",
    "with_solution":       "Question + Detailed Solution [not yet implemented]",
    "full_paper":          "Full Paper (JEE Main / NEET — multi-subject, answer key at end)",
}

VALID_LAYOUT_TYPES: list[str] = list(LAYOUT_REGISTRY.keys())


def build_questions(
    blocks: list[dict],
    images_dir: Path,
    layout_type: str,
) -> tuple[list[Question], str]:
    """
    Dispatch content blocks to the correct QuestionBuilder.

    Args:
        blocks:      Cleaned MinerU content blocks.
        images_dir:  Path to MinerU's images/ directory.
        layout_type: One of the keys in LAYOUT_REGISTRY.
                     Required — no auto-detection, no fallback.

    Returns:
        (questions, builder_class_name)

    Raises:
        ValueError: if layout_type is not in LAYOUT_REGISTRY.
        NotImplementedError: if the selected builder is not yet implemented.
    """
    builder_class = LAYOUT_REGISTRY.get(layout_type)
    if builder_class is None:
        raise ValueError(
            f"Unknown layout_type: '{layout_type}'. "
            f"Valid values are: {VALID_LAYOUT_TYPES}"
        )

    builder = builder_class(blocks, images_dir)
    questions = builder.build()  # may raise NotImplementedError for placeholders

    # Always sort by question_number for consistent ordering
    questions.sort(key=lambda q: q.question_number or 0)

    return questions, builder_class.__name__


def available_layouts() -> dict[str, str]:
    """Return all registered layout_type keys with their human-readable labels."""
    return dict(LAYOUT_LABELS)
