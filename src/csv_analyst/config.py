"""
Configuration management for CSV Analyst.

Loads settings from environment variables with sensible defaults.
Uses python-dotenv to load a .env file if present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

# Load .env from project root or current directory
load_dotenv(find_dotenv(usecwd=True))


def _env(key: str, default: str) -> str:
    """Get an environment variable with a fallback default."""
    return os.environ.get(key, default)


@dataclass
class Config:
    """Central configuration for the CSV Analyst agent."""

    # DeepSeek / LLM settings
    deepseek_api_key: str = field(
        default_factory=lambda: _env("DEEPSEEK_API_KEY", "")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    )
    deepseek_model: str = field(
        default_factory=lambda: _env("DEEPSEEK_MODEL", "deepseek-chat")
    )
    deepseek_max_tokens: int = field(
        default_factory=lambda: int(_env("DEEPSEEK_MAX_TOKENS", "4096"))
    )
    deepseek_temperature: float = field(
        default_factory=lambda: float(_env("DEEPSEEK_TEMPERATURE", "0.3"))
    )

    # Output settings
    charts_dir: str = field(
        default_factory=lambda: _env("CSV_ANALYST_CHARTS_DIR", "./charts")
    )

    # Analysis limits
    max_sample_rows: int = field(
        default_factory=lambda: int(_env("CSV_ANALYST_MAX_SAMPLE_ROWS", "50"))
    )

    @property
    def is_api_key_set(self) -> bool:
        """Check whether the API key has been configured."""
        return bool(self.deepseek_api_key) and self.deepseek_api_key != ""


# Global config singleton
config = Config()
