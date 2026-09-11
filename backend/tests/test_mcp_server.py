"""Tests for the MCP tool wrappers in mcp_server.py.

Everything here stubs tavily_search / firecrawl_scrape, the same way every
other test in this codebase stubs an external API - no real Tavily or
Firecrawl call, no spend. Uses the SDK's own in-process Client, not a real
stdio server process.

The Client is opened and closed within each test function directly, not via
a yielding pytest fixture - that pattern hit a real anyio/pytest-asyncio
cross-task teardown error (the Client's internal TaskGroup gets entered in
one task and exited in another), verified directly rather than worked around
blindly. Keeping the whole async-with block inside one function avoids it.

One thing worth pinning down: an uncaught exception inside a tool function
was verified (empirically, against the installed mcp==2.2.0, not assumed) to
crash the whole client session, not just that one call. Both tools catch and
return a controlled error dict instead - these tests prove that actually
holds, not just that it looks right on inspection.
"""

from __future__ import annotations

import asyncio
import json

from mcp import Client

import mcp_server


def _content_json(result) -> dict:
    """Tool returns are dicts, which this SDK version serializes into
    content[0].text as JSON - verified directly, not the structured_content
    field the docs' own int-returning example used."""
    return json.loads(result.content[0].text)


async def test_both_tools_are_registered():
    async with Client(mcp_server.mcp, raise_exceptions=True) as c:
        tools = await c.list_tools()

    assert {t.name for t in tools.tools} == {"search_company", "scrape_company_site"}


async def test_search_company_schema_matches_its_real_signature():
    async with Client(mcp_server.mcp, raise_exceptions=True) as c:
        tools = await c.list_tools()

    tool = next(t for t in tools.tools if t.name == "search_company")
    assert tool.input_schema["required"] == ["company_name", "company_url"]
    assert set(tool.input_schema["properties"]) == {"company_name", "company_url"}


async def test_search_company_returns_the_underlying_results(monkeypatch):
    async def fake_tavily_search(company_name, company_url, queue, feedback=None, category=None):
        return ([{"title": "Acme raises funding"}], [{"title": "Globex - a competitor"}])

    monkeypatch.setattr(mcp_server, "tavily_search", fake_tavily_search)

    async with Client(mcp_server.mcp, raise_exceptions=True) as c:
        result = await c.call_tool("search_company", {"company_name": "Acme", "company_url": "https://acme.com"})

    data = _content_json(result)
    assert data["press_results"] == [{"title": "Acme raises funding"}]
    assert data["competitor_raw_results"] == [{"title": "Globex - a competitor"}]


async def test_search_company_failure_returns_an_error_dict_not_a_crash(monkeypatch):
    async def failing_tavily_search(*args, **kwargs):
        raise RuntimeError("simulated Tavily outage")

    monkeypatch.setattr(mcp_server, "tavily_search", failing_tavily_search)

    async with Client(mcp_server.mcp, raise_exceptions=True) as c:
        result = await c.call_tool("search_company", {"company_name": "Acme", "company_url": "https://acme.com"})

    data = _content_json(result)
    assert "error" in data
    assert "RuntimeError" in data["error"]
    assert "simulated Tavily outage" in data["error"]


async def test_scrape_company_site_returns_the_markdown(monkeypatch):
    async def fake_firecrawl_scrape(url, queue):
        return "# Acme\nWe build widgets."

    monkeypatch.setattr(mcp_server, "firecrawl_scrape", fake_firecrawl_scrape)

    async with Client(mcp_server.mcp, raise_exceptions=True) as c:
        result = await c.call_tool("scrape_company_site", {"url": "https://acme.com"})

    data = _content_json(result)
    assert data["url"] == "https://acme.com"
    assert data["markdown"] == "# Acme\nWe build widgets."


async def test_scrape_company_site_failure_returns_an_error_dict_not_a_crash(monkeypatch):
    async def failing_scrape(url, queue):
        raise TimeoutError("simulated Firecrawl timeout")

    monkeypatch.setattr(mcp_server, "firecrawl_scrape", failing_scrape)

    async with Client(mcp_server.mcp, raise_exceptions=True) as c:
        result = await c.call_tool("scrape_company_site", {"url": "https://acme.com"})

    data = _content_json(result)
    assert "error" in data
    assert "TimeoutError" in data["error"]


async def test_discard_queue_put_never_blocks():
    """The queue passed to the wrapped functions has no consumer - put() has
    to complete on its own, not hang waiting for someone to drain it."""
    q = mcp_server._discard_queue()

    await asyncio.wait_for(q.put({"step": "x", "status": "running"}), timeout=1.0)
