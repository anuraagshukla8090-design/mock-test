from __future__ import annotations

import json
import re

import httpx


class OllamaClient:
    """LLM client backed by a local Ollama instance."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def generate(self, prompt: str, system: str = "") -> str:
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("response", "")

    async def generate_json(self, prompt: str, system: str = "") -> dict:
        """
        Request JSON output using Ollama's native format mode.

        Setting `format: "json"` instructs Ollama to constrain token
        sampling so the model can only produce valid JSON. This is
        significantly more reliable than post-hoc regex parsing and
        eliminates most retry scenarios.

        The prompt still asks for JSON explicitly as belt-and-suspenders.
        """
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",          # ← native JSON mode
            "options": {"temperature": 0.1},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")

        # format=json guarantees valid JSON from Ollama, but still parse
        # defensively in case the model wraps it in markdown fences.
        parsed = _try_parse(raw)
        if parsed is not None:
            return parsed

        # Fallback: retry without format constraint (shouldn't be needed)
        retry_prompt = (
            f"{prompt}\n\nReturn ONLY a valid JSON object. No markdown, no explanation."
        )
        payload2 = {**payload, "prompt": retry_prompt}
        async with httpx.AsyncClient(timeout=300.0) as client:
            response2 = await client.post(
                f"{self._base_url}/api/generate",
                json=payload2,
            )
            response2.raise_for_status()
            raw2 = response2.json().get("response", "")

        parsed2 = _try_parse(raw2)
        if parsed2 is not None:
            return parsed2

        raise ValueError(f"Ollama returned invalid JSON after retry.\nLast: {raw2[:400]}")


def _try_parse(text: str) -> dict | None:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
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
    without doubling the backslash. This causes:
      - \\text  -> tab + 'ext'         (\\t = tab in JSON)
      - \\frac  -> form-feed + 'rac'   (\\f = form-feed in JSON)
      - \\nabla -> newline + 'abla'    (\\n = newline in JSON)
      - \\beta  -> backspace + 'eta'   (\\b = backspace in JSON)
      - \\rho   -> CR + 'ho'           (\\r = carriage-return in JSON)

    Strategy:
      - Always keep \\" and \\\\ (mandatory JSON escapes)
      - Keep \\uXXXX only when followed by exactly 4 hex digits
      - Keep \\b \\f \\n \\r \\t ONLY when NOT followed by a letter
        (real whitespace escapes are standalone; LaTeX commands have letters after)
      - Double-escape everything else
    """
    def _replacer(m: re.Match) -> str:
        char = m.group(1)
        pos = m.end()
        next_ch = text[pos] if pos < len(text) else ""

        # Always keep \" and \\
        if char in ('"', '\\', '/'):
            return m.group(0)

        # Keep \uXXXX only when followed by 4 hex digits
        if char == 'u' and re.match(r'[0-9a-fA-F]{4}', text[pos:pos + 4]):
            return m.group(0)

        # Keep \b \f \n \r \t as real JSON escapes ONLY when NOT followed by a letter.
        # \text, \frac, \theta, \rho, \nabla, \beta all have a letter after the char.
        if char in ('b', 'f', 'n', 'r', 't') and not next_ch.isalpha():
            return m.group(0)

        # Double the backslash so JSON parses it as a literal backslash
        return '\\\\' + char

    return re.sub(r'\\(.)', _replacer, text)
