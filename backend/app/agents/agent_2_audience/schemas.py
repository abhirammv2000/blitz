"""Pydantic output schema for Agent 2 (Audience Intelligence)."""

from pydantic import BaseModel


class AudienceSegment(BaseModel):
    """A single synthetic audience segment with full psychographic detail."""

    name: str
    demographics: dict  # {age_range, job_titles, company_sizes, industries}
    psychographics: dict  # {values, goals, frustrations, personality_traits}
    pain_points: list[str]
    buying_triggers: list[str]
    active_channels: list[str]
    reasoning: str  # why this segment was identified from research
    fit_label: str  # "High", "Medium", or "Low"
    synthetic_attributes: dict  # generated enrichment data for demo realism


class AudienceOutput(BaseModel):
    """Structured output from the Audience Intelligence agent.

    Produces 3-5 synthetic audience segments grounded in research data.
    """

    segments: list[AudienceSegment]
