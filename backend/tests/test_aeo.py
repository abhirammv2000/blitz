"""Tests for aeo_check's handling of failed probes.

The bug: a probe that timed out or errored was recorded with mentioned=False,
identical in shape to a probe that ran and genuinely found nothing. The filter
meant to separate the two - `d.get("mentioned") is not None` - is true for
every entry, since even the failure branch sets mentioned=False. A run where
every probe timed out scored a confirmed 0/10, not "no data came back."

Two separate places computed this the same wrong way: the overall score, and
each model's own summary (what the frontend gauge reads). Both are covered
here, with real API calls stubbed out - no network, no spend.
"""

from __future__ import annotations

import asyncio

import litellm
import pytest

from app.agents.agent_0_research.research import aeo_check

pytestmark = pytest.mark.usefixtures("isolated_chroma")

_GOOD_MODEL = "test/always-answers"
_BAD_MODEL = "test/always-times-out"


def _mentioning_response(company: str) -> str:
    return f"1. {company} - a great choice for this category."


@pytest.fixture(autouse=True)
def _point_aeo_at_two_controllable_models(monkeypatch):
    """Real aeo_check reads its two model names from settings - pointing them
    at fake names lets each be made to succeed or fail on purpose."""
    import app.agents.agent_0_research.research as research

    monkeypatch.setattr(research.settings, "aeo_first_model", _GOOD_MODEL)
    monkeypatch.setattr(research.settings, "aeo_second_model", _BAD_MODEL)


async def _stub_acompletion(*, model, messages, **_kwargs):
    from types import SimpleNamespace

    if model == _BAD_MODEL:
        await asyncio.sleep(0)
        raise litellm.Timeout("simulated timeout", model=model, llm_provider="test")

    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=_mentioning_response("Acme")))],
    )


async def test_a_model_that_always_times_out_does_not_drag_the_score_down(monkeypatch):
    """Before the fix: 3 real mentions + 3 timeouts scored as 3/6 = 50% mention
    rate. After: the timeouts are excluded, so it scores 3/3 = 100% - what the
    model that actually answered actually said.
    """
    monkeypatch.setattr(litellm, "acompletion", _stub_acompletion)
    queue = asyncio.Queue()

    score, _details = await aeo_check("Acme", "acme.com", queue, category="widgets")

    assert score == 10.0


async def test_the_failing_models_summary_does_not_claim_zero_mentions(monkeypatch):
    """A model that never answered should not be reported the same way as a
    model that answered three times and found nothing."""
    monkeypatch.setattr(litellm, "acompletion", _stub_acompletion)
    queue = asyncio.Queue()

    _score, model_summaries = await aeo_check("Acme", "acme.com", queue, category="widgets")

    by_model = {d["model"]: d for d in model_summaries}
    assert by_model[_GOOD_MODEL]["mention_rate"] == "3/3"
    assert by_model[_GOOD_MODEL]["mentioned"] is True
    # 0/0, not 0/3 - nothing to divide by, not three confirmed non-mentions.
    assert by_model[_BAD_MODEL]["mention_rate"] == "0/0"
    assert by_model[_BAD_MODEL]["confidence"] == 0.0


async def test_all_probes_failing_does_not_crash_and_scores_zero(monkeypatch):
    """No data at all still has to produce a number, not an exception - the
    frontend gauge needs something to render."""
    async def always_fails(*, model, messages, **_kwargs):
        raise litellm.Timeout("simulated timeout", model=model, llm_provider="test")

    monkeypatch.setattr(litellm, "acompletion", always_fails)
    queue = asyncio.Queue()

    score, model_summaries = await aeo_check("Acme", "acme.com", queue, category="widgets")

    assert score == 0.0
    assert len(model_summaries) == 2  # one summary per model, both empty
    assert all(s["mention_rate"] == "0/0" for s in model_summaries)
    assert all(s["confidence"] == 0.0 for s in model_summaries)


async def test_a_mix_of_mentions_and_genuine_misses_still_averages_correctly(monkeypatch):
    """Sanity check that the fix didn't just make everything pass: a model
    that really did miss two of three angles still scores accordingly."""
    call_count = {"n": 0}

    async def mostly_missing(*, model, messages, **_kwargs):
        from types import SimpleNamespace

        call_count["n"] += 1
        if model == _GOOD_MODEL and call_count["n"] == 1:
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=_mentioning_response("Acme")))],
            )
        if model == _BAD_MODEL:
            raise litellm.Timeout("simulated timeout", model=model, llm_provider="test")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Nothing relevant here."))])

    monkeypatch.setattr(litellm, "acompletion", mostly_missing)
    queue = asyncio.Queue()

    score, model_summaries = await aeo_check("Acme", "acme.com", queue, category="widgets")

    by_model = {d["model"]: d for d in model_summaries}
    assert by_model[_GOOD_MODEL]["mention_rate"] == "1/3"
    assert 0.0 < score < 10.0
