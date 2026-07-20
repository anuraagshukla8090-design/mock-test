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
    # First attempt: parse as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Second attempt: repair invalid LaTeX backslash escapes (\mathrm, \frac, etc.)
    repaired = re.sub(r'\\(?!["\\\'\/bfnrtu])', r'\\\\', text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None
