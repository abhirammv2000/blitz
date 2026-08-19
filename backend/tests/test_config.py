"""Tests for the settings layer.

config.Settings is the single source of truth for configuration: nothing else in
the backend reads os.environ. These tests pin the behaviour that makes that safe
— environment overrides, validation of bad values, and path resolution that does
not depend on the working directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from config import Settings


def _settings(**overrides) -> Settings:
    """Build Settings without reading the developer's .env file."""
    return Settings(_env_file=None, **overrides)


def test_defaults_are_usable_without_any_configuration():
    """A fresh checkout must run with only API keys supplied."""
    s = _settings()

    assert s.primary_model
    assert s.mini_model
    assert s.request_timeout_seconds > 0
    assert s.image_cap_per_run >= 0


def test_environment_overrides_the_default(monkeypatch):
    monkeypatch.setenv("PRIMARY_MODEL", "gemini/gemini-3.6-flash")

    assert Settings(_env_file=None).primary_model == "gemini/gemini-3.6-flash"


def test_settings_are_case_insensitive(monkeypatch):
    monkeypatch.setenv("primary_model", "openai/gpt-4o-mini")

    assert Settings(_env_file=None).primary_model == "openai/gpt-4o-mini"


# ---------------------------------------------------------------------------
# Validation — a bad value should fail loudly at startup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_timeout_seconds", 0),
        ("request_timeout_seconds", -5),
        ("content_max_tokens", 0),
        ("llm_num_retries", -1),
        ("site_content_prompt_chars", 0),
        ("profile_temperature", 3.0),
        ("ads_temperature", -0.1),
    ],
)
def test_invalid_values_are_rejected(field, value):
    """Better to fail at import than twenty minutes into a pipeline run."""
    with pytest.raises(ValidationError):
        _settings(**{field: value})


def test_log_level_is_normalised():
    assert _settings(log_level="debug").log_level == "DEBUG"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_unset_cors_falls_back_to_the_dev_port_range():
    origins = _settings(cors_origins="").allowed_origins

    assert "http://localhost:5173" in origins


def test_configured_cors_replaces_the_dev_defaults():
    origins = _settings(cors_origins="https://a.com,https://b.com").allowed_origins

    assert origins == ["https://a.com", "https://b.com"]
    assert not any("localhost" in o for o in origins)


def test_cors_tolerates_whitespace_and_empty_entries():
    assert _settings(cors_origins=" https://a.com , , https://b.com ").allowed_origins == [
        "https://a.com",
        "https://b.com",
    ]


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def test_relative_paths_resolve_against_the_backend_directory():
    """Otherwise launching uvicorn from another directory silently creates a
    second, empty database and every previous run appears to vanish.
    """
    chroma = _settings(chroma_path="./chroma_data").chroma_dir

    assert chroma.is_absolute()
    assert chroma.name == "chroma_data"


def test_absolute_paths_are_left_alone():
    absolute = Path("/var/data/chroma").absolute()

    assert _settings(chroma_path=str(absolute)).chroma_dir == absolute


def test_unknown_environment_variables_are_ignored(monkeypatch):
    """Deployments carry unrelated variables; they must not break startup."""
    monkeypatch.setenv("SOME_UNRELATED_PLATFORM_VAR", "x")

    assert Settings(_env_file=None)
