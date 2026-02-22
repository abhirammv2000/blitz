"""Pydantic output schema for Agent 0 (Research)."""

from pydantic import BaseModel


class ResearchOutput(BaseModel):
    """Structured output from the Research agent.

    Captures company intelligence, competitive landscape, and AEO (AI Engine Optimization)
    visibility scores across frontier LLMs.
    """

    company_name: str
    company_url: str
    summary: str
    press_coverage: list[str]
    competitors: list[dict]  # [{name, positioning, strengths, weaknesses}]
    aeo_score: float  # 0-10 composite AI visibility score
    aeo_details: list[dict]  # [{model, mentioned, reasoning}]
