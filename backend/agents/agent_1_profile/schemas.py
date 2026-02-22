"""Pydantic output schema for Agent 1 (Marketing Profile)."""

from pydantic import BaseModel


class MarketingProfile(BaseModel):
    """Structured output from the Marketing Profile agent.

    Synthesizes research into a brand DNA, positioning statement, USPs,
    and actionable marketing gap analysis.
    """

    brand_dna: dict  # {mission, values, tone, visual_style}
    positioning_statement: str
    usps: list[str]
    marketing_gaps: list[dict]  # [{gap, recommendation}]
