"""Pydantic output schema for Agent 5 (Paid Ads)."""

from pydantic import BaseModel


class AdsOutput(BaseModel):
    """Structured output from the Paid Ads agent.

    Produces ad copy variants, visual direction briefs, and A/B test variations
    ready for Google, Meta, and LinkedIn campaign setup.
    """

    ad_copies: list[dict]  # [{segment, platform, headline, body, cta, character_counts}]
    ad_visuals: list[dict]  # [{segment, platform, visual_concept, color_palette, image_prompt}]
    ab_variations: list[dict]  # [{ad_copy_ref, variant_a, variant_b, test_hypothesis}]
