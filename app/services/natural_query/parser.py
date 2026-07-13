"""
Stage 1 — NaturalQueryParser

Calls the LLM, receives a JSON response, and returns a RawBlueprint.
Has exactly one responsibility: translate a natural language string to
a structured (but not yet validated) blueprint object.
"""
from __future__ import annotations

import json
import re

from app.services.llm import get_llm_client
from app.services.natural_query.exceptions import NaturalQueryParseError
from app.services.natural_query.schemas import RawBlueprint
from app.constants.exams import normalize_exam_name, normalize_subject

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM = (
    "You are a query parser for an exam question bank system. "
    "Given a teacher's natural language request, extract the query parameters "
    "as a JSON object. Return ONLY the JSON — no explanation, no markdown fences."
)

# ── Few-shot prompt template ──────────────────────────────────────────────────
_PROMPT_TEMPLATE = """\
Teacher request: "{prompt}"

Return a JSON object matching this schema exactly:
{{
  "exam_name": "JEE Main",
  "subject": "physics",
  "chapter_filter_mode": "upto",
  "chapter": null,
  "chapter_upto": "Rotational Motion",
  "chapter_from": null,
  "chapter_to": null,
  "chapter_after": null,
  "exclude_chapters": [],
  "question_count": 30,
  "difficulty": null,
  "difficulty_distribution": null,
  "question_type": null,
  "section_type": null,
  "has_formula": null,
  "has_diagram": null,
  "concepts": [],
  "concept_match_mode": "any"
}}

Rules:
- exam_name: "JEE Main", "NEET", or "CUET". Default "JEE Main".
- subject: "physics", "chemistry", "mathematics", or "biology". Lowercase only.
- chapter_filter_mode must be exactly one of: "exact", "upto", "from", "between", "after", "all"
  * "upto"    = all chapters UP TO AND INCLUDING the named chapter ("till X", "up to X")
  * "after"   = all chapters AFTER the named one, exclusive ("after X")
  * "from"    = from a chapter onwards ("from X onwards", "starting from X")
  * "between" = from chapter_from to chapter_to, both inclusive ("from X to Y")
  * "exact"   = one specific chapter only ("only from X", "just X")
  * "all"     = no chapter filter (use when no chapter is mentioned)
- IMPORTANT: If the teacher does NOT mention a specific chapter name, ALWAYS use chapter_filter_mode="all". Never use "upto", "from", "exact", "after", or "between" unless the teacher explicitly names a chapter.
- Set ONLY the chapter field that matches the mode. All others must be null.
- exclude_chapters: list of chapter names to exclude (e.g. ["Kinematics"])
- question_count: integer 1-200. Default 30.
- difficulty: "easy", "medium", "hard", or null (if not mentioned).
- difficulty_distribution: dict if explicit split given (e.g. "10 easy, 15 medium, 5 hard"),
  otherwise null. Values must sum to question_count.
- question_type: "conceptual", "numerical", "assertion_reason", "match_the_following",
  "statement_based", or null.
- section_type: "mcq", "integer", or null.
- has_formula: true/false/null. True for "formula-based", "formula questions".
- has_diagram: true/false/null. True for "with diagrams", "diagram questions".
- concepts: list of concept strings if teacher mentions specific concepts. Usually [].
- concept_match_mode: always "any" in V1.

Use common chapter name abbreviations from the teacher's vocabulary; the backend resolves them.
"""


class NaturalQueryParser:
    """Translates a teacher's natural language query into a RawBlueprint."""

    async def parse(self, prompt: str) -> RawBlueprint:
        """
        Calls the LLM and returns a RawBlueprint.

        Raises:
            NaturalQueryParseError: if LLM returns invalid JSON or
                                    if required fields are missing/wrong type.
        """
        client = get_llm_client()
        formatted_prompt = _PROMPT_TEMPLATE.format(prompt=prompt.replace('"', "'"))

        try:
            raw = await client.generate_json(formatted_prompt, system=_SYSTEM)
        except (ValueError, json.JSONDecodeError) as exc:
            raise NaturalQueryParseError(
                detail=f"LLM returned invalid JSON: {exc}",
                raw_response=str(exc),
            ) from exc

        # Normalize exam_name and subject before Pydantic validation.
        # The LLM might return "jee mains", "maths", etc.
        if "exam_name" in raw and raw["exam_name"]:
            raw["exam_name"] = normalize_exam_name(str(raw["exam_name"])) or raw["exam_name"]
        if "subject" in raw and raw["subject"]:
            raw["subject"] = normalize_subject(str(raw["subject"])) or raw["subject"]

        # Defensive normalization: if the LLM set a chapter_filter_mode but
        # forgot to fill the companion field, fall back to "all" so Pydantic
        # validation never sees an inconsistent state.
        mode = raw.get("chapter_filter_mode", "all")
        _companion = {
            "upto":    "chapter_upto",
            "exact":   "chapter",
            "from":    "chapter_from",
            "after":   "chapter_after",
            "between": "chapter_from",  # between needs both; check from only
        }
        if mode in _companion:
            companion_key = _companion[mode]
            companion_val = raw.get(companion_key)
            if not companion_val or str(companion_val).strip().lower() in ("null", "none", ""):
                raw["chapter_filter_mode"] = "all"

        # Validate and coerce via Pydantic
        try:
            blueprint = RawBlueprint.model_validate(raw)
        except Exception as exc:
            raise NaturalQueryParseError(
                detail=f"Blueprint fields invalid: {exc}",
                raw_response=json.dumps(raw),
            ) from exc

        return blueprint
