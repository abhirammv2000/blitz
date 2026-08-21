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
