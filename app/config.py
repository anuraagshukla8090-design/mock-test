from __future__ import annotations

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = directory containing this file's parent (app/../)
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:password@localhost:5432/questionbank"

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = "groq"            # "groq" | "ollama" | "qwen"
    llm_model: str = "llama-3.3-70b-versatile"

    groq_api_key: str = ""
    qwen_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # ── MinerU ────────────────────────────────────────────────────────────────
    # Set MINERU_PYTHON in .env — no default because the path is machine-specific.
    mineru_python: str = ""
    mineru_script: str = str(_PROJECT_ROOT / "scripts" / "run_mineru_single.py")

    # ── Storage ───────────────────────────────────────────────────────────────
    # Defaults to <project_root>/storage so the app works out-of-the-box
    # without any configuration. Override via STORAGE_DIR in .env.
    storage_dir: str = str(_PROJECT_ROOT / "storage")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _validate_paths(self) -> "Settings":
        """
        Validate that required paths exist at startup.
        Fail fast rather than failing mid-request during an ingestion.
        """
        if not self.mineru_python:
            # Only raise if someone actually tries to ingest — checked at
            # runtime in mineru_runner.py so a missing value doesn't break
            # endpoints that don't use MinerU.
            pass  # deferred — validated in mineru_runner on first use

        script_path = Path(self.mineru_script)
        if not script_path.exists():
            import logging
            logging.getLogger(__name__).warning(
                "MINERU_SCRIPT not found at %s — ingestion will fail until resolved.",
                script_path,
            )

        return self


# Singleton — import this everywhere
settings = Settings()
