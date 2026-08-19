"""Tests for ad image generation.

Image generation has broken twice in ways that were silent to the user, so both
failure modes are pinned here.
"""

from __future__ import annotations

import pytest

from app.agents.agent_5_ads.node import _image_mime
from app.core.llm import api_key_for_model


@pytest.mark.parametrize(
    "b64,expected",
    [
        ("iVBORw0KGgoAAAANSUhEUg", "image/png"),
        ("/9j/4AAQSkZJRgABAQ", "image/jpeg"),
        ("R0lGODlhAQABAIAAAA", "image/gif"),
        ("UklGRhoAAABXRUJQ", "image/webp"),
    ],
)
def test_data_uri_type_matches_the_payload(b64, expected):
    """A data URI whose declared type contradicts its bytes can fail to render.

    The type was hardcoded to image/png, which was right for gpt-image-1 and
    wrong for Gemini, which returns JPEG.
    """
    assert _image_mime(b64) == expected


def test_unrecognised_payload_falls_back_rather_than_raising():
    assert _image_mime("not-a-known-magic-prefix") == "image/png"


def test_image_credentials_follow_the_configured_provider(monkeypatch):
    """The key was hardcoded to OpenAI, so pointing IMAGE_MODEL at Gemini sent
    it an OpenAI key and image generation stayed broken with no credits.
    """
    import app.core.llm as llm

    monkeypatch.setattr(llm.settings, "openai_api_key", "openai-key")
    monkeypatch.setattr(llm.settings, "gemini_api_key", "gemini-key")

    assert api_key_for_model("gemini/gemini-3.1-flash-image") == "gemini-key"
    assert api_key_for_model("gpt-image-1") == "openai-key"
