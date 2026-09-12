"""Tests for the API endpoints and the SSE stream.

The streaming tests call stream_graph_with_progress directly instead of going
through the HTTP client, because things like "did we cancel the background
task" can't be seen from the outside.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main_mod
from app.config import settings

pytestmark = pytest.mark.usefixtures("isolated_chroma")


@pytest.fixture
def client():
    with TestClient(main_mod.app) as c:
        yield c


def _parse(events: list[str]) -> list[dict]:
    """Turn raw SSE strings into the dicts the frontend store would see."""
    out = []
    for chunk in events:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                out.append(json.loads(line[6:]))
    return out


class _FakeGraph:
    """Stands in for the compiled graph. Yields chunks, then optionally blows up."""

    def __init__(self, chunks, error=None, hang=False):
        self._chunks = chunks
        self._error = error
        self._hang = hang

    async def astream(self, *_args, **_kwargs):
        for chunk in self._chunks:
            yield chunk
            await asyncio.sleep(0)
        if self._hang:
            await asyncio.sleep(3600)
        if self._error:
            raise self._error


async def _collect(monkeypatch, graph) -> list[dict]:
    monkeypatch.setattr(main_mod, "graph", graph)
    events = []
    async for evt in main_mod.stream_graph_with_progress(
        "run-1", {"run_id": "run-1"}, {"configurable": {"thread_id": "run-1"}}
    ):
        events.append(evt)
    return _parse(events)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def test_health_reports_ok(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_pipeline_start_rejects_a_body_with_no_url(client):
    assert client.post("/pipeline/start", json={}).status_code == 422


# ---------------------------------------------------------------------------
# GET /pipeline/{run_id} - looking a run back up after the fact
# ---------------------------------------------------------------------------


def test_unknown_run_id_is_a_404(client):
    assert client.get("/pipeline/no-such-run").status_code == 404


def test_a_fully_finished_run_comes_back_complete(client):
    from app.db import store_agent_output

    run_id = "run-finished"
    for key in ("research_decision", "profile", "audience", "content", "sales", "ads"):
        store_agent_output(run_id, key, json.dumps({"stub": key}))

    body = client.get(f"/pipeline/{run_id}").json()

    assert body["complete"] is True
    assert body["current_step"] == 5
    assert body["research_output"] == {"stub": "research_decision"}
    assert body["ads_output"] == {"stub": "ads"}


def test_a_partial_run_comes_back_with_only_what_finished(client):
    """Closing the tab after agent 2 should not lose agents 0 and 1 - this is
    the whole point of reading from Chroma instead of the in-memory
    checkpoint."""
    from app.db import store_agent_output

    run_id = "run-partial"
    store_agent_output(run_id, "research_decision", json.dumps({"stub": "research_decision"}))
    store_agent_output(run_id, "profile", json.dumps({"stub": "profile"}))

    body = client.get(f"/pipeline/{run_id}").json()

    assert body["complete"] is False
    assert body["current_step"] == 1
    assert body["research_output"] == {"stub": "research_decision"}
    assert body["profile_output"] == {"stub": "profile"}
    assert body["audience_output"] is None
    assert body["ads_output"] is None


def test_a_run_that_only_got_through_research_reports_step_zero(client):
    from app.db import store_agent_output

    run_id = "run-just-started"
    store_agent_output(run_id, "research_decision", json.dumps({"stub": "research_decision"}))

    body = client.get(f"/pipeline/{run_id}").json()

    assert body["current_step"] == 0
    assert body["complete"] is False


# ---------------------------------------------------------------------------
# Access key - open by default, gated once ACCESS_KEY is configured
# ---------------------------------------------------------------------------


def test_no_key_configured_means_every_route_is_open(client):
    """The local/dev default: ACCESS_KEY unset, nothing is gated."""
    assert client.get("/telemetry/summary").status_code == 200


def test_missing_key_is_rejected_once_one_is_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "access_key", "secret123")
    assert client.get("/telemetry/summary").status_code == 401


def test_wrong_key_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "access_key", "secret123")
    r = client.get("/telemetry/summary", headers={"X-Blitz-Key": "not-it"})
    assert r.status_code == 401


def test_correct_key_is_accepted(client, monkeypatch):
    monkeypatch.setattr(settings, "access_key", "secret123")
    r = client.get("/telemetry/summary", headers={"X-Blitz-Key": "secret123"})
    assert r.status_code == 200


def test_health_never_needs_a_key(client, monkeypatch):
    """The load balancer's health check can't send a header, so this one route
    must stay open even with ACCESS_KEY configured."""
    monkeypatch.setattr(settings, "access_key", "secret123")
    assert client.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# Daily run cap - the backstop for a leaked or over-shared access key
# ---------------------------------------------------------------------------


def test_pipeline_start_is_refused_once_the_daily_cap_is_hit(client, monkeypatch):
    monkeypatch.setattr(main_mod, "check_and_increment_daily_cap", lambda _cap: False)

    r = client.post("/pipeline/start", json={"url": "https://acme.com"})

    assert r.status_code == 429
    assert "limit" in r.json()["detail"].lower()


def test_pipeline_start_checks_the_cap_before_touching_the_graph(client, monkeypatch):
    """A refused run shouldn't spin up the graph at all."""
    called = False

    class _ExplodingGraph:
        async def astream(self, *_args, **_kwargs):
            nonlocal called
            called = True
            yield {}

    monkeypatch.setattr(main_mod, "graph", _ExplodingGraph())
    monkeypatch.setattr(main_mod, "check_and_increment_daily_cap", lambda _cap: False)

    client.post("/pipeline/start", json={"url": "https://acme.com"})

    assert called is False


