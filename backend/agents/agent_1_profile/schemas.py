"""Pydantic output schema for Agent 1 (Marketing Profile)."""

from pydantic import BaseModel


class BrandDNA(BaseModel):
    """Structured brand identity extracted from research data."""

    mission: str
    values: list[str]
    tone: str
    visual_style: str


class MarketingGap(BaseModel):
    """A single identified marketing gap with an actionable recommendation."""

    gap: str
    recommendation: str


class MarketingProfile(BaseModel):
    """Structured output from the Marketing Profile agent.

    Synthesizes research into a brand DNA, positioning statement, USPs,
    and actionable marketing gap analysis.
    """

    brand_dna: BrandDNA
    positioning_statement: str
    usps: list[str]
    marketing_gaps: list[MarketingGap]
