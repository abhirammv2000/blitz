"""MCP server exposing the research pipeline's own search and scrape calls as
tools an MCP client can call directly.

Purely additive - the pipeline itself still calls tavily_search and
firecrawl_scrape the way it always has (agent 0 deciding when to call them,
not the model). This wraps the same functions a second way, for a client
that wants to call them directly. Nothing in the working pipeline imports
this file.

Verified against the installed mcp==2.2.0 package directly, not assumed from
docs - a couple of the official examples used camelCase attribute names
(inputSchema, isError) that don't exist on this version's objects; the real
ones are snake_case (input_schema, is_error). See MCPServer's own docs for
that this SDK's v2 line is the current stable, GA release, not v1 or the
2026-07-28 spec's prerelease.

    cd backend
    python mcp_server.py          # runs as a real stdio MCP server
    pytest tests/test_mcp_server.py   # in-process tests, no server process, no spend

Both tools call the real Tavily/Firecrawl APIs and cost the same as they do
inside the pipeline. Nothing here is free to run for real - only the tests are,
because they stub the underlying calls the same way every other external-API
test in this codebase does.
"""

from __future__ import annotations

import asyncio
import logging

from mcp.server import MCPServer

from app.agents.agent_0_research.research import firecrawl_scrape, tavily_search

logger = logging.getLogger(__name__)

mcp = MCPServer("blitz-research")


def _discard_queue() -> asyncio.Queue:
    """tavily_search and firecrawl_scrape report progress through a queue, for
    the pipeline's SSE stream. There's no stream here, so give them an
    unbounded queue nobody drains - put() on one never blocks, verified
    against asyncio.Queue's own default (maxsize=0)."""
    return asyncio.Queue()


@mcp.tool()
async def search_company(company_name: str, company_url: str) -> dict:
    """Search for press coverage and competitors for a company, via Tavily.

    Returns press results and raw competitor search results separately - the
    same shape agent 0 works with internally, before its own LLM call
    structures the competitor list.
    """
    try:
        press, competitors_raw = await tavily_search(company_name, company_url, _discard_queue())
        return {"press_results": press, "competitor_raw_results": competitors_raw}
    except Exception as exc:  # noqa: BLE001
        # Caught here, not left to raise: an uncaught exception in a tool
        # function crashes the whole client session in this SDK, verified
        # directly, not assumed - a controlled error is what a caller can
        # actually do something with.
        logger.warning("search_company failed for %s: %s", company_url, exc)
        return {"error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
async def scrape_company_site(url: str) -> dict:
    """Scrape a company's website and return its content as markdown."""
    try:
        markdown = await firecrawl_scrape(url, _discard_queue())
        return {"url": url, "markdown": markdown}
    except Exception as exc:  # noqa: BLE001
        logger.warning("scrape_company_site failed for %s: %s", url, exc)
        return {"error": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