# ---------------------------------------------------------------------------
# Streaming: the happy path
# ---------------------------------------------------------------------------


async def test_successful_run_streams_state_then_done(monkeypatch):
    events = await _collect(
        monkeypatch,
        _FakeGraph([{"run_id": "run-1", "current_step": 0}, {"run_id": "run-1", "current_step": 1}]),
    )

    assert [e["type"] for e in events][-1] == "done"
    assert sum(1 for e in events if e["type"] == "state") == 2


async def test_internal_langgraph_keys_are_not_leaked(monkeypatch):
    """Keys starting with __ are LangGraph's own bookkeeping."""
    events = await _collect(
        monkeypatch, _FakeGraph([{"run_id": "run-1", "__internal__": "x", "current_step": 0}])
    )

    state = next(e for e in events if e["type"] == "state")
    assert "__internal__" not in state["data"]
    assert state["data"]["run_id"] == "run-1"


# ---------------------------------------------------------------------------
# Streaming: failure paths
# ---------------------------------------------------------------------------


async def test_completed_work_survives_a_later_failure(monkeypatch):
    """Two agents finish, the next one dies. We should still send what finished."""
    completed = [
        {"run_id": "run-1", "current_step": 0, "research_output": {"a": 1}},
        {"run_id": "run-1", "current_step": 1, "profile_output": {"b": 2}},
    ]
    events = await _collect(monkeypatch, _FakeGraph(completed, error=RuntimeError("agent 5 died")))

    states = [e for e in events if e["type"] == "state"]
    assert len(states) == 2, "completed agent output was discarded"
    assert states[-1]["data"]["profile_output"] == {"b": 2}
    assert events[-1]["type"] == "error"


async def test_error_message_is_never_blank(monkeypatch):
    """Timeouts stringify to nothing, which showed up in the UI as a blank error."""
    events = await _collect(monkeypatch, _FakeGraph([], error=asyncio.TimeoutError()))

    error = next(e for e in events if e["type"] == "error")
    assert error["message"].strip()
    assert "TimeoutError" in error["message"]


async def test_error_message_keeps_the_underlying_detail(monkeypatch):
    events = await _collect(monkeypatch, _FakeGraph([], error=ValueError("bad json from model")))

    error = next(e for e in events if e["type"] == "error")
    assert "bad json from model" in error["message"]


async def test_a_failed_run_does_not_also_report_done(monkeypatch):
    """A run that failed shouldn't also look like it succeeded."""
    events = await _collect(monkeypatch, _FakeGraph([], error=RuntimeError("boom")))

    assert not any(e["type"] == "done" for e in events)


# ---------------------------------------------------------------------------
# Streaming: client disconnect
# ---------------------------------------------------------------------------


async def test_abandoning_the_stream_cancels_the_running_graph(monkeypatch):
    """Closing the tab used to leave the pipeline running with nobody watching."""
    graph = _FakeGraph([{"run_id": "run-1", "current_step": 0}], hang=True)
    monkeypatch.setattr(main_mod, "graph", graph)

    stream = main_mod.stream_graph_with_progress(
        "run-1", {"run_id": "run-1"}, {"configurable": {"thread_id": "run-1"}}
    )
    await stream.__anext__()
    # Closing the generator is what Starlette does when the client goes away.
    await stream.aclose()
    await asyncio.sleep(0.05)

    tasks = [t for t in asyncio.all_tasks() if not t.done() and t is not asyncio.current_task()]
    assert not any("graph_runner" in (t.get_name() or "") for t in tasks)


async def test_the_progress_queue_is_released_after_a_run(monkeypatch):
    """Queues live in a module-level dict, so a stale one leaks for good."""
    from app.agents.agent_0_research.progress import _queues

    await _collect(monkeypatch, _FakeGraph([{"run_id": "run-1", "current_step": 0}]))

    assert "run-1" not in _queues


# ---------------------------------------------------------------------------
# Image generation cost cap
# ---------------------------------------------------------------------------


def test_image_generation_is_capped_per_run(client, monkeypatch):
    """Images are the priciest thing a click can trigger, so the cap matters."""
    monkeypatch.setattr(main_mod, "IMAGE_CAP", 2)
    monkeypatch.setattr(main_mod, "_image_counts", {})

    async def fake_image(_prompt):
        return "data:image/png;base64,AAAA"

    monkeypatch.setattr("app.agents.agent_5_ads.node.generate_ad_image", fake_image)

    seen = []
    for _ in range(3):
        r = client.post("/ads/run-cap/generate-image", json={"prompt": "x"})
        seen.append(r.json())

    assert seen[0]["image_url"] and seen[1]["image_url"]
    assert seen[2]["image_url"] is None
    assert "limit" in seen[2]["error"].lower()


def test_a_failed_generation_does_not_consume_cap(client, monkeypatch):
    """Otherwise an outage quietly eats someone's allowance."""
    monkeypatch.setattr(main_mod, "IMAGE_CAP", 2)
    monkeypatch.setattr(main_mod, "_image_counts", {})

    async def failing_image(_prompt):
        return None

    monkeypatch.setattr("app.agents.agent_5_ads.node.generate_ad_image", failing_image)

    body = client.post("/ads/run-fail/generate-image", json={"prompt": "x"}).json()

    assert body["image_url"] is None
    assert body["remaining"] == 2, "a failed generation consumed part of the cap"
