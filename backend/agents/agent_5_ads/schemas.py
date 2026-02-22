"""Pydantic output schema for Agent 5 (Paid Ads)."""

from pydantic import BaseModel


class AdCopy(BaseModel):
    """Ad copy for a specific audience segment and platform."""

    segment: str
    platform: str
    headline: str
    body: str
    cta: str


class AdVisual(BaseModel):
    """Visual direction brief for a specific segment and platform."""

    segment: str
    platform: str
    visual_concept: str
    color_palette: list[str]
    image_prompt: str
    image_url: str | None = None


class AbVariation(BaseModel):
    """A/B test variation with its own ad copy and AI-generated image."""

    ad_copy_ref: str
    variant_label: str
    headline: str
    body: str
    cta: str
    test_hypothesis: str
    image_prompt: str
    image_url: str | None = None


class AdsOutput(BaseModel):
    """Structured output from the Paid Ads agent.

    Produces ad copy variants, visual direction briefs, and A/B test variations
    ready for Google, Meta, and LinkedIn campaign setup.

    image_url fields on AdVisual and AbVariation are populated after the LLM
    generates the ad copy — DALL-E 3 image generation runs as a separate async step.
    """

    ad_copies: list[AdCopy]
    ad_visuals: list[AdVisual]
    ab_variations: list[AbVariation]
