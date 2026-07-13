from __future__ import annotations

from pathlib import Path

from app.services.question_builder.abstract_builder import AbstractBuilder
from app.services.question_builder.base import Question


class WithSolutionBuilder(AbstractBuilder):
    """
    Placeholder for PDFs with format: Question + Options + Detailed Solution.
    Not implemented in V1.
    """

    def build(self) -> list[Question]:
        raise NotImplementedError(
            "WithSolutionBuilder is not yet implemented. "
            "Use layout_type='inline_answer' or 'separate_answer_key' instead."
        )

    @classmethod
    def can_handle(cls, blocks: list[dict]) -> bool:
        return False
