from __future__ import annotations

import json
import re

from groq import AsyncGroq


class GroqClient:
    """LLM client backed by the Groq API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    async def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,  # Low temp for consistent structured output
        )
        return response.choices[0].message.content or ""

    async def generate_json(self, prompt: str, system: str = "") -> dict:
        raw = await self.generate(prompt, system)
        return await _parse_json_with_retry(raw, prompt, system, self)


async def _parse_json_with_retry(
    raw: str,
    original_prompt: str,
    system: str,
    client: GroqClient,
) -> dict:
    """Try to parse JSON; retry once with explicit error feedback if it fails."""
    parsed = _try_parse(raw)
    if parsed is not None:
        return parsed

    # Retry: tell the LLM what went wrong
    retry_prompt = (
        f"{original_prompt}\n\n"
        f"Your previous response was not valid JSON:\n{raw[:500]}\n\n"
        "Please return ONLY a valid JSON object. No markdown, no explanation."
    )
    raw2 = await client.generate(retry_prompt, system)
    parsed2 = _try_parse(raw2)
    if parsed2 is not None:
        return parsed2

    raise ValueError(
        f"Groq returned invalid JSON after retry.\nLast response: {raw2[:500]}"
    )


def _try_parse(text: str) -> dict | None:
    """Try to parse JSON from text, stripping markdown code fences if present."""
    text = text.strip()
    # Strip ```json ... ``` fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    # Extract first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        text = brace_match.group()
    # ALWAYS repair LaTeX backslashes BEFORE parsing.
    # \text, \frac, \nabla, \rho, \beta start with valid JSON escapes (\t, \f, \n, \r, \b)
    # that json.loads() silently consumes — so waiting for JSONDecodeError is too late.
    repaired = _fix_invalid_escapes(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    # Fallback: try the original text as-is (in case repair broke something)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _fix_invalid_escapes(text: str) -> str:
    """
    Repair backslash escape sequences in a raw LLM JSON string.

    LLMs write LaTeX like \\text{m}, \\frac{a}{b}, \\theta inside JSON strings
    without doubling the backslash. This breaks JSON parsing because:
      - \\t is a tab (so \\text -> tab + 'ext')
      - \\f is a form-feed (so \\frac -> form-feed + 'rac')
      - \\n is a newline (so \\nabla -> newline + 'abla')
      - \\b is a backspace (so \\beta -> backspace + 'eta')
      - \\r is carriage-return (so \\rho -> CR + 'ho')

    Strategy:
      - Always keep \\" and \\\\ (mandatory JSON escapes)
      - Keep \\uXXXX only when followed by exactly 4 hex digits
      - Keep \\b \\f \\n \\r \\t ONLY when NOT followed by a letter
        (i.e. a real tab/newline/etc, not a LaTeX command)
      - Double-escape everything else
    """
    def _replacer(m: re.Match) -> str:
        char = m.group(1)           # character after the backslash
        pos  = m.end()              # position right after \X in `text`
        next_ch = text[pos] if pos < len(text) else ""

        # Always keep \" and \\
        if char in ('"', '\\', '/'):
            return m.group(0)

        # Keep \uXXXX only when followed by 4 hex digits
        if char == 'u' and re.match(r'[0-9a-fA-F]{4}', text[pos:pos + 4]):
            return m.group(0)

        # Keep \b \f \n \r \t ONLY when the next character is NOT a letter.
        # Real escape sequences are single-char (e.g. \t followed by space/digit/punct).
        # LaTeX commands are \t followed by a letter: \text, \theta, \frac, \rho ...
        if char in ('b', 'f', 'n', 'r', 't') and not next_ch.isalpha():
            return m.group(0)

        # Everything else: double the backslash so JSON can parse it as a literal \\
        return '\\\\' + char

    return re.sub(r'\\(.)', _replacer, text)
