"""End-to-end LangGraph run with every external call stubbed.

This is the test that would have caught the bug that broke the pipeline: the
critic node raised KeyError on a malformed prompt template, so every run died
at the last node. Nothing in the codebase exercised the assembled graph, so it
reached production and was only found by running the real thing for five
minutes at real API cost.

Everything here is offline: no LLM, no Tavily, no Firecrawl. The point is to
verify wiring — that nodes run in order, that each one's output reaches the
next, that the critic loop terminates — not to judge output quality.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import agents.agent_0_research.research as research_mod
import db as db_mod

pytestmark = pytest.mark.usefixtures("isolated_chroma")


def _response(content: str):
    """Shape a fake completion like the LiteLLM response the nodes unpack."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")],
        model="stub",
        usage=SimpleNamespace(completion_tokens=100, prompt_tokens=100),
    )


# Canned JSON keyed by a marker unique to each agent's prompt.
from tests.test_schemas import ADS, AUDIENCE, CONTENT, PROFILE, SALES  # noqa: E402

_BY_MARKER = [
    ("expert paid advertising strategist", ADS),
    ("image_prompt", [{"ref": "s + Google Ads", "image_prompt": "a prompt"}]),
    ("marketing director evaluating", {"approved": True, "feedback": "Great job."}),
]


class _StubRouter:
    """Stands in for the shared Router, dispatching on prompt content."""

    def __init__(self):
        self.calls: list[str] = []

    async def acompletion(self, model, messages, **kwargs):
        prompt = messages[0]["content"]
        self.calls.append(model)

        for marker, payload in _BY_MARKER:
            if marker in prompt:
                return _response(json.dumps(payload))
        if "content strategist" in prompt.lower() or "content_calendar" in prompt:
            return _response(json.dumps(CONTENT))
        if "sales" in prompt.lower() and "email_sequences" in prompt:
            return _response(json.dumps(SALES))
        if "audience" in prompt.lower() and "segments" in prompt:
            return _response(json.dumps(AUDIENCE))
        if "brand_dna" in prompt:
            return _response(json.dumps(PROFILE))
        # Small utility calls (entity name, category) want bare text.
        return _response("Acme")


@pytest.fixture
def stub_router(monkeypatch):
    router = _StubRouter()
    for module_path in (
        "llm.get_router",
        "agents.agent_0_research.research.get_router",
        "agents.agent_1_profile.node.get_router",
        "agents.agent_2_audience.node.get_router",
        "agents.agent_3_content.node.get_router",
        "agents.agent_4_sales.node.get_router",
        "agents.agent_5_ads.node.get_router",
        "agents.agent_5_ads.critic.get_router",
    ):
        monkeypatch.setattr(module_path, lambda: router, raising=False)
    return router


@pytest.fixture
def offline_research(monkeypatch):
    """Stub agent 0's network calls: Tavily, Firecrawl, and the AEO probes."""

    async def fake_tavily(company_name, company_url, queue, feedback=None, category=None):
        await queue.put({"step": "tavily", "status": "done"})
        return ([{"title": "Acme raises", "url": "https://news.example/acme", "content": "acme.com"}], [])

    async def fake_firecrawl(url, queue):
        await queue.put({"step": "firecrawl", "status": "done"})
        return "# Acme\nWe build widgets for teams."

    async def fake_aeo(company_name, domain, queue, category=None):
        await queue.put({"step": "aeo", "status": "done"})
        return 7.5, [{"model": "stub", "mentioned": True, "mention_rate": "3/3", "confidence": 1.0, "quote": ""}]

    async def fake_competitors(raw, name, category="", site_excerpt=""):
        return [{"name": "Globex", "positioning": "cheap", "strengths": [], "weaknesses": []}]

    monkeypatch.setattr(research_mod, "tavily_search", fake_tavily)
    monkeypatch.setattr(research_mod, "firecrawl_scrape", fake_firecrawl)
    monkeypatch.setattr(research_mod, "aeo_check", fake_aeo)
    monkeypatch.setattr(research_mod, "extract_competitors", fake_competitors)


async def _run_graph(run_id="test-run"):
    from graph import build_graph

    graph = build_graph()
    chunks = []
    async for chunk in graph.astream(
        {"run_id": run_id, "company_url": "https://acme.com", "current_step": 0},
        config={"configurable": {"thread_id": run_id}},
        stream_mode="values",
    ):
        chunks.append(chunk)
    return chunks[-1]


async def test_pipeline_runs_every_agent_to_completion(stub_router, offline_research):
    """The regression guard: a broken node must fail here, not in production."""
    final = await _run_graph()

    for key in (
        "research_output", "profile_output", "audience_output",
        "content_output", "sales_output", "ads_output",
    ):
        assert final.get(key), f"{key} missing — the pipeline did not complete"


async def test_critic_loop_terminates(stub_router, offline_research):
    """The critic routes back to agent 5 when it rejects.

    Without a revision cap this is an infinite loop that burns API spend on the
    most expensive node until something else breaks.
    """
    final = await _run_graph()

    assert final.get("ads_approved") is True
    assert final.get("ads_revision_count", 0) <= 3


async def test_each_agent_persists_its_output_for_the_next(stub_router, offline_research):
    """Agents pass data through ChromaDB, not through the graph state alone."""
    await _run_graph("persist-run")

    for agent in ("research_decision", "profile", "audience", "content", "sales", "ads"):
        assert db_mod.get_agent_output("persist-run", agent), f"{agent} was not stored"


async def test_pipeline_reports_the_final_step(stub_router, offline_research):
    final = await _run_graph()

    assert final["current_step"] == 5


async def test_agents_use_the_cheap_tier_for_utility_calls(stub_router, offline_research):
    """Cost guard: utility calls must not be billed at the primary model's rate."""
    await _run_graph()

    assert "mini" in stub_router.calls
    assert "primary" in stub_router.calls


async def test_a_failing_agent_does_not_lose_earlier_work(stub_router, offline_research, monkeypatch):
    """When a later agent fails, the earlier agents' output must still be
    readable. This is what lets the API return partial results instead of
    discarding several minutes of completed, paid-for work.
    """
    import agents.agent_4_sales.node as sales_node

    async def boom(run_id, feedback=None):
        raise RuntimeError("sales agent exploded")

    monkeypatch.setattr(sales_node, "run_sales", boom)

    with pytest.raises(RuntimeError):
        await _run_graph("partial-run")

    for agent in ("research_decision", "profile", "audience", "content"):
        assert db_mod.get_agent_output("partial-run", agent), f"{agent} was lost"
