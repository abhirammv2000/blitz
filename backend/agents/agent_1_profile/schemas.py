"""Pydantic output schema for Agent 1 (Marketing Profile)."""

from pydantic import BaseModel


class BrandDNA(BaseModel):
    """Structured brand identity extracted from research data."""

    mission: str
    values: list[str]
    tone: str
    voice_example: str  # A sample sentence written in the brand's voice
    visual_style: str


class TargetAudience(BaseModel):
    """Primary target audience for marketing efforts."""

    segment: str  # e.g. "Mid-market SaaS engineering teams"
    pain_points: list[str]  # What problems they face that this company solves
    decision_drivers: list[str]  # What matters when they evaluate solutions


class CompetitiveEdge(BaseModel):
    """How the company is positioned against a specific competitor."""

    competitor: str
    advantage: str  # What this company does better
    vulnerability: str  # Where the competitor is stronger


class MarketingGap(BaseModel):
    """A single identified marketing gap with an actionable recommendation."""

    gap: str
    evidence: str  # What from the research supports this gap
    recommendation: str


class MarketingProfile(BaseModel):
    """Structured output from the Marketing Profile agent.

    Synthesizes research into brand identity, positioning, competitive edges,
    and actionable marketing gap analysis.
    """

    brand_dna: BrandDNA
    positioning_statement: str
    target_audiences: list[TargetAudience]  # 2-3 audiences
    usps: list[str]
    competitive_edges: list[CompetitiveEdge]  # vs top 2-3 competitors
    messaging_pillars: list[str]  # 3-4 key themes for all marketing content
    marketing_gaps: list[MarketingGap]
