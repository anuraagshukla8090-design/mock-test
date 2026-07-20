"""
Question Regeneration Service.

Generates a new question variant from an existing one using either local Ollama
or Groq, selectable per-request. The regenerated question changes numerical values,
contextual parameters, and wording while preserving the same concept, difficulty
level, and question structure.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Literal

from app.config import settings

if TYPE_CHECKING:
    from app.models.question import Question

logger = logging.getLogger(__name__)

ProviderLiteral = Literal["ollama", "groq"]

_SYSTEM_PROMPT = """\
You are a subject-matter expert and question-paper creator for JEE/NEET/competitive exams.
You will create a VARIANT of a given question that tests the SAME concept, but with DIFFERENT
numerical values, substances, or contextual details.

CRITICAL PROCESS — follow these steps in order:

STEP 1 — DESIGN the new question:
  - Keep the same concept, formula, and structure as the original.
  - Change numbers, substances, or context significantly (not just ±10%).
  - Ensure the new scenario is physically/chemically realistic.

STEP 2 — SOLVE the new question completely:
  - Work through the calculation step-by-step.
  - Arrive at the CORRECT answer before writing any options.
  - Double-check your arithmetic.

STEP 3 — WRITE the options (MCQ only):
  - Option A/B/C/D: exactly ONE must be correct (your solved answer).
  - The other 3 must be PLAUSIBLE WRONG answers from common student errors, e.g.:
      • Forgot to square a value
      • Used wrong unit conversion factor
      • Applied formula to wrong quantity
      • Made a sign error
      • Used approximation incorrectly
  - Do NOT just copy or slightly tweak the original options.

SUBJECT-SPECIFIC VALIDITY RULES:

CHEMISTRY:
  - Only use REAL chemical substances with valid molecular formulas.
  - All chemical equations must be balanced.
  - Molar masses, bond energies, lattice energies must be realistic.
  - Do NOT invent non-existent compounds (e.g., "XeCl8" is invalid).
  - Thermodynamic values (ΔH, ΔG, Kp) must be physically plausible.

PHYSICS:
  - All quantities must have consistent SI units.
  - No physically impossible values (e.g., speed > c, negative mass, negative absolute temperature).
  - Use standard physical constants: g = 9.8 m/s², c = 3×10⁸ m/s, etc.
  - Check significant figures and order-of-magnitude reasonableness.

MATHEMATICS:
  - Verify the answer algebraically or numerically before writing it.
  - Ensure discriminants, domains, and ranges are valid.
  - Integer-type answers should be non-negative integers ≤ 9999.

FORMATTING:
  - All LaTeX: use $...$ for inline math, $$...$$ for display math.
  - Do NOT start the stem with a question number (e.g., no "54." or "Q1.").
  - Do NOT add explanation text outside the JSON.

CRITICAL JSON RULE \u2014 LaTeX backslashes MUST be doubled in JSON strings:
  - Write \\\\frac{a}{b}    NOT \\frac{a}{b}
  - Write \\\\text{m/s}     NOT \\text{m/s}
  - Write \\\\theta          NOT \\theta
  - Write \\\\mathrm{kg}    NOT \\mathrm{kg}
  - Write \\\\times          NOT \\times
  - Write \\\\rho            NOT \\rho
  - Write \\\\beta           NOT \\beta
  - Write \\\\nabla          NOT \\nabla
  In JSON, a single backslash (\\) is an escape character. Every LaTeX backslash
  must be written as \\\\\\\\ so it appears as \\\\ in the final string.

