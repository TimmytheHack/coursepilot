"""Configuration helpers for optional CoursePilot integrations."""

from __future__ import annotations

import os
from typing import Optional
from pydantic import BaseModel, Field


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AppConfig(BaseModel):
    """Application-level configuration loaded from environment variables."""

    llm_enabled: bool = False
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = Field(default="claude-3-5-haiku-latest")
    anthropic_timeout_seconds: float = Field(default=15.0, gt=0)
    anthropic_max_tokens: int = Field(default=1200, gt=0)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build configuration from environment variables."""
        return cls(
            llm_enabled=_env_flag("COURSEPILOT_LLM_ENABLED", default=False),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("COURSEPILOT_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            anthropic_timeout_seconds=float(os.getenv("COURSEPILOT_ANTHROPIC_TIMEOUT_SECONDS", "15")),
            anthropic_max_tokens=int(os.getenv("COURSEPILOT_ANTHROPIC_MAX_TOKENS", "1200")),
        )
