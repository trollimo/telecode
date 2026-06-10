"""Configuration loader for the Telegram bot."""

import json
import os
from pathlib import Path
from typing import Optional

import pydantic


class Config(pydantic.BaseModel):
    """Application configuration loaded from JSON file."""

    telegram_token: str
    allowed_user_id: int
    opencode_url: str = "http://opencode:4096"

    model_config = pydantic.ConfigDict(frozen=True)


def _default_config_path() -> Path:
    """Resolve config path: env var OVERRIDE_CONFIG → ~/.rem-opencode/config.json."""
    env_override = os.environ.get("OVERRIDE_CONFIG")
    if env_override:
        return Path(env_override)
    return Path.home() / ".rem-opencode" / "config.json"


def load_config(path: Optional[Path] = None) -> Config:
    """Load and validate configuration from a JSON file.

    Args:
        path: Path to config JSON. Defaults to ~/.rem-opencode/config.json.

    Returns:
        Validated Config instance.

    Raises:
        FileNotFoundError: If config file does not exist.
        json.JSONDecodeError: If config is not valid JSON.
        pydantic.ValidationError: If required fields are missing or invalid.
    """
    config_path = path or _default_config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Create it with:\n"
            '{"telegram_token": "...", "allowed_user_id": 123}\n'
            f"Or set OVERRIDE_CONFIG env var to a different path."
        )
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config(**data)
