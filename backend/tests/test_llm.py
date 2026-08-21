"""Tests for the router setup and error messages in llm.py.

Covers two bugs we hit: timeouts showing up in the UI as a blank error, and the
router handing an OpenAI key to a Gemini model when PRIMARY_MODEL was changed.
"""

from __future__ import annotations

import asyncio

import pytest

import app.core.llm as llm


@pytest.fixture(autouse=True)
def _fresh_router():
    """The router is built once and cached, so clear it between tests."""
    llm._router = None
    yield
    llm._router = None


# ---------------------------------------------------------------------------
# describe_exception — the blank error message bug
# ---------------------------------------------------------------------------


def test_timeout_error_produces_a_non_empty_message():
    """The exact bug: str(asyncio.TimeoutError()) is ''."""
    assert str(asyncio.TimeoutError()) == ""
    assert llm.describe_exception(asyncio.TimeoutError()) == "TimeoutError"


def test_exception_with_a_message_keeps_both_type_and_detail():
    assert llm.describe_exception(ValueError("bad json")) == "ValueError: bad json"


@pytest.mark.parametrize(
    "exc",
    [asyncio.TimeoutError(), ValueError(""), RuntimeError("   "), Exception()],
)
def test_no_exception_ever_renders_as_empty(exc):
    """Whatever we show the user, it shouldn't be blank."""
    assert llm.describe_exception(exc).strip()


# ---------------------------------------------------------------------------
# Provider-aware credentials
# ---------------------------------------------------------------------------


def test_gemini_model_gets_the_gemini_key(monkeypatch):
    monkeypatch.setattr(llm.settings, "openai_api_key", "openai-key")
    monkeypatch.setattr(llm.settings, "gemini_api_key", "gemini-key")

    assert llm._api_key_for("gemini/gemini-3.6-flash") == "gemini-key"


def test_openai_model_gets_the_openai_key(monkeypatch):
    monkeypatch.setattr(llm.settings, "openai_api_key", "openai-key")
    monkeypatch.setattr(llm.settings, "gemini_api_key", "gemini-key")

    assert llm._api_key_for("openai/gpt-4o") == "openai-key"


def test_swapping_primary_to_gemini_also_swaps_its_credential(monkeypatch):
    """Point primary at Gemini and it should get the Gemini key.

    This used to always hand over the OpenAI key, so every call quietly went to
    the fallback while looking like the primary was fine.
    """
    monkeypatch.setattr(llm.settings, "openai_api_key", "openai-key")
    monkeypatch.setattr(llm.settings, "gemini_api_key", "gemini-key")
    monkeypatch.setattr(llm.settings, "primary_model", "gemini/gemini-3.6-flash")

    entry = next(m for m in llm.get_router().model_list if m["model_name"] == "primary")

    assert entry["litellm_params"]["model"] == "gemini/gemini-3.6-flash"
    assert entry["litellm_params"]["api_key"] == "gemini-key"


# ---------------------------------------------------------------------------
# Router wiring
# ---------------------------------------------------------------------------


def test_router_exposes_both_cost_tiers():
    """Utility calls route to "mini" so they are not billed at gpt-4o rates."""
    groups = {m["model_name"] for m in llm.get_router().model_list}

    assert {"primary", "fallback", "mini", "mini_fallback"} <= groups


def test_each_tier_has_a_fallback_configured():
    fallbacks = {k: v for entry in llm.get_router().fallbacks for k, v in entry.items()}

    assert fallbacks["primary"] == ["fallback"]
    assert fallbacks["mini"] == ["mini_fallback"]


def test_retry_policy_does_not_retry_deterministic_failures():
    """Retrying a bad request or a bad key just wastes time on the same error."""
    policy = llm.get_router().retry_policy

    assert policy.BadRequestErrorRetries == 0
    assert policy.AuthenticationErrorRetries == 0
    assert policy.RateLimitErrorRetries > 0
    assert policy.TimeoutErrorRetries > 0


def test_timeout_leaves_room_for_the_slower_fallback():
    """The sales call takes 15-34s normally and the fallback is slower again,
    so a 30s timeout was cutting off calls that would have worked.
    """
    assert llm.REQUEST_TIMEOUT_SECONDS >= 60


def test_router_is_a_singleton():
    assert llm.get_router() is llm.get_router()


def test_gemini_2_5_models_are_not_referenced():
    """Gemini 2.5 is gone, and a dead model here fails quietly rather than loudly."""
    configured = " ".join(m["litellm_params"]["model"] for m in llm.get_router().model_list)

    assert "gemini-2.5" not in configured
