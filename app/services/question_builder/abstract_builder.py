from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from app.services.question_builder.base import Question


class AbstractBuilder(ABC):
    """
    Base class for all PDF layout parsers.

    To add a new layout:
      1. Create a new file in question_builder/ (e.g. separate_key.py)
      2. Subclass AbstractBuilder
      3. Implement build() and can_handle()
      4. Register it in registry.py

    That's it. Nothing else changes.
    """

    def __init__(self, blocks: list[dict], images_dir: Path) -> None:
        self.blocks = blocks
        self.images_dir = images_dir

    @abstractmethod
    def build(self) -> list[Question]:
        """
        Parse self.blocks into Question objects.
        Must return an empty list (never raise) if no questions are found.
        """
        ...

    @classmethod
    def can_handle(cls, blocks: list[dict]) -> bool:
        """
        Return True if this builder is appropriate for the given blocks.
        Used by the registry for auto-detection.
        Default: False (opt-in detection per builder).
        """
        return False
