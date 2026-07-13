from __future__ import annotations

from app.config import settings
from app.services.llm.base import LLMClient
from app.services.llm.groq_client import GroqClient
from app.services.llm.ollama_client import OllamaClient
from app.services.llm.qwen_client import QwenClient


def get_llm_client() -> LLMClient:
    """
    Factory function — returns the configured LLM client.
    Change LLM_PROVIDER in .env to switch providers. Nothing else changes.
    """
    match settings.llm_provider.lower():
        case "groq":
            return GroqClient(api_key=settings.groq_api_key, model=settings.llm_model)
        case "ollama":
            return OllamaClient(base_url=settings.ollama_base_url, model=settings.llm_model)
        case "qwen":
            return QwenClient(api_key=settings.qwen_api_key, model=settings.llm_model)
        case _:
            raise ValueError(
                f"Unknown LLM provider: {settings.llm_provider!r}. "
                "Choose from: groq, ollama, qwen"
            )


__all__ = ["LLMClient", "get_llm_client"]
