"""Tests for the ads critic's deterministic length/character checks.

The critic used to ask a model to count words and got it wrong - a 12-word ad
body was once judged as exceeding a 50-word limit. Word and character counts
are exact and checkable in Python, so they no longer go through a model at
all; the model is only asked about genericness, which actually needs judgment.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.agents.agent_5_ads.critic import _length_violations, critic_ads_node


def _ad(headline="Fast, simple, done", body="Short body copy here.", cta="Try it", platform="Google Ads", **extra):
    return {"segment": "s", "platform": platform, "headline": headline, "body": body, "cta": cta, **extra}


def _ab(headline="Fast, simple, done", body="Short body copy here.", cta="Try it", platform="Google Ads", **extra):
    return {
        "ad_copy_ref": "r", "variant_label": "A", "platform": platform,
        "headline": headline, "body": body, "cta": cta, **extra,
    }


# ---------------------------------------------------------------------------
# _length_violations
# ---------------------------------------------------------------------------


def test_compliant_ad_has_no_violations():
    assert _length_violations({"ad_copies": [_ad()], "ab_variations": []}) == []


def test_empty_output_has_no_violations():
    assert _length_violations({}) == []
    assert _length_violations({"ad_copies": [], "ab_variations": []}) == []


def test_a_short_body_is_not_flagged():
    """The regression pin: a body this short was once wrongly judged too long."""
    body = "Transform your startup's workflow with AI-driven tools. Compete like never before!"
    assert len(body.split()) == 11

    ad = _ad(headline="", body=body, cta="")
    assert _length_violations({"ad_copies": [ad], "ab_variations": []}) == []


def test_over_fifty_words_is_flagged():
    body = " ".join(["word"] * 60)
    violations = _length_violations({"ad_copies": [_ad(headline="", body=body, cta="")], "ab_variations": []})

    assert len(violations) == 1
    assert "60 words" in violations[0]
    assert "limit is 50" in violations[0]


def test_word_count_covers_headline_body_and_cta_together():
    """2 + 44 + 5 words in three fields still adds up to one over-limit ad,
    even though no single field looks long on its own. Headline stays short
    so this tests word count in isolation from the character-limit check."""
    ad = _ad(
        headline="Two words",
        body=" ".join(["b"] * 44),
        cta=" ".join(["c"] * 5),
    )
    violations = _length_violations({"ad_copies": [ad], "ab_variations": []})

    assert len(violations) == 1
    assert "51 words" in violations[0]


@pytest.mark.parametrize("platform,limit", [("Google Ads", 30), ("Meta Ads", 40), ("LinkedIn Ads", 40)])
def test_headline_over_the_platform_limit_is_flagged(platform, limit):
    headline = "x" * (limit + 1)
    violations = _length_violations({"ad_copies": [_ad(headline=headline, platform=platform)], "ab_variations": []})

    assert any(f"limit is {limit}" in v for v in violations)


def test_headline_at_exactly_the_limit_is_not_flagged():
    headline = "x" * 30
    violations = _length_violations({"ad_copies": [_ad(headline=headline, platform="Google Ads")], "ab_variations": []})

    assert violations == []


def test_unknown_platform_skips_the_character_check_but_still_counts_words():
    """Only word count applies to a platform we don't have a stated limit for -
    we check what we can verify, not guess at limits nobody specified."""
    ad = _ad(headline="x" * 500, platform="TikTok Ads")

    violations = _length_violations({"ad_copies": [ad], "ab_variations": []})

    assert not any("chars" in v for v in violations)


def test_ab_variations_are_checked_too_not_just_ad_copies():
    long_body = " ".join(["word"] * 60)
    ab = _ab(headline="", body=long_body, cta="")
    violations = _length_violations({"ad_copies": [], "ab_variations": [ab]})

    assert len(violations) == 1
    assert "60 words" in violations[0]


# ---------------------------------------------------------------------------
# critic_ads_node - the deterministic check runs before any model call
# ---------------------------------------------------------------------------


async def test_a_length_violation_rejects_without_calling_the_model(monkeypatch):
    import app.agents.agent_5_ads.critic as critic_mod

    def _must_not_be_called():
        raise AssertionError("the model should not be called when a deterministic check already failed")

    monkeypatch.setattr(critic_mod, "get_router", _must_not_be_called)

    long_body = " ".join(["word"] * 60)
    ad = _ad(headline="", body=long_body, cta="")
    state = {"ads_output": {"ad_copies": [ad], "ab_variations": []}}

    result = await critic_ads_node(state)

    assert result["ads_approved"] is False
    assert "60 words" in result["ads_critic_feedback"]


async def test_compliant_ads_are_judged_by_the_model(monkeypatch):
    import app.agents.agent_5_ads.critic as critic_mod

    class _Router:
        async def acompletion(self, **_kwargs):
            content = json.dumps({"approved": True, "feedback": "Great job."})
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setattr(critic_mod, "get_router", lambda: _Router())

    state = {"ads_output": {"ad_copies": [_ad()], "ab_variations": []}}
    result = await critic_ads_node(state)

    assert result["ads_approved"] is True
    assert result["ads_critic_feedback"] is None


async def test_revision_cap_forces_approval_regardless_of_violations():
    long_body = " ".join(["word"] * 60)
    state = {
        "ads_output": {"ad_copies": [_ad(body=long_body)], "ab_variations": []},
        "ads_revision_count": 2,
    }

    result = await critic_ads_node(state)

    assert result["ads_approved"] is True
