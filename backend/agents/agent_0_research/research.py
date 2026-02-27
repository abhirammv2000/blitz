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
from agents.agent_0_research.prompts import AEO_BLIND_PROMPTS, AEO_CATEGORY_PROMPT, CATEGORY_FROM_CONTENT_PROMPT, COMPETITOR_EXTRACTION_PROMPT, RESEARCH_SYNTHESIS_PROMPT
from agents.agent_0_research.schemas import ResearchOutput


_COMMON_TLDS_RE = r"\.(com|io|ai|co|net|org|app|dev|tech|so|me|us|xyz|gg|ly|to)$"

# Common vanity prefixes in domains (e.g. joinblossomhealth.com, getnotion.com)
_VANITY_PREFIXES_RE = r"^(join|get|try|use|go|meet|hello|hey|my|the|visit|app)"


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


async def _extract_company_name_from_content(site_content: str, url: str, fallback_name: str) -> str:
    """Extract the real company name from scraped page content using a fast LLM call.

    Handles cases where the domain doesn't match the company name
    (e.g. joinblossomhealth.com -> "Blossom Health").

    Falls back to the regex-based name on any failure.
    """
    if not site_content or site_content.startswith("[Firecrawl"):
        return fallback_name

    # Use first 1500 chars — company name is almost always near the top
    excerpt = site_content[:1500]
    try:
        response = await asyncio.wait_for(
            litellm.acompletion(
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": (
                    f"What is the official company or product name for the website {url}?\n\n"
                    f"Page content:\n{excerpt}\n\n"
                    "Reply with ONLY the company/product name, nothing else. "
                    "Use proper capitalization (e.g. 'Blossom Health', not 'blossom health')."
                )}],
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                temperature=0,
                max_tokens=30,
            ),
            timeout=8.0,
        )
        name = (response.choices[0].message.content or "").strip().strip('"').strip("'")
        # Sanity check: reject empty, too long, or multi-sentence responses
        if name and len(name) <= 60 and "\n" not in name:
            return name
    except Exception as exc:
        print(f"[DEBUG] _extract_company_name_from_content FAILED: {exc!r}")
    return fallback_name


