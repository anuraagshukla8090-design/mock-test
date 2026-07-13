"""
All exception types for the natural query pipeline.

Each exception maps to a specific pipeline stage and HTTP status code.
The orchestrator (pipeline.py) catches these and converts them to
FastAPI HTTP responses with human-readable detail messages.
"""
from __future__ import annotations


class NaturalQueryError(Exception):
    """Base class. All subclasses carry an http_status."""
    http_status: int = 422
    user_message: str = "Natural query processing failed."


class NaturalQueryParseError(NaturalQueryError):
    """
    Stage: NaturalQueryParser.
    Raised when the LLM returns malformed JSON or missing required fields.
    """
    http_status = 422

    def __init__(self, detail: str, raw_response: str = "") -> None:
        self.detail = detail
        self.raw_response = raw_response
        super().__init__(detail)

    @property
    def user_message(self) -> str:
        return (
            f"Could not parse your query: {self.detail}. "
            "Try phrasing like: 'Generate 30 JEE Main Physics questions "
            "till Rotational Motion'."
        )


class BlueprintValidationError(NaturalQueryError):
    """
    Stage: BlueprintValidator.
    Raised when the blueprint has inconsistent or invalid fields.
    """
    http_status = 422

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")

    @property
    def user_message(self) -> str:
        return f"Invalid query parameter '{self.field}': {self.reason}"


class SyllabusNotFoundError(NaturalQueryError):
    """
    Stage: SyllabusResolver.
    Raised when the syllabus table has no rows for the given exam+subject.
    """
    http_status = 422

    def __init__(self, exam_name: str, subject: str) -> None:
        self.exam_name = exam_name
        self.subject = subject
        super().__init__(f"No syllabus for {exam_name} / {subject}")

    @property
    def user_message(self) -> str:
        return (
            f"No syllabus defined for '{self.exam_name}' / '{self.subject}'. "
            "Supported: JEE Main (physics, chemistry, mathematics), "
            "NEET (physics, chemistry, biology)."
        )


class ChapterNotFoundError(NaturalQueryError):
    """
    Stage: SyllabusResolver._resolve_chapter_name().
    Raised when Exact + Alias + RapidFuzz all fail to match the chapter.
    """
    http_status = 422

    def __init__(
        self,
        chapter_name: str,
        exam_name: str,
        subject: str,
        available_chapters: list[str],
    ) -> None:
        self.chapter_name = chapter_name
        self.exam_name = exam_name
        self.subject = subject
        self.suggestions = available_chapters[:8]
        super().__init__(
            f"Chapter '{chapter_name}' not found in {exam_name} {subject}"
        )

    @property
    def user_message(self) -> str:
        suggestions = ", ".join(f"'{s}'" for s in self.suggestions)
        return (
            f"Chapter '{self.chapter_name}' not found in "
            f"{self.exam_name} {self.subject} syllabus. "
            f"Did you mean one of: {suggestions}?"
        )


class EmptyRangeError(NaturalQueryError):
    """
    Stage: SyllabusResolver.
    The filter mode produced zero chapters after applying inclusions/exclusions.
    """
    http_status = 422

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)

    @property
    def user_message(self) -> str:
        return f"Chapter filter produced no chapters: {self.reason}"


class InsufficientQuestionsError(NaturalQueryError):
    """
    Stage: QuestionSelector.
    Not enough questions in the DB to satisfy the request.
    This returns HTTP 200 with can_generate=False — it is NOT a server error.
    """
    http_status = 200  # intentionally not 4xx — pipeline succeeds, DB is just sparse

    def __init__(self, requested: int, available: int) -> None:
        self.requested = requested
        self.available = available
        super().__init__(
            f"Requested {requested} questions but only {available} available"
        )

    @property
    def user_message(self) -> str:
        return (
            f"Only {self.available} questions are available for this filter "
            f"(you requested {self.requested}). "
            "Try broadening the chapter range or reducing the question count."
        )
