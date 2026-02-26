"""Standalone test for Agent 0 (Research Scout).

Usage:
    cd backend
    python -m agents.agent_0_research.test_agent0                         # default: https://notion.so
    python -m agents.agent_0_research.test_agent0 https://stripe.com      # custom URL
"""

import asyncio
import json
import sys
import time
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend/ is on the path (this file lives in backend/agents/agent_0_research/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(override=True)

from agents.agent_0_research.research import (
    run_research,
    tavily_search,
    firecrawl_scrape,
    aeo_check,
    extract_competitors,
    _extract_company_name,
    _extract_bare_domain,
)
from agents.agent_0_research.progress import get_queue


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def drain_queue(queue: asyncio.Queue):
    """Print all progress events from the queue."""
    while not queue.empty():
        event = await queue.get()
        status = event.get("status", "")
        step = event.get("step", "")
        detail = event.get("detail", "")
        icon = {"running": ">>", "done": "OK", "error": "!!", "timeout": "TT"}.get(status, "--")
        print(f"  [{icon}] {step}: {detail}")


async def test_full_pipeline(url: str):
    """Run the full Agent 0 pipeline and inspect every field."""
    run_id = "test-run-001"
    queue = get_queue(run_id)

    print_section(f"AGENT 0 TEST: {url}")
    company_name = _extract_company_name(url)
    domain = _extract_bare_domain(url)
    print(f"  Extracted name: {company_name}")
    print(f"  Extracted domain: {domain}")

    start = time.time()
    output = await run_research(url, run_id)
    elapsed = time.time() - start

    # Drain progress queue
    print_section("PROGRESS EVENTS")
    await drain_queue(queue)

    # -- Executive Summary --
    print_section("EXECUTIVE SUMMARY")
    print(f"  {output.executive_summary}")

    # -- Summary --
    print_section("SUMMARY")
    print(f"  {output.summary[:1500]}")

    # -- Press Coverage --
    print_section(f"PRESS COVERAGE ({len(output.press_coverage)} items)")
    for i, p in enumerate(output.press_coverage[:10]):
        title = p.get("title", "?")[:80]
        url_str = p.get("url", "")[:60]
        snippet = p.get("snippet", "")[:120]
        print(f"  {i+1}. {title}")
        print(f"     URL: {url_str}")
        print(f"     {snippet}")
        print()

    # -- Competitors --
    print_section(f"COMPETITORS ({len(output.competitors)} found)")
    for c in output.competitors:
        print(f"  - {c.get('name', '?')}")
        print(f"    Positioning: {c.get('positioning', 'N/A')}")
        print(f"    Strengths:   {c.get('strengths', [])}")
        print(f"    Weaknesses:  {c.get('weaknesses', [])}")
        print()

    # -- AEO --
    print_section(f"AEO SCORE: {output.aeo_score:.1f}/10")
    for d in output.aeo_details:
        model = d.get("model", "?")
        mentioned = d.get("mentioned", False)
        confidence = d.get("confidence", 0)
        quote = d.get("quote", "")[:150]
        print(f"  {model}:")
        print(f"    Mentioned: {mentioned}  |  Confidence: {confidence:.0%}")
        print(f"    Quote: {quote}")
        print()

    # -- Site Content --
    print_section("SITE CONTENT (first 500 chars)")
    print(f"  {output.site_content[:500]}")

    # -- Stats --
    print_section("STATS")
    print(f"  Time:          {elapsed:.1f}s")
    print(f"  Press items:   {len(output.press_coverage)}")
    print(f"  Competitors:   {len(output.competitors)}")
    print(f"  AEO Score:     {output.aeo_score:.1f}/10")
    print(f"  Site chars:    {len(output.site_content)}")

    # -- Save full output to file for inspection --
    outfile = os.path.join(os.path.dirname(__file__), "test_agent0_output.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {outfile}")

    return output


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://notion.so"
    asyncio.run(test_full_pipeline(url))
