"""Tests for the telemetry layer.

The thing to watch for is under-recording. A dashboard that quietly misses
failed calls or retries still renders fine, it's just wrong, so these check that
everything gets counted and that nothing here can crash a pipeline run.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from app.telemetry import agent_context, current_agent, current_run_id
from app.telemetry.logger import BlitzTelemetryLogger, _provider_of
from app.telemetry.store import (
    get_agent_costs,
    get_run_detail,
    get_runs,
    get_summary,
    init_telemetry_table,
    record_call,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Use a throwaway database file so we don't touch the real blitz.db."""
    import app.telemetry.store as store

    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "telemetry-test.db")
    init_telemetry_table()


def _call(**overrides):
    payload = dict(
        run_id="run-1", agent="agent_1_profile", model_group="primary",
        model="gpt-4o", provider="openai", prompt_tokens=1000,
        completion_tokens=200, cost_usd=0.005, latency_ms=1200, status="success",
    )
    payload.update(overrides)
    record_call(**payload)


# ---------------------------------------------------------------------------
# Context propagation
# ---------------------------------------------------------------------------


def test_agent_context_sets_and_restores():
    assert current_run_id() is None

    with agent_context("run-9", "agent_3_content"):
        assert current_run_id() == "run-9"
        assert current_agent() == "agent_3_content"

    assert current_run_id() is None, "context leaked out of the block"


def test_nested_contexts_do_not_bleed():
    with agent_context("run-a", "agent_1_profile"):
        with agent_context("run-a", "agent_2_audience"):
            assert current_agent() == "agent_2_audience"
        assert current_agent() == "agent_1_profile", "inner context clobbered the outer"


async def test_concurrent_runs_keep_separate_identity():
    """Two runs at once shouldn't end up with each other's labels."""
    seen = {}

    async def one(run_id, agent, delay):
        with agent_context(run_id, agent):
            await asyncio.sleep(delay)
            seen[run_id] = (current_run_id(), current_agent())

    await asyncio.gather(one("run-x", "agent_1_profile", 0.02), one("run-y", "agent_5_ads", 0.01))

    assert seen["run-x"] == ("run-x", "agent_1_profile")
    assert seen["run-y"] == ("run-y", "agent_5_ads")


# ---------------------------------------------------------------------------
# Recording and aggregation
# ---------------------------------------------------------------------------


def test_summary_totals_cost_and_tokens():
    _call(cost_usd=0.01, prompt_tokens=100, completion_tokens=50)
    _call(cost_usd=0.02, prompt_tokens=200, completion_tokens=50)

    s = get_summary()

    assert s["calls"] == 2
    assert s["total_cost_usd"] == pytest.approx(0.03)
    assert s["total_tokens"] == 400


def test_failures_are_recorded_not_dropped():
    """Failed calls still cost time and tokens, so they have to be counted."""
    _call(status="success")
    _call(status="failure", error_type="RateLimitError", cost_usd=0.0)

    s = get_summary()

    assert s["calls"] == 2
    assert s["failures"] == 1
    assert s["success_rate"] == pytest.approx(0.5)


def test_cost_is_attributed_per_agent():
    """The total isn't much use on its own; we want to know who spent it."""
    _call(agent="agent_3_content", cost_usd=0.05)
    _call(agent="agent_1_profile", cost_usd=0.01)
    _call(agent="agent_3_content", cost_usd=0.03)

    costs = {row["agent"]: row for row in get_agent_costs()}

    assert costs["agent_3_content"]["cost_usd"] == pytest.approx(0.08)
    assert costs["agent_3_content"]["calls"] == 2
    assert list(costs)[0] == "agent_3_content", "agents should be ranked by spend"


def test_a_failover_is_visible_in_the_data():
    """Asked for primary, a Gemini model answered: that means the fallback ran."""
    _call(model_group="primary", model="gpt-4o", provider="openai")
    _call(model_group="primary", model="gemini-3.6-flash", provider="gemini")

    detail = get_run_detail("run-1")
    failovers = [
        c for c in detail["calls"]
        if c["model_group"] == "primary" and c["provider"] == "gemini"
    ]

    assert len(failovers) == 1


def test_runs_are_listed_newest_first():
    _call(run_id="run-old")
    _call(run_id="run-new")

    run_ids = [r["run_id"] for r in get_runs()]

    assert set(run_ids) == {"run-old", "run-new"}


def test_run_detail_is_scoped_to_one_run():
    """One run's calls shouldn't show up in another run's detail."""
    _call(run_id="run-1", cost_usd=0.01)
    _call(run_id="run-2", cost_usd=0.99)

    detail = get_run_detail("run-1")

    assert len(detail["calls"]) == 1
    assert detail["calls"][0]["cost_usd"] == pytest.approx(0.01)


def test_queries_are_safe_on_an_empty_table():
    """A fresh install should show an empty dashboard, not crash on a divide."""
    s = get_summary()

    assert s["calls"] == 0
    assert s["avg_cost_per_run_usd"] == 0.0
    assert s["success_rate"] == 0.0
    assert get_agent_costs() == []
    assert get_runs() == []


# ---------------------------------------------------------------------------
# Telemetry should never take the pipeline down with it
# ---------------------------------------------------------------------------


async def test_callback_records_a_successful_call():
    logger_ = BlitzTelemetryLogger()

    class _Usage:
        prompt_tokens, completion_tokens = 1500, 300

    class _Response:
        usage = _Usage()

    start = datetime.now()
    with agent_context("run-cb", "agent_4_sales"):
        await logger_.async_log_success_event(
            {"model": "gemini/gemini-3.6-flash", "response_cost": 0.0042, "litellm_params": {}},
            _Response(), start, start + timedelta(milliseconds=850),
        )

    calls = get_run_detail("run-cb")["calls"]
    assert len(calls) == 1
    assert calls[0]["agent"] == "agent_4_sales"
    assert calls[0]["cost_usd"] == pytest.approx(0.0042)
    assert calls[0]["prompt_tokens"] == 1500
    assert calls[0]["latency_ms"] == 850
    assert calls[0]["provider"] == "gemini"


async def test_a_malformed_event_does_not_raise():
    """If this throws, it takes a pipeline run down with it."""
    logger_ = BlitzTelemetryLogger()

    await logger_.async_log_success_event({}, None, None, None)  # should not raise


def test_store_write_failure_is_swallowed(monkeypatch):
    import app.telemetry.store as store

    monkeypatch.setattr(store, "_DB_PATH", "/nonexistent-dir/does-not-exist.db")

    record_call(  # should not raise
        run_id="r", agent="a", model_group="primary", model="m",
        provider="openai", status="success",
    )


@pytest.mark.parametrize(
    "model,expected",
    [
        ("gemini/gemini-3.6-flash", "gemini"),
        ("gpt-4o", "openai"),
        ("openai/gpt-4o-mini", "openai"),
        (None, "unknown"),
    ],
)
def test_provider_is_derived_from_the_model(model, expected):
    assert _provider_of(model) == expected