async def tavily_search(
    company_name: str,
    company_url: str,
    queue: asyncio.Queue,
    feedback: str | None = None,
    category: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Search for press coverage and competitor information using Tavily.

    Runs three concurrent searches:
    1. Major tech/business outlet coverage (include_domains for top publications)
    2. General third-party coverage (exclude company's own domain)
    3. Competitor discovery search (max_results=8)

    All searches exclude the company's own site — we already get site content
    from Firecrawl. Press search targets real journalism, not product pages.

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

    # Major tech/business publications for high-quality press coverage
    _NEWS_DOMAINS = [
        "techcrunch.com", "wired.com", "theverge.com", "arstechnica.com",
        "forbes.com", "bloomberg.com", "reuters.com", "wsj.com",
        "venturebeat.com", "thenextweb.com", "zdnet.com", "cnet.com",
        "businessinsider.com", "cnbc.com", "nytimes.com", "ft.com",
        "producthunt.com", "crunchbase.com", "sifted.eu", "protocol.com",
    ]

    # Two competitor searches: company-specific + category-specific (for generic names)
    competitor_query_company = f"\"{company_name}\" {bare_domain} competitors alternatives{feedback_suffix}"
    competitor_query_category = f"best {category} apps platforms competitors comparison{feedback_suffix}" if category else None

    try:
        # Include the domain in queries to disambiguate generic names
        # (e.g. "Linear linear.app" ensures results are about Linear the product,
        # not "Linear Technology" the semiconductor company)
        # Search 1: Coverage from major publications
        press_major_task = asyncio.wait_for(
            client.search(
                f"\"{company_name}\" {bare_domain} funding launch product announcement",
                include_domains=_NEWS_DOMAINS,
                max_results=5,
            ),
            timeout=25.0,
        )
        # Search 2: General third-party coverage (broader net)
        press_general_task = asyncio.wait_for(
            client.search(
                f"\"{company_name}\" {bare_domain} review analysis funding OR launch OR raised{feedback_suffix}",
                exclude_domains=[bare_domain],
                max_results=5,
            ),
            timeout=25.0,
        )
        competitor_company_task = asyncio.wait_for(
            client.search(competitor_query_company, max_results=8),
            timeout=25.0,
        )

        tasks = [press_major_task, press_general_task, competitor_company_task]

        # Category-based competitor search for better disambiguation
        if competitor_query_category:
            competitor_category_task = asyncio.wait_for(
                client.search(competitor_query_category, max_results=8),
                timeout=25.0,
            )
            tasks.append(competitor_category_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        press_major_resp = results[0]
        press_general_resp = results[1]
        competitor_company_resp = results[2]
        competitor_category_resp = results[3] if len(results) > 3 else None

        press_results: list[dict] = []
        for resp in (press_major_resp, press_general_resp):
            if isinstance(resp, Exception):
                continue
            press_results.extend(resp.get("results", []) if isinstance(resp, dict) else [])

        if not press_results and isinstance(press_major_resp, Exception) and isinstance(press_general_resp, Exception):
            press_results = [{"title": f"Tavily press search failed: {press_major_resp}", "url": "", "content": ""}]

        # Merge both competitor searches, deduplicating by URL
        competitor_results: list[dict] = []
        seen_urls: set[str] = set()
        for resp in (competitor_company_resp, competitor_category_resp):
            if resp is None or isinstance(resp, Exception):
                continue
            for r in (resp.get("results", []) if isinstance(resp, dict) else []):
                url = r.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    competitor_results.append(r)

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
    category: str | None = None,
) -> tuple[float, list[dict]]:
    """Check AI Engine Optimization (AEO) score for a company.

    Uses blind prompts — the company name is NOT in the question. Instead we
    describe the product category and ask each model to recommend tools. Then
    we check whether the company appears organically in the response and where
    it ranks (position scoring).

    Two phases:
    1. Fast category extraction from company name + domain (~1-2s)
    2. 3 prompt angles x 2 models = 6 blind queries (concurrent)

    Score: 0-10 based on mention rate and average position across all queries.

    Args:
        company_name: Clean company name.
        domain: Company domain (e.g. "acme.com") for detection.
        queue: Progress event queue for SSE streaming.

    Returns:
        Tuple of (composite_score, details_list).
        details_list: per-model summaries with mention_rate, avg_position, quote.
    """
    await queue.put({"step": "aeo", "status": "running", "detail": "Querying 2 models x 3 angles"})

    # Use pre-computed category if provided, otherwise extract it
    if not category:
        category = "software tools"  # fallback
        try:
            cat_response = await asyncio.wait_for(
                litellm.acompletion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": AEO_CATEGORY_PROMPT.format(
                        company_name=company_name, domain=domain,
                    )}],
                    api_key=os.environ.get("OPENAI_API_KEY", ""),
                    temperature=0.0,
                    max_tokens=30,
                ),
                timeout=10.0,
            )
            category = (cat_response.choices[0].message.content or category).strip().strip('".')
        except Exception:
            pass  # use fallback

    await queue.put({"step": "aeo", "status": "running", "detail": f"Category: {category}. Querying models..."})

    # Step 2: Run 3 blind prompts x 2 models concurrently
    # Using gemini-2.5-flash instead of pro (21s -> 12s) — AEO needs recall, not deep reasoning
    models = [
        ("openai/gpt-4o", "OPENAI_API_KEY"),
        ("gemini/gemini-2.5-flash", "GEMINI_API_KEY"),
    ]

    name_lower = company_name.lower()
    name_stem = re.sub(_COMMON_TLDS_RE, "", domain, flags=re.IGNORECASE).lower()
    domain_lower = domain.lower()

    def _find_mention(text: str) -> tuple[bool, int, str]:
        """Check if company is mentioned. Returns (mentioned, position, quote).

        Position = which numbered recommendation (1-based). 0 if not in a list.
        -1 if not mentioned at all.
        """
        text_lower = text.lower()
        # Check for company name or domain mention
        mentioned = (name_lower in text_lower or name_stem in text_lower or domain_lower in text_lower)
        if not mentioned:
            return False, -1, ""

        # Find the position in numbered list (look for "1.", "2.", etc. before first mention)
        # Split into lines, find which numbered item first mentions the company
        lines = text.splitlines()
        position = 0
        current_num = 0
        quote = ""
        for line in lines:
            # Match numbered items: "1.", "1)", "**1.", "### 1."
            num_match = re.match(r'^[\s#*]*(\d+)[.):\s]', line)
            if num_match:
                current_num = int(num_match.group(1))
            line_lower = line.lower()
            if name_lower in line_lower or name_stem in line_lower or domain_lower in line_lower:
                position = current_num if current_num > 0 else 1
                quote = line.strip()[:200]
                break

        return True, position, quote

    async def _query(model: str, api_key_env: str, angle_idx: int) -> dict:
        prompt = AEO_BLIND_PROMPTS[angle_idx].format(category=category)
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
            mentioned, position, quote = _find_mention(content)
            return {
                "model": model,
                "angle": angle_idx + 1,
                "mentioned": mentioned,
                "position": position,
                "quote": quote,
                "reasoning": content,
            }
        except asyncio.TimeoutError:
            return {"model": model, "angle": angle_idx + 1, "mentioned": False, "position": -1, "quote": "[timeout]", "reasoning": "[timeout]"}
        except Exception as exc:
            return {"model": model, "angle": angle_idx + 1, "mentioned": False, "position": -1, "quote": f"[error: {exc}]", "reasoning": str(exc)}

    # Fire all 6 queries concurrently
    tasks = [
        _query(model, key_env, angle)
        for model, key_env in models
        for angle in range(len(AEO_BLIND_PROMPTS))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    details: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            details.append({"model": "unknown", "angle": 0, "mentioned": False, "position": -1, "quote": f"[error: {r}]"})
        else:
            details.append(r)

    # Step 3: Compute score from mention rate + position
    valid = [d for d in details if d.get("position", -1) != -1 or d.get("mentioned") is not None]
    if not valid:
        score = 0.0
    else:
        # Mention rate: what fraction of queries mentioned the company (0-1)
        mention_rate = sum(1 for d in valid if d["mentioned"]) / len(valid)

        # Position score: average position score across queries where mentioned.
        # Position 1 = 1.0, position 2 = 0.75, position 3 = 0.5, position 4 = 0.3, 5+ = 0.15
        _pos_scores = {1: 1.0, 2: 0.75, 3: 0.5, 4: 0.3}
        position_scores = []
        for d in valid:
            if d["mentioned"]:
                pos = d.get("position", 0)
                position_scores.append(_pos_scores.get(pos, 0.15) if pos > 0 else 0.5)

        avg_position = sum(position_scores) / len(position_scores) if position_scores else 0.0

        # Final score: 60% mention rate + 40% position quality, scaled to 10
        score = round((mention_rate * 0.6 + avg_position * 0.4) * 10, 1)

    # Build per-model summary for backward compatibility with the UI
    model_summaries = []
    for model, _ in models:
        model_results = [d for d in details if d.get("model") == model]
        mentions = sum(1 for d in model_results if d["mentioned"])
        positions = [d["position"] for d in model_results if d["mentioned"] and d["position"] > 0]
        avg_pos = sum(positions) / len(positions) if positions else 0
        best_quote = next((d["quote"] for d in model_results if d.get("quote") and not d["quote"].startswith("[")), "")
        model_summaries.append({
            "model": model,
            "mentioned": mentions > 0,
            "mention_rate": f"{mentions}/{len(model_results)}",
            "avg_position": round(avg_pos, 1) if avg_pos else None,
            "confidence": round(mentions / len(model_results), 2) if model_results else 0.0,
            "quote": best_quote,
        })

    await queue.put({
        "step": "aeo",
        "status": "done",
        "detail": f"AEO score: {score:.1f}/10 (category: {category})",
    })

    return score, model_summaries


async def extract_competitors(
    raw_results: list[dict],
    company_name: str,
    category: str = "software tools",
    site_excerpt: str = "",
) -> list[dict]:
    """Extract structured competitor information from raw Tavily search results.

    Uses LiteLLM structured output via the primary model (GPT-4o) to identify
    3-5 competitors with positioning, strengths, and weaknesses.

    Args:
        raw_results: Raw Tavily search result dicts with title, url, content fields.
        company_name: The company being analyzed (to exclude from competitor list).
        category: Product category (e.g. "cashback rewards app") for filtering relevance.
        site_excerpt: Brief description of what the company does (from scraped content).

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

    company_description = site_excerpt[:800] if site_excerpt else f"A {category} company."

    prompt = COMPETITOR_EXTRACTION_PROMPT.format(
        raw_results=formatted,
        company_name=company_name,
        category=category,
        company_description=company_description,
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
    # AEO extracts its own category from name+domain (good enough for blind prompts)
    # Tavily competitor search uses category hint if available
    tavily_task = tavily_search(company_name, company_url, queue, feedback)
    firecrawl_task = firecrawl_scrape(company_url, queue)
    aeo_task = aeo_check(company_name, domain, queue)

    (press_results, competitor_raw), site_content, (aeo_score, aeo_details) = await asyncio.gather(
        tavily_task,
        firecrawl_task,
        aeo_task,
        return_exceptions=False,
    )

    # Refine company name from actual page content (handles vanity domains like joinblossomhealth.com)
    old_name = company_name
    company_name = await _extract_company_name_from_content(site_content, company_url, company_name)
    print(f"[DEBUG] Company name: '{old_name}' -> '{company_name}'", flush=True)

    # Extract accurate category from actual site content (not just domain guessing)
    category = "software tools"  # fallback
    if site_content and not site_content.startswith("[Firecrawl"):
        try:
            cat_response = await asyncio.wait_for(
                litellm.acompletion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": CATEGORY_FROM_CONTENT_PROMPT.format(
                        company_name=company_name,
                        site_excerpt=site_content[:1500],
                    )}],
                    api_key=os.environ.get("OPENAI_API_KEY", ""),
                    temperature=0.0,
                    max_tokens=30,
                ),
                timeout=10.0,
            )
            category = (cat_response.choices[0].message.content or category).strip().strip('".')
        except Exception:
            pass
    print(f"[DEBUG] Category from site content: '{category}'", flush=True)

    # Sequential: extract competitors from Tavily results (with category + site context for relevance filtering)
    await queue.put({"step": "assembly", "status": "running", "detail": "Extracting competitor profiles"})
    site_excerpt_for_competitors = site_content[:800] if site_content else ""
    competitors = await extract_competitors(competitor_raw, company_name, category=category, site_excerpt=site_excerpt_for_competitors)

    # Build press coverage list — score, filter, and deduplicate.
    # Scoring prevents false positives for generic company names (e.g. "Linear"
    # matching "Linear Technology" or "Linear (LINA) crypto token").
    bare_domain = _extract_bare_domain(company_url)
    name_lower = company_name.lower()
    domain_lower = bare_domain.lower()
    name_stem = re.sub(_COMMON_TLDS_RE, "", bare_domain, flags=re.IGNORECASE).lower()

    scored_results: list[tuple[int, dict]] = []
    seen_paths: set[str] = set()  # deduplicate by URL path
    for r in press_results:
        title = r.get("title", "")
        content = r.get("content", "")
        url = r.get("url", "")
        title_lower = title.lower()
        url_lower = url.lower()
        content_lower = content.lower()

        # Skip the company's own site — we already have site content from Firecrawl
        if domain_lower in url_lower:
            continue

        # Deduplicate: strip locale prefixes and query params, compare path
        path = re.sub(r"^https?://[^/]+", "", url_lower).split("?")[0].rstrip("/")
        path = re.sub(r"^/[a-z]{2}(-[a-z]{2})?/", "/", path)
        if path in seen_paths:
            continue
        seen_paths.add(path)

        # Score relevance — higher is better.
        # Domain mentions are the strongest disambiguation signal (e.g. "linear.app"
        # distinguishes Linear the product from "linear algebra" or "Linear Technology").
        score = 0
        # Score relevance — higher is better
        score = 0
        # Full domain in content or URL (strongest disambiguation signal)
        if domain_lower in content_lower or domain_lower in url_lower:
            score += 3
        # Company name in title
        if name_lower in title_lower or name_stem in title_lower:
            score += 2
        # Company name in content body
        if name_lower in content_lower or name_stem in content_lower:
            score += 1

        if score >= 2:
            scored_results.append((score, {
                "title": title,
                "url": url,
                "snippet": content[:300],
            }))

    # Sort by relevance score descending, take top 10
    scored_results.sort(key=lambda x: x[0], reverse=True)
    press_coverage = [item for _, item in scored_results[:10]]

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
    except (asyncio.TimeoutError, json.JSONDecodeError, Exception) as exc:
        # Fallback to basic assembly if synthesis fails
        print(f"[DEBUG] Synthesis FAILED: {type(exc).__name__}: {exc!r}", flush=True)
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
