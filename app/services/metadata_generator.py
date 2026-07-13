from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.services.llm.base import LLMClient
from app.services.question_builder.base import Question, strip_latex_for_search

logger = logging.getLogger(__name__)

# ── Chapter name normalization ────────────────────────────────────────────────
# Maps LLM-generated variations to canonical NCERT chapter names.
# Extend this dict as new variations are observed in production.
_CHAPTER_ALIASES: dict[str, str] = {
    "Newton's Laws of Motion": "Laws of Motion",
    "Newton Laws": "Laws of Motion",
    "Newton's Laws": "Laws of Motion",
    "Rotational Mechanics": "Rotational Motion",
    "Rotational Dynamics": "Rotational Motion",
    "Simple Harmonic Motion": "Oscillations",
    "SHM": "Oscillations",
    "Wave Optics": "Wave Optics",
    "Ray Optics": "Ray Optics and Optical Instruments",
    "Electrostatics": "Electric Charges and Fields",
    "Gravitation": "Gravitation",
    "Work Energy Theorem": "Work, Energy and Power",
    "Work-Energy": "Work, Energy and Power",
    "Organic Chemistry": "Some Basic Principles of Organic Chemistry",
    "Chemical Equilibrium": "Equilibrium",
    "Ionic Equilibrium": "Equilibrium",
}

_METADATA_PROMPT_TEMPLATE = """\
You are a metadata tagger for {exam_name} exam questions. The subject is {subject}.

Analyze the question below and return a JSON object with these exact fields.

QUESTION:
{stem}

OPTIONS:
{options}

Return this JSON object with values filled in for THIS specific question:
{{
  "chapter": "<standard NCERT {subject} chapter name>",
  "topic": "<specific topic within that chapter>",
  "subtopic": "<narrow subtopic — REQUIRED, never null>",
  "difficulty": "<easy|medium|hard relative to {exam_name} level>",
  "question_type": "<conceptual|numerical|assertion_reason|match_the_following|statement_based>",
  "concepts": ["<concept 1>", "<concept 2>"],
  "has_formula": <true|false>,
  "has_diagram": <true|false>
}}

Rules:
- chapter: MUST be a real NCERT {subject} chapter name (e.g. for physics: "Kinematics", "Laws of Motion", "Work, Energy and Power", "Rotational Motion", "Gravitation", "Thermal Properties of Matter", "Thermodynamics", "Oscillations", "Waves", "Electric Charges and Fields", "Electrostatic Potential and Capacitance", "Current Electricity", "Moving Charges and Magnetism", "Electromagnetic Induction", "Alternating Current", "Ray Optics and Optical Instruments", "Wave Optics", "Dual Nature of Radiation and Matter", "Atoms", "Nuclei", "Semiconductor Electronics")
- topic: specific topic within the chapter (never null)
- subtopic: REQUIRED. Narrow subtopic within the topic. If no distinct subtopic exists, use the topic value itself. Never null.
- difficulty: easy/medium/hard relative to {exam_name} level
- question_type: one of the listed types
- concepts: 2 to 5 key concepts tested
- has_formula: true if a specific formula must be applied
- has_diagram: true ONLY if a physical diagram is needed to solve

Return ONLY the JSON object. No explanation.\
"""

# Used for full_paper layout: model must also identify the subject
_FULL_PAPER_PROMPT_TEMPLATE = """\
You are a metadata tagger for {exam_name} full exam papers.
This paper contains Physics, Chemistry, and Mathematics questions.
You must identify the subject of the given question.

QUESTION:
{stem}

OPTIONS:
{options}

Return this JSON object with values filled in for THIS specific question:
{{
  "subject": "<physics|chemistry|mathematics|biology>",
  "chapter": "<standard NCERT chapter name for that subject>",
  "topic": "<specific topic within that chapter>",
  "subtopic": "<narrow subtopic — REQUIRED, never null>",
  "difficulty": "<easy|medium|hard relative to {exam_name} level>",
  "question_type": "<conceptual|numerical|assertion_reason|match_the_following|statement_based>",
  "concepts": ["<concept 1>", "<concept 2>"],
  "has_formula": <true|false>,
  "has_diagram": <true|false>
}}

Rules:
- subject: identify from question content — physics (mechanics, optics, thermodynamics, electricity, magnetism, modern physics), chemistry (organic, inorganic, physical), mathematics (algebra, calculus, coordinate geometry, vectors, probability)
- chapter: standard NCERT chapter name for that subject
- topic: specific topic within the chapter (never null)
- subtopic: REQUIRED. Narrow subtopic within the topic. If no distinct subtopic exists, use the topic value itself. Never null.
- difficulty: easy/medium/hard relative to {exam_name} level
- question_type: one of the listed types
- concepts: 2 to 5 key concepts tested
- has_formula: true if a specific formula must be applied
- has_diagram: true ONLY if a physical diagram is needed to solve

Return ONLY the JSON object. No explanation.\
"""



