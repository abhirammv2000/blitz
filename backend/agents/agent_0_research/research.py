"""Async research sub-step functions for Agent 0.

Architecture:
- All external API calls are wrapped with asyncio.wait_for(timeout=25s) for 60s SLA
- tavily_search, firecrawl_scrape, aeo_check run concurrently via asyncio.gather()
- extract_competitors runs sequentially after gather (needs Tavily results)
- Progress events are published to a per-run asyncio.Queue for SSE streaming
- AEO check calls GPT-4o and Gemini-2.5-pro concurrently (NOT via Router — both models needed)
- On timeout, returns partial results with a note rather than failing entirely

Usage:
    output = await run_research("https://example.com", run_id="abc123")
"""

from __future__ import annotations

import asyncio
import json
import os
import re

import litellm

from agents.agent_0_research.progress import get_queue
from agents.agent_0_research.prompts import AEO_CHECK_PROMPT, COMPETITOR_EXTRACTION_PROMPT, RESEARCH_SYNTHESIS_PROMPT
from agents.agent_0_research.schemas import ResearchOutput


_COMMON_TLDS_RE = r"\.(com|io|ai|co|net|org|app|dev|tech|so|me|us|xyz|gg|ly|to)$"


def _extract_bare_domain(url: str) -> str:
    """Extract bare domain from a URL, stripping protocol, www, and path.

    Example: "https://www.acme.com/about" -> "acme.com"
    """
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    return url.split("/")[0]


def _extract_company_name(url: str) -> str:
    """Extract a clean company name from a URL.

    Strips protocol, www prefix, path, and common TLDs.
    Example: "https://www.acme.com/about" -> "acme"
    """
    domain = _extract_bare_domain(url)
    name = re.sub(_COMMON_TLDS_RE, "", domain, flags=re.IGNORECASE)
    return name.capitalize()


