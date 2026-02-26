"""Prompt templates for Agent 5 (Paid Ads).

Two prompts:
ADS_SYNTHESIS_PROMPT — generates ad copy, visual concepts, and A/B variations.
IMAGE_PROMPT_SYNTHESIS — takes research + visual concepts and produces unique,
    grounded image generation prompts for each ad.
"""


ADS_SYNTHESIS_PROMPT = """You are an expert paid advertising strategist. Given a company's research dossier, brand marketing profile, and audience segments, generate platform-specific ad copy and visual direction for Google Ads, Meta Ads, and LinkedIn Ads.

## Research Dossier (competitors, press, funding, AEO)
{research_data}

## Brand Marketing Profile
{profile_data}

## Audience Segments
{audience_data}

{feedback}

## Instructions

For each audience segment and each platform (Google Ads, Meta Ads, LinkedIn Ads), produce:
1. **Ad copy** — platform-adapted tone:
   - Google Ads: keyword-focused, intent-driven, concise headlines
   - Meta Ads: emotional, visual storytelling, conversational body copy (125-250 characters for body)
   - LinkedIn Ads: professional, ROI-focused, authority-building (100-200 characters for body)

2. **Visual direction** — abstract and branded visual concepts with color palette and image prompt

3. **A/B variations** — 2-3 variations per ad for EVERY segment testing DIFFERENT selling angles AND tones:
   - Variation A: rational/benefit-led angle
   - Variation B: emotional/aspiration angle
   - Variation C (optional): social proof / authority angle
   Each variation must include an `image_prompt` field describing the abstract branded visual (NOT literal product shots).

## GROUNDING RULES — ad copy MUST reference specific facts from the Research Dossier above:
- Reference specific competitors by name (e.g. "Unlike [Competitor], we...")
- Cite real product stats, user counts, or performance metrics from the research (e.g. "50,000+ teams", "1.5% cash back", "75% faster close")
- Reference press milestones or funding rounds when relevant for authority ads
- Do NOT fabricate statistics — only use numbers found in the research dossier or profile

## Image Prompts
Leave all image_prompt fields as empty strings (""). Image prompts will be generated in a separate step.

## Output Format
Return ONLY valid JSON matching this exact schema — no markdown, no explanation:

{{
  "ad_copies": [
    {{
      "segment": "segment name",
      "platform": "Google Ads | Meta Ads | LinkedIn Ads",
      "headline": "Max 30 chars for Google, 40 for Meta/LinkedIn",
      "body": "Ad body copy",
      "cta": "Call to action text"
    }}
  ],
  "ad_visuals": [
    {{
      "segment": "segment name",
      "platform": "Google Ads | Meta Ads | LinkedIn Ads",
      "visual_concept": "Abstract visual concept description",
      "color_palette": ["#hex1", "#hex2", "#hex3"],
      "image_prompt": "DALL-E 3 prompt for abstract branded visual",
      "image_url": null
    }}
  ],
  "ab_variations": [
    {{
      "ad_copy_ref": "segment + platform reference",
      "variant_label": "A | B | C",
      "headline": "Variant headline",
      "body": "Variant body copy",
      "cta": "Variant CTA",
      "test_hypothesis": "What this variant tests vs. the control",
      "image_prompt": "DALL-E 3 prompt for this variation's abstract branded visual",
      "image_url": null
    }}
  ]
}}
"""


IMAGE_STYLES: dict[str, str] = {
    "conceptual_sketch": (
        "Rough hand-drawn conceptual sketch on cream sketch paper. "
        "Pencil and ink lines, crosshatching for shading, greyscale tones with subtle warm undertones. "
        "Loose annotations and arrows as if from a designer's notebook. "
        "Raw, experimental, idea-driven aesthetic — like a brainstorming sketch, NOT a polished render. "
        "No photographic elements, no color fills. Square 1:1 composition."
    ),
    "bauhaus": (
        "Bauhaus-inspired poster design: functional, geometric, and minimal. "
        "Primary color palette (red, blue, yellow) on white or black backgrounds. "
        "Grid systems, bold sans-serif typography placeholders, circles/triangles/squares as compositional elements. "
        "Clean lines, flat shapes, no gradients, no photographic elements. "
        "Rational and structured — form follows function. Square 1:1 composition."
    ),
    "japandi": (
        "Japandi minimalist aesthetic fusing Japanese wabi-sabi with Scandinavian functionality. "
        "Neutral palette: warm beige, soft grey, cream, muted earth tones. "
        "Clean sans-serif typography placeholders, generous whitespace, organic soft curves. "
        "Natural material textures (light wood grain, linen, ceramic). "
        "Calm, peaceful, intentional — no clutter, no bright colors, no photographic people. Square 1:1 composition."
    ),
}

DEFAULT_IMAGE_STYLE = "conceptual_sketch"

IMAGE_PROMPT_SYNTHESIS = """\
You are an expert visual director for digital advertising. Your job is to write unique, \
specific image generation prompts for each ad — grounded in the company's real identity.

## Company Research
{research_data}

## Ads to generate image prompts for
{ads_json}

## Visual Style
{style_directive}

## Rules
- Each prompt must be a COMPLETE, standalone image generation instruction (1-2 sentences).
- Incorporate the ad's visual_concept into every prompt.
- Reference the company's actual brand identity, product category, or industry from the research.
- ALWAYS apply the Visual Style above — every prompt must match that aesthetic.
- Every prompt MUST be unique — different composition, different metaphor, different focal element.

Return ONLY a JSON array of objects, one per ad, in the same order as the input:
[
  {{"ref": "segment + platform or ad_copy_ref + variant", "image_prompt": "the prompt"}}
]
No markdown, no explanation.
"""
