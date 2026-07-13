from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol all LLM clients must satisfy.
    Adding a new provider = implement these two methods. Nothing else changes.
    """

    async def generate(self, prompt: str, system: str = "") -> str:
        """Send a prompt and return the raw text response."""
        ...

    async def generate_json(self, prompt: str, system: str = "") -> dict:
        """
        Send a prompt expecting a JSON response.
        Returns a parsed dict.
        Raises ValueError if the response cannot be parsed as JSON.
        Implementations should retry once with explicit error feedback
        before raising.
        """
        ...