@dataclass
class QuestionMetadata:
    chapter: str | None
    topic: str | None
    subtopic: str | None
    difficulty: str | None
    question_type: str | None
    concepts: list[str]
    has_formula: bool
    has_diagram: bool
    raw_response: dict  # The unmodified LLM JSON response
    # Subject is only populated when detect_subject=True (full_paper layout).
    # For all other layouts, subject comes from ingestion.subject.
    subject: str | None = None


async def generate_metadata(
    question: Question,
    llm: LLMClient,
    exam_name: str = "JEE Main",
    subject: str = "physics",
    detect_subject: bool = False,
) -> QuestionMetadata:
    """
    Generate metadata for a single question by calling the LLM.

    exam_name and subject are passed from the ingestion record so the model
    knows which curriculum's chapter names to use. Previously this was missing,
    causing the model to return null for chapter and topic on all questions.

    When detect_subject=True (full_paper layout), a different prompt is used
    that asks the model to IDENTIFY which subject the question belongs to
    in addition to the other metadata fields.

    Returns QuestionMetadata. Never raises — returns empty metadata on failure.
    Retries up to 3 times on transient errors with exponential backoff.
    """
    options_text = "\n".join(
        f"({k}) {v}" for k, v in (question.options or {}).items()
    ) or "(No options — integer/numerical type)"

    if detect_subject:
        prompt = _FULL_PAPER_PROMPT_TEMPLATE.format(
            stem=question.stem_md,
            options=options_text,
            exam_name=exam_name,
        )
    else:
        prompt = _METADATA_PROMPT_TEMPLATE.format(
            stem=question.stem_md,
            options=options_text,
            exam_name=exam_name,
            subject=subject,
        )

    for attempt in range(3):
        try:
            raw = await llm.generate_json(prompt)
            return _parse_metadata(raw, question)
        except Exception as exc:
            exc_str = str(exc)
            # Rate limit — wait and retry
            if "429" in exc_str or "rate_limit" in exc_str.lower():
                wait = 5 * (2 ** attempt)   # 5s, 10s, 20s
                logger.warning(
                    "Rate limit on Q%s (attempt %d/3) — waiting %ds",
                    question.question_number, attempt + 1, wait,
                )
                await asyncio.sleep(wait)
                continue
            # Other error — log and give up
            logger.warning(
                "LLM metadata generation failed for Q%s: %s",
                question.question_number, exc,
            )
            break

    return QuestionMetadata(
        chapter=None, topic=None, subtopic=None,
        difficulty=None, question_type=None,
        concepts=[], has_formula=False, has_diagram=False,
        raw_response={}, subject=None,
    )


async def generate_metadata_batch(
    questions: list[Question],
    llm: LLMClient,
    concurrency: int = 1,
    exam_name: str = "JEE Main",
    subject: str = "physics",
    detect_subject: bool = False,
) -> list[QuestionMetadata]:
    """
    Generate metadata for a list of questions.

    concurrency=1 is the default for local Ollama (single GPU, serialised).
    For cloud providers (Groq, Qwen), increase via the call site.

    exam_name and subject are passed through to every individual prompt.
    detect_subject=True is used for full_paper layout — the model identifies
    the subject from question content instead of receiving it as input.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _one(q: Question) -> QuestionMetadata:
        async with semaphore:
            return await generate_metadata(
                q, llm,
                exam_name=exam_name,
                subject=subject,
                detect_subject=detect_subject,
            )

    return await asyncio.gather(*[_one(q) for q in questions])


def _parse_metadata(raw: dict, question: Question) -> QuestionMetadata:
    """
    Parse and normalize the raw LLM response into QuestionMetadata.
    """
    def _str(key: str) -> str | None:
        v = raw.get(key)
        if v is None or str(v).strip().lower() in ("null", "none", ""):
            return None
        return str(v).strip()

    def _bool(key: str) -> bool:
        v = raw.get(key, False)
        if isinstance(v, bool):
            return v
        return str(v).lower() in ("true", "1", "yes")

    def _list(key: str) -> list[str]:
        v = raw.get(key, [])
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []

    chapter = _str("chapter")
    if chapter:
        chapter = _CHAPTER_ALIASES.get(chapter, chapter)

    # Normalize the LLM-returned subject to our canonical lowercase values
    raw_subject = _str("subject")
    subject: str | None = None
    if raw_subject:
        s = raw_subject.strip().lower()
        if any(k in s for k in ("physics", "phy")):
            subject = "physics"
        elif any(k in s for k in ("chemistry", "chem")):
            subject = "chemistry"
        elif any(k in s for k in ("math", "maths")):
            subject = "mathematics"
        elif any(k in s for k in ("biology", "bio")):
            subject = "biology"
        else:
            subject = s  # unknown — store as-is

    return QuestionMetadata(
        chapter=chapter,
        topic=_str("topic"),
        subtopic=_str("subtopic"),
        difficulty=_str("difficulty"),
        question_type=_str("question_type"),
        concepts=_list("concepts"),
        has_formula=_bool("has_formula"),
        has_diagram=_bool("has_diagram") or bool(question.images),
        raw_response=raw,
        subject=subject,
    )
