"""
Compatibility layer for legacy `app.core.config.settings` usage.

This module provides a small `settings` object for modules that import
`from app.core.config import settings` in the original codebase.

It centralizes a few environment variables used by diagram generation.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()
    # Provider-specific keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: Optional[str] = os.getenv("OPENAI_MODEL")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL")
    NVIDIA_API_KEY: Optional[str] = os.getenv("NVIDIA_API_KEY")
    NVIDIA_MODEL: Optional[str] = os.getenv("NVIDIA_MODEL")
    NVIDIA_BASE_URL: Optional[str] = os.getenv("NVIDIA_BASE_URL")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: Optional[str] = os.getenv("GEMINI_MODEL")

    # Max tokens used across LLM calls (defaults to 1024)
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))

    # PlantUML server URL for WBS rendering (defaults to plantuml.com)
    PLANTUML_SERVER_URL: str = os.getenv("PLANTUML_SERVER_URL", "https://www.plantuml.com/plantuml")


# Create a module-level settings instance for ease of import
settings = Settings()
