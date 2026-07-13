from __future__ import annotations

import json
import re

import httpx


class QwenClient:
    """LLM client backed by Alibaba Cloud Qwen API (OpenAI-compatible endpoint)."""

    _API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self._API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def generate_json(self, prompt: str, system: str = "") -> dict:
        raw = await self.generate(prompt, system)
        parsed = _try_parse(raw)
        if parsed is not None:
            return parsed

        retry_prompt = (
            f"{prompt}\n\nYour previous response was not valid JSON:\n{raw[:400]}\n\n"
            "Return ONLY a JSON object. No markdown, no explanation."
        )
        raw2 = await self.generate(retry_prompt, system)
        parsed2 = _try_parse(raw2)
        if parsed2 is not None:
            return parsed2

        raise ValueError(f"Qwen returned invalid JSON after retry.\nLast: {raw2[:400]}")


def _try_parse(text: str) -> dict | None:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        text = brace_match.group()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
