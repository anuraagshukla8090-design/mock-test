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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