async def tavily_search(
    company_name: str,
    company_url: str,
    queue: asyncio.Queue,
    feedback: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Search for press coverage and competitor information using Tavily.

    Runs three concurrent searches:
    1. Company's own press/blog content (include_domains=[company domain])
    2. Third-party press coverage (exclude_domains=[company domain])
    3. Competitor discovery search (max_results=8)

    Uses general search mode (not topic="news") so results are ranked by
    relevance instead of recency — prevents trending news from drowning out
    actual company coverage.

    Args:
        company_name: Clean company name for search queries.
        company_url: Company URL for targeted search.
        queue: Progress event queue for SSE streaming.
        feedback: Optional user feedback to refine search queries (reject case).

    Returns:
        Tuple of (press_results, competitor_raw_results) — each a list of Tavily result dicts.
    """
    from tavily import AsyncTavilyClient  # type: ignore[import]

    await queue.put({"step": "tavily", "status": "running", "detail": "Searching news and competitors"})

    client = AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))

    feedback_suffix = f" {feedback}" if feedback else ""

    bare_domain = _extract_bare_domain(company_url)

    competitor_query = f"\"{bare_domain}\" OR \"{company_name}\" competitors alternatives comparison{feedback_suffix}"

    try:
        # Search 1: Company's own press/blog content
        press_own_task = asyncio.wait_for(
            client.search(
                f"{company_name} press news blog",
                include_domains=[bare_domain],
                max_results=3,
            ),
            timeout=25.0,
        )
        # Search 2: Third-party coverage (exclude company's own site)
        press_external_task = asyncio.wait_for(
            client.search(
                f"\"{company_name}\" press coverage news announcement{feedback_suffix}",
                exclude_domains=[bare_domain],
                max_results=5,
            ),
            timeout=25.0,
        )
        competitor_task = asyncio.wait_for(
            client.search(competitor_query, max_results=8),
            timeout=25.0,
        )
        press_own_resp, press_ext_resp, competitor_resp = await asyncio.gather(
            press_own_task, press_external_task, competitor_task, return_exceptions=True,
        )

        press_results: list[dict] = []
        for resp in (press_own_resp, press_ext_resp):
            if isinstance(resp, Exception):
                continue
            press_results.extend(resp.get("results", []) if isinstance(resp, dict) else [])

        if not press_results and isinstance(press_own_resp, Exception) and isinstance(press_ext_resp, Exception):
            press_results = [{"title": f"Tavily press search failed: {press_own_resp}", "url": "", "content": ""}]

        if isinstance(competitor_resp, Exception):
            competitor_results: list[dict] = []
        else:
            competitor_results = competitor_resp.get("results", []) if isinstance(competitor_resp, dict) else []

    except asyncio.TimeoutError:
        press_results = [{"title": "Tavily search timed out", "url": "", "content": ""}]
        competitor_results = []

    await queue.put({
        "step": "tavily",
        "status": "done",
        "detail": f"{len(press_results)} press results, {len(competitor_results)} competitor results",
    })

    return press_results, competitor_results


async def firecrawl_scrape(url: str, queue: asyncio.Queue) -> str:
    """Scrape a company website and return markdown content using Firecrawl.

    Falls back to sync FirecrawlApp in thread executor if async variant unavailable.

    Args:
        url: Company website URL to scrape.
        queue: Progress event queue for SSE streaming.

    Returns:
        Markdown string of scraped content, or error note on failure.
    """
    await queue.put({"step": "firecrawl", "status": "running", "detail": f"Scraping {url}"})

    try:
        try:
            from firecrawl import AsyncFirecrawlApp  # type: ignore[import]

            app = AsyncFirecrawlApp(api_key=os.environ.get("FIRECRAWL_API_KEY", ""))
            result = await asyncio.wait_for(
                app.scrape(url, params={"formats": ["markdown"]}),
                timeout=25.0,
            )
        except (ImportError, AttributeError):
            # Fall back to sync FirecrawlApp in thread executor
            from firecrawl import FirecrawlApp  # type: ignore[import]

            sync_app = FirecrawlApp(api_key=os.environ.get("FIRECRAWL_API_KEY", ""))

            def _sync_scrape() -> dict:
                return sync_app.scrape(url, params={"formats": ["markdown"]})

            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _sync_scrape),
                timeout=25.0,
            )

        # firecrawl returns dict or ScrapeResponse object
        if isinstance(result, dict):
            markdown = result.get("markdown", "") or result.get("content", "")
        else:
            markdown = getattr(result, "markdown", "") or getattr(result, "content", "") or ""

        await queue.put({"step": "firecrawl", "status": "done", "detail": f"{len(markdown)} chars scraped"})
        return markdown

    except asyncio.TimeoutError:
        await queue.put({"step": "firecrawl", "status": "timeout", "detail": "Scrape timed out after 25s"})
        return f"[Firecrawl scrape timed out for {url}]"
    except Exception as exc:
        await queue.put({"step": "firecrawl", "status": "error", "detail": str(exc)})
        return f"[Firecrawl scrape failed: {exc}]"


async def aeo_check(
    company_name: str,
    domain: str,
    queue: asyncio.Queue,
) -> tuple[float, list[dict]]:
    """Check AI Engine Optimization (AEO) score for a company.

    Queries GPT-4o and Gemini-2.5-pro concurrently to see if they mention the
    company in a natural customer-style question. Computes a 0-10 composite score.

    Note: Uses litellm.acompletion() directly, NOT the Router — AEO needs both
    models explicitly to compare their responses, not fallback behavior.

    Args:
        company_name: Clean company name.
        domain: Company domain (e.g. "acme.com") for the prompt.
        queue: Progress event queue for SSE streaming.

    Returns:
        Tuple of (composite_score, details_list).
        composite_score: 0-10 (sum of confidence * 5 per model where mentioned=True, max 10)
        details_list: [{model, mentioned, confidence, quote}]
    """
    await queue.put({"step": "aeo", "status": "running", "detail": "Querying GPT-4o and Gemini concurrently"})

    prompt = AEO_CHECK_PROMPT.format(company_name=company_name, domain=domain)

    async def _query_model(model: str, api_key_env: str) -> dict:
        try:
            api_key = os.environ.get(api_key_env, "")
            response = await asyncio.wait_for(
                litellm.acompletion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=api_key,
                    temperature=0.3,
                ),
                timeout=60.0,
            )
            content = response.choices[0].message.content or ""
            # Parse the last line as JSON
            lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
            last_line = lines[-1] if lines else "{}"
            try:
                parsed = json.loads(last_line)
            except json.JSONDecodeError:
                # Try to find JSON in the content
                json_match = re.search(r'\{[^}]+\}', content)
                parsed = json.loads(json_match.group()) if json_match else {}

            return {
                "model": model,
                "mentioned": bool(parsed.get("mentioned", False)),
                "confidence": float(parsed.get("confidence", 0.0)),
                "quote": str(parsed.get("quote", "")),
                "reasoning": content,  # Full LLM response for manual verification
            }
        except asyncio.TimeoutError:
            return {"model": model, "mentioned": False, "confidence": 0.0, "quote": "[timeout]", "reasoning": "[timeout]"}
        except Exception as exc:
            return {"model": model, "mentioned": False, "confidence": 0.0, "quote": f"[error: {exc}]"}

    gpt4o_task = _query_model("openai/gpt-4o", "OPENAI_API_KEY")
    gemini_task = _query_model("gemini/gemini-2.5-pro", "GEMINI_API_KEY")

    results = await asyncio.gather(gpt4o_task, gemini_task, return_exceptions=True)

    details: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            details.append({"model": "unknown", "mentioned": False, "confidence": 0.0, "quote": f"[error: {r}]"})
        else:
            details.append(r)

    # Composite score: sum of (confidence * 5) for each model where mentioned=True, capped at 10
    score = sum(d["confidence"] * 5 for d in details if d.get("mentioned"))
    score = min(score, 10.0)

    await queue.put({
        "step": "aeo",
        "status": "done",
        "detail": f"AEO score: {score:.1f}/10",
    })

    return score, details


async def extract_competitors(raw_results: list[dict], company_name: str) -> list[dict]:
    """Extract structured competitor information from raw Tavily search results.

    Uses LiteLLM structured output via the primary model (GPT-4o) to identify
    3-5 competitors with positioning, strengths, and weaknesses.

    Args:
        raw_results: Raw Tavily search result dicts with title, url, content fields.
        company_name: The company being analyzed (to exclude from competitor list).

    Returns:
        List of competitor dicts: [{name, positioning, strengths, weaknesses}]
    """
    if not raw_results:
        return []

    # Format results for the prompt
    formatted = "\n\n".join(
        f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nContent: {r.get('content', '')[:500]}"
        for r in raw_results[:8]
    )

    prompt = COMPETITOR_EXTRACTION_PROMPT.format(
        raw_results=formatted,
        company_name=company_name,
    )

    try:
        response = await asyncio.wait_for(
            litellm.acompletion(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                temperature=0.2,
            ),
            timeout=25.0,
        )
        content = response.choices[0].message.content or "[]"

        # Strip markdown code fences if present
        content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

        competitors: list[dict] = json.loads(content)
        if not isinstance(competitors, list):
            competitors = []
        return competitors

    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
        return []


async def run_research(
    company_url: str,
    run_id: str,
    feedback: str | None = None,
) -> ResearchOutput:
    """Run the full research pipeline for a company URL.

    Concurrently runs Tavily search, Firecrawl scrape, and AEO check.
    Then sequentially extracts competitors from Tavily results.
    Publishes sub-step progress events to the run's asyncio.Queue.

    All external calls are wrapped with 25s timeouts for a 60s SLA.
    On timeout, returns partial results with a note rather than failing.

    Args:
        company_url: The company website URL to research.
        run_id: Pipeline run identifier (UUID4) — used to scope the progress queue.
        feedback: Optional user feedback from a HITL reject — appended to search queries.

    Returns:
        ResearchOutput with company intelligence, press coverage, competitors, and AEO scores.
    """
    queue = get_queue(run_id)

    company_name = _extract_company_name(company_url)
    domain = _extract_bare_domain(company_url)

    await queue.put({"step": "research", "status": "starting", "company": company_name})

    # Run Tavily, Firecrawl, and AEO concurrently
    tavily_task = tavily_search(company_name, company_url, queue, feedback)
    firecrawl_task = firecrawl_scrape(company_url, queue)
    aeo_task = aeo_check(company_name, domain, queue)

    (press_results, competitor_raw), site_content, (aeo_score, aeo_details) = await asyncio.gather(
        tavily_task,
        firecrawl_task,
        aeo_task,
        return_exceptions=False,
    )

    # Sequential: extract competitors from Tavily results
    await queue.put({"step": "assembly", "status": "running", "detail": "Extracting competitor profiles"})
    competitors = await extract_competitors(competitor_raw, company_name)

    # Build press coverage list — filter out irrelevant results
    bare_domain = _extract_bare_domain(company_url)
    name_lower = company_name.lower()
    domain_lower = bare_domain.lower()
    name_stem = re.sub(_COMMON_TLDS_RE, "", bare_domain, flags=re.IGNORECASE).lower()

    press_coverage = []
    for r in press_results:
        title = r.get("title", "")
        content = r.get("content", "")
        url = r.get("url", "")
        title_lower = title.lower()
        url_lower = url.lower()
        # Strict relevance: domain must appear in the article URL,
        # OR the company name must appear in the article TITLE (not body — too many false positives)
        is_from_company_site = domain_lower in url_lower
        is_named_in_title = name_lower in title_lower or name_stem in title_lower
        if is_from_company_site or is_named_in_title:
            press_coverage.append({
                "title": title,
                "url": url,
                "snippet": content[:300],
            })

    # If nothing relevant found, say so instead of showing garbage
    if not press_coverage and press_results:
        press_coverage = [{"title": "No relevant press coverage found", "url": "", "snippet": f"Tavily returned {len(press_results)} results but none mentioned {company_name}."}]

    # Synthesize insights via LLM instead of mechanical copy-paste
    await queue.put({"step": "synthesis", "status": "running", "detail": "Synthesizing strategic insights"})

    site_excerpt = site_content[:3000] if site_content else "No website content available."
    press_summary = "\n".join(
        f"- {p['title']}: {p['snippet']}" for p in press_coverage[:5] if p.get("title")
    ) or "No press coverage found."
    competitor_summary = "\n".join(
        f"- {c.get('name', '?')}: {c.get('positioning', '')} | Strengths: {', '.join(c.get('strengths', []))} | Weaknesses: {', '.join(c.get('weaknesses', []))}"
        for c in competitors
    ) or "No competitors identified."
    aeo_summary = "\n".join(
        f"- {d.get('model', '?')}: {'Mentioned' if d.get('mentioned') else 'Not mentioned'} (confidence {d.get('confidence', 0):.0%}) {d.get('quote', '')}"
        for d in aeo_details
    ) or "No AEO data."

    synthesis_prompt = RESEARCH_SYNTHESIS_PROMPT.format(
        company_name=company_name,
        company_url=company_url,
        site_excerpt=site_excerpt,
        press_summary=press_summary,
        competitor_summary=competitor_summary,
        aeo_score=f"{aeo_score:.1f}",
        aeo_summary=aeo_summary,
    )

    try:
        synth_response = await asyncio.wait_for(
            litellm.acompletion(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": synthesis_prompt}],
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                temperature=0.4,
            ),
            timeout=30.0,
        )
        synth_content = synth_response.choices[0].message.content or "{}"
        synth_content = re.sub(r"```(?:json)?\n?", "", synth_content).strip().rstrip("```").strip()
        synth_data = json.loads(synth_content)
        summary = synth_data.get("summary", f"Research gathered for {company_name}.")
        executive_summary = synth_data.get("executive_summary", f"{company_name}: {aeo_score:.1f}/10 AEO score.")
    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
        # Fallback to basic assembly if synthesis fails
        summary = site_excerpt[:1000] if site_content else f"Research gathered for {company_name} at {company_url}."
        executive_summary = (
            f"{company_name} at {domain}. "
            f"{len(press_coverage)} press items, {len(competitors)} competitors. "
            f"AEO score: {aeo_score:.1f}/10."
        )

    await queue.put({
        "step": "synthesis",
        "status": "done",
        "detail": f"Research complete — {len(press_coverage)} articles, {len(competitors)} competitors",
    })

    return ResearchOutput(
        company_name=company_name,
        company_url=company_url,
        summary=summary,
        executive_summary=executive_summary,
        press_coverage=press_coverage,
        site_content=site_content,
        competitors=competitors,
        aeo_score=aeo_score,
        aeo_details=aeo_details,
    )
