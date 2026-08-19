"""Pydantic output schema for Agent 0 (Research)."""

from pydantic import BaseModel


class ResearchOutput(BaseModel):
    """Structured output from the Research agent.

    Captures company intelligence, competitive landscape, and AEO (AI Engine Optimization)
    visibility scores across frontier LLMs.

    Fields:
        company_name: Extracted company name from URL.
        company_url: The original URL submitted by the user.
        summary: 1-2 paragraph narrative summary of the company.
        executive_summary: 2-3 sentence summary with key stats for dashboard display.
        press_coverage: List of press/news items with title, url, snippet.
        site_content: Raw markdown from Firecrawl scrape, used downstream by other agents.
        competitors: List of competitor dicts with name, positioning, strengths, weaknesses.
        aeo_score: 0-10 composite AI visibility score (sum of confidence * 5 per model).
        aeo_details: Per-model AEO results [{model, mentioned, confidence, quote}].
    """

    company_name: str
    company_url: str
    summary: str
    executive_summary: str
    press_coverage: list[dict]  # [{title, url, snippet}]
    site_content: str  # Firecrawl markdown
    competitors: list[dict]  # [{name, positioning, strengths, weaknesses}]
    aeo_score: float  # 0-10 composite AI visibility score
    aeo_details: list[dict]  # [{model, mentioned, confidence, quote}]
