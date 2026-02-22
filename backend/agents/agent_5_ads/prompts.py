"""Prompt templates for Agent 5 (Paid Ads)."""


ADS_SYNTHESIS_PROMPT = """You are an expert paid advertising strategist. Given a brand marketing profile and audience segments, generate platform-specific ad copy and visual direction for Google Ads, Meta Ads, and LinkedIn Ads.

## Brand Marketing Profile
{profile_data}

## Audience Segments
{audience_data}

{feedback}

## Instructions

For each audience segment and each platform (Google Ads, Meta Ads, LinkedIn Ads), produce:
1. **Ad copy** — platform-adapted tone:
   - Google Ads: keyword-focused, intent-driven, concise headlines
   - Meta Ads: emotional, visual storytelling, conversational body copy
   - LinkedIn Ads: professional, ROI-focused, authority-building

2. **Visual direction** — abstract and branded visual concepts with color palette and image prompt

3. **A/B variations** — 2-3 variations per ad testing DIFFERENT selling angles AND tones:
   - Variation A: rational/benefit-led angle
   - Variation B: emotional/aspiration angle
   - Variation C (optional): social proof / authority angle
   Each variation must include an `image_prompt` field describing the abstract branded visual (NOT literal product shots).

## Image Style Rules for image_prompt fields
Use this style for all image prompts: "Bold colors, geometric shapes, brand-aligned, abstract and conceptual, NOT literal product shots, minimal text overlay, square 1:1 composition, no photographic people."

## Output Format
Return ONLY valid JSON matching this exact schema — no markdown, no explanation:

{
  "ad_copies": [
    {
      "segment": "segment name",
      "platform": "Google Ads | Meta Ads | LinkedIn Ads",
      "headline": "Max 30 chars for Google, 40 for Meta/LinkedIn",
      "body": "Ad body copy",
      "cta": "Call to action text"
    }
  ],
  "ad_visuals": [
    {
      "segment": "segment name",
      "platform": "Google Ads | Meta Ads | LinkedIn Ads",
      "visual_concept": "Abstract visual concept description",
      "color_palette": ["#hex1", "#hex2", "#hex3"],
      "image_prompt": "DALL-E 3 prompt for abstract branded visual",
      "image_url": null
    }
  ],
  "ab_variations": [
    {
      "ad_copy_ref": "segment + platform reference",
      "variant_label": "A | B | C",
      "headline": "Variant headline",
      "body": "Variant body copy",
      "cta": "Variant CTA",
      "test_hypothesis": "What this variant tests vs. the control",
      "image_prompt": "DALL-E 3 prompt for this variation's abstract branded visual",
      "image_url": null
    }
  ]
}
"""


def build_image_prompt(visual_concept: str, brand_tone: str, color_palette: list[str]) -> str:
    """Build a DALL-E 3 prompt from a visual concept, brand tone, and colors.

    Adds style constraints ensuring abstract/branded style without literal
    product photography or photographic people.

    Args:
        visual_concept: The ad's visual concept description from the LLM output.
        brand_tone: Brand tone descriptor (e.g. "professional", "energetic").
        color_palette: List of hex color strings from the visual direction.

    Returns:
        A DALL-E 3 ready prompt string with style constraints appended.
    """
    colors_str = ", ".join(color_palette) if color_palette else "vibrant brand colors"
    return (
        f"{visual_concept}. "
        f"Brand tone: {brand_tone}. "
        f"Color palette: {colors_str}. "
        "Abstract and branded. Bold geometric shapes. Minimal text. "
        "Square 1:1 composition. No photographic people. "
        "Digital art style, high contrast, modern marketing aesthetic."
    )