OUTPUT FORMAT \u2014 return ONLY this JSON object, nothing else:
{
  "reasoning": "<your step-by-step solution here>",
  "stem_md": "<question text with LaTeX>",
  "options": {"A": "<option>", "B": "<option>", "C": "<option>", "D": "<option>"},
  "answer": "<A or B or C or D>"
}
For integer-type questions, use: {"reasoning": "...", "stem_md": "...", "options": {}, "answer": "<integer>"}
"""


def _build_prompt(question: "Question") -> str:
    """Build a tailored regeneration prompt based on section_type."""
    subject = (question.subject or "").lower()
    meta = (
        f"Subject: {question.subject or 'N/A'}\n"
        f"Chapter: {question.chapter or 'N/A'}\n"
        f"Topic: {question.topic or 'N/A'}\n"
        f"Difficulty: {question.difficulty or 'N/A'}\n"
        f"Section Type: {question.section_type}\n"
    )

    original_block = f"ORIGINAL QUESTION STEM:\n{question.stem_md}\n"

    if question.section_type == "mcq" and question.options:
        options_text = "\n".join(
            f"  {k}: {v}" for k, v in question.options.items()
        )
        original_block += f"\nORIGINAL OPTIONS:\n{options_text}\n"
        original_block += f"\nCORRECT ANSWER: {question.answer}\n"

        task = (
            "Create a NEW MCQ question on the same concept with different values/substances/context.\n"
            "Follow the 3-step process: (1) Design the new scenario, (2) SOLVE it completely to find "
            "the correct answer, (3) Write 4 options where only ONE matches your solved answer and the "
            "other 3 are plausible wrong answers from common errors.\n"
            "Return JSON: {\"reasoning\": \"...\", \"stem_md\": \"...\", "
            "\"options\": {\"A\": \"...\", \"B\": \"...\", \"C\": \"...\", \"D\": \"...\"},"
            " \"answer\": \"<A/B/C/D>\"}"
        )
    elif question.section_type in ("integer", "numerical"):
        original_block += f"\nCORRECT ANSWER: {question.answer}\n"
        task = (
            "Create a NEW integer-type question on the same concept with different values.\n"
            "Follow the 3-step process: (1) Design the new scenario, (2) SOLVE it completely, "
            "(3) Write only the final integer answer.\n"
            "Return JSON: {\"reasoning\": \"...\", \"stem_md\": \"...\", "
            "\"options\": {}, \"answer\": \"<integer>\"}"
        )
    else:
        if question.options:
            options_text = "\n".join(
                f"  {k}: {v}" for k, v in question.options.items()
            )
            original_block += f"\nORIGINAL OPTIONS:\n{options_text}\n"
        original_block += f"\nCORRECT ANSWER: {question.answer}\n"
        task = (
            "Create a NEW question on the same concept with different items/values/context.\n"
            "Solve it first to verify the correct answer.\n"
            "Return JSON: {\"reasoning\": \"...\", \"stem_md\": \"...\", "
            "\"options\": {...}, \"answer\": \"...\"}"
        )

    # Add subject-specific reminder
    subject_note = ""
    if "chem" in subject:
        subject_note = (
            "\nREMINDER (Chemistry): Use only real compounds with valid formulas. "
            "Balance all equations. Check molar masses and thermodynamic values are realistic."
        )
    elif "phys" in subject:
        subject_note = (
            "\nREMINDER (Physics): Verify units are consistent throughout. "
            "Check that all values are physically realistic (no speeds > c, no negative masses)."
        )
    elif "math" in subject:
        subject_note = (
            "\nREMINDER (Mathematics): Verify your answer algebraically. "
            "Check domain/range validity and that discriminants are non-negative where required."
        )

    prompt = (
        f"{meta}\n"
        f"{original_block}\n"
        f"TASK: {task}{subject_note}\n\n"
        "IMPORTANT: Return ONLY a valid JSON object. No markdown fences, no extra text."
    )
    return prompt


def _get_client(provider: ProviderLiteral):
    """Return the appropriate LLM client for regeneration."""
    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is not set in .env. "
                "Add it or switch the provider to Ollama."
            )
        from app.services.llm.groq_client import GroqClient
        return GroqClient(api_key=settings.groq_api_key, model=settings.regen_groq_model)

    # Default: ollama
    from app.services.llm.ollama_client import OllamaClient
    return OllamaClient(base_url=settings.ollama_base_url, model=settings.regen_ollama_model)


async def regenerate_question(
    question: "Question",
    provider: ProviderLiteral | None = None,
) -> dict:
    """
    Generate a new question variant from an existing question.

    Args:
        question:  The original Question ORM object to use as the seed.
        provider:  "ollama" or "groq". Defaults to settings.regen_provider.

    Returns:
        A dict with keys: stem_md, options, answer, section_type, provider_used

    Raises:
        ValueError: If the provider has a config issue or LLM returns bad JSON.
        httpx.HTTPError: If Ollama is unreachable.
        groq.APIError: If Groq API fails.
    """
    effective_provider: ProviderLiteral = (provider or settings.regen_provider).lower()  # type: ignore[assignment]
    if effective_provider not in ("ollama", "groq"):
        effective_provider = "ollama"

    client = _get_client(effective_provider)
    prompt = _build_prompt(question)

    model_name = (
        settings.regen_groq_model if effective_provider == "groq"
        else settings.regen_ollama_model
    )
    logger.info(
        "Regenerating question %s (subject=%s, chapter=%s, type=%s) via %s model=%s",
        question.id,
        question.subject,
        question.chapter,
        question.section_type,
        effective_provider,
        model_name,
    )

    result = await client.generate_json(prompt=prompt, system=_SYSTEM_PROMPT)

    # Validate required keys
    if "stem_md" not in result:
        raise ValueError(f"LLM response missing 'stem_md' key. Got: {result}")
    if "answer" not in result:
        raise ValueError(f"LLM response missing 'answer' key. Got: {result}")

    # Strip the reasoning field — it was only used to force the LLM to solve first.
    # We don't persist or show it to the teacher.
    result.pop("reasoning", None)

    # Post-process: wrap bare LaTeX commands in $...$ so the renderer can display them.
    stem = _wrap_bare_latex(str(result.get("stem_md", "")).strip())
    raw_options = result.get("options") or {}
    fixed_options = {k: _wrap_bare_latex(str(v)) for k, v in raw_options.items()}
    answer = str(result.get("answer", "")).strip()

    return {
        "stem_md": stem,
        "options": fixed_options,
        "answer": answer,
        "section_type": question.section_type,
        "provider_used": effective_provider,
    }


# Regex to match bare LaTeX commands outside $...$ delimiters.
# Matches: \command optionally followed by {arg}, ^{sup}, _{sub}, or single digit sup/sub.
_BARE_LATEX_RE = re.compile(
    r"(\\(?:text|frac|dfrac|mathrm|mathbf|mathit|sqrt|times|div|cdot|pm|mp"
    r"|alpha|beta|gamma|delta|theta|phi|psi|omega|lambda|mu|nu|rho"
    r"|sigma|tau|pi|epsilon|zeta|eta|kappa|xi|chi"
    r"|Delta|Gamma|Sigma|Omega|Lambda|Pi|Theta|Phi|Psi"
    r"|nabla|infty|partial|hbar"
    r"|int|oint|sum|prod|lim|log|ln|sin|cos|tan|cot|sec|csc"
    r"|vec|hat|bar|dot|ddot|tilde|overline|underline"
    r"|rightarrow|leftarrow|Rightarrow|Leftarrow|leftrightarrow"
    r"|le|ge|neq|approx|equiv|propto|sim|simeq|cong"
    r"|circ|bullet|star|dagger|perp|parallel"
    r"|left|right|big|Big|bigg|Bigg)"
    r"(?:\{[^}]*\})*"          # zero or more {braced args}
    r"(?:[\^_]\{[^}]*\})*"    # zero or more ^{sup} or _{sub}
    r"(?:[\^_][0-9])*"         # zero or more ^2 _1 (bare digit)
    r")"
)


def _wrap_bare_latex(text: str) -> str:
    """
    Wrap bare LaTeX commands not inside $...$ with $ delimiters.

    Strategy: split on existing $ delimiters; segments at even indices are
    outside math mode and may contain unwrapped LaTeX commands.

    Example: '3.75 \\text{ m/s}^2'  ->  '3.75 $\\text{ m/s}^2$'
    Unchanged: '$\\frac{a}{b}$'       ->  '$\\frac{a}{b}$'
    Unchanged: 'plain text'           ->  'plain text'
    """
    if not text or "\\" not in text:
        return text

    # Split on $ so we can identify math vs. non-math segments.
    # Even-indexed parts are outside $, odd-indexed are inside $.
    parts = text.split("$")
    result: list[str] = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            # Already inside $...$  — restore delimiter and leave as-is
            result.append("$" + part + "$")
        else:
            # Outside $...$  — wrap any bare \command sequences
            wrapped = _BARE_LATEX_RE.sub(lambda m: "$" + m.group(0) + "$", part)
            result.append(wrapped)

    # The split/join dance adds an extra trailing $ for each pair;
    # a string with N dollar signs produces N+1 parts, so rejoining
    # with the above logic is correct as long as $ count is even.
    # If odd (malformed), just return original to avoid corruption.
    dollar_count = text.count("$")
    if dollar_count % 2 != 0:
        return text

    return "".join(result)
