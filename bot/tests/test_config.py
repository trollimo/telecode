"""Tests for config loader."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import pydantic

from bot.config import load_config, Config


class TestLoadConfig:
    """Tests for load_config()."""

    def test_loads_valid_config(self) -> None:
        """Loads a valid JSON config and returns the correct values."""
        data = {
            "telegram_token": "123:ABC",
            "allowed_user_id": 42,
            "opencode_url": "http://test:3000",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            config = load_config(path)
            assert config.telegram_token == "123:ABC"
            assert config.allowed_user_id == 42
            assert config.opencode_url == "http://test:3000"
        finally:
            path.unlink(missing_ok=True)

    def test_uses_default_opencode_url(self) -> None:
        """Defaults opencode_url to http://opencode:4096 when not in config."""
        data = {
            "telegram_token": "tok",
            "allowed_user_id": 1,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            config = load_config(path)
            assert config.opencode_url == "http://opencode:4096"
        finally:
            path.unlink(missing_ok=True)

    def test_raises_on_missing_token(self) -> None:
        """Raises ValidationError when telegram_token is missing."""
        data = {"allowed_user_id": 1}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(pydantic.ValidationError):
                load_config(path)
        finally:
            path.unlink(missing_ok=True)

    def test_raises_on_missing_user_id(self) -> None:
        """Raises ValidationError when allowed_user_id is missing."""
        data = {"telegram_token": "tok"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(pydantic.ValidationError):
                load_config(path)
        finally:
            path.unlink(missing_ok=True)

    def test_raises_on_missing_file(self) -> None:
        """Raises FileNotFoundError when config path does not exist."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/config.json"))

    def test_invalid_json_raises(self) -> None:
        """Raises JSONDecodeError for malformed JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json}")
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(json.JSONDecodeError):
                load_config(path)
        finally:
            path.unlink(missing_ok=True)

    def test_env_override_takes_precedence(self) -> None:
        """OVERRIDE_CONFIG env var changes which file is loaded."""
        data = {
            "telegram_token": "env_override_token",
            "allowed_user_id": 99,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        os.environ["OVERRIDE_CONFIG"] = str(path)
        try:
            config = load_config()
            assert config.telegram_token == "env_override_token"
            assert config.allowed_user_id == 99
        finally:
            del os.environ["OVERRIDE_CONFIG"]
            path.unlink(missing_ok=True)

    def test_config_is_frozen(self) -> None:
        """Config instances cannot be modified after creation."""
        config = Config(telegram_token="t", allowed_user_id=1)
        with pytest.raises(pydantic.ValidationError):
            config.telegram_token = "new_token"  # type: ignore[misc]
