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
        "Directional side-lighting casting soft graphite shadows across the page. "
        "Visible paper texture and slight smudges for authenticity. "
        "Raw, experimental, idea-driven aesthetic — like a brainstorming sketch, NOT a polished render. "
        "No photographic elements, no color fills. Square 1:1 composition."
    ),
    "bauhaus": (
        "Bauhaus-inspired poster design: functional, geometric, and minimal. "
        "Primary color palette (red, blue, yellow) on white or black backgrounds. "
        "Grid systems, bold sans-serif typography placeholders, circles/triangles/squares as compositional elements. "
        "Flat even lighting, hard edges, matte surface finish with no reflections. "
        "Clean lines, flat shapes, no gradients, no photographic elements. "
        "Rational and structured — form follows function. Square 1:1 composition."
    ),
    "japandi": (
        "Japandi minimalist aesthetic fusing Japanese wabi-sabi with Scandinavian functionality. "
        "Neutral palette: warm beige, soft grey, cream, muted earth tones. "
        "Clean sans-serif typography placeholders, generous whitespace, organic soft curves. "
        "Natural material textures (light wood grain, linen, ceramic) with subtle tactile depth. "
        "Soft diffused overhead lighting, gentle ambient shadows, no harsh contrasts. "
        "Calm, peaceful, intentional — no clutter, no bright colors, no photographic people. Square 1:1 composition."
    ),
    "editorial_3d": (
        "Soft 3D render with matte clay-like materials and smooth rounded forms. "
        "Pastel gradient backgrounds (lavender to peach, mint to sky blue). "
        "Subtle ambient occlusion shadows, soft studio lighting from upper-left. "
        "Isometric or slightly elevated camera angle. "
        "Modern SaaS/startup aesthetic — friendly, approachable, polished but not hyper-realistic. "
        "No photographic textures, no harsh specular highlights. Square 1:1 composition."
    ),
    "risograph": (
        "Risograph print aesthetic: limited color overlaps creating unexpected secondary hues. "
        "Visible halftone dot patterns, slight ink misregistration between layers. "
        "Grain and paper texture throughout — kraft or off-white stock. "
        "Flat shapes with imperfect edges, retro print-shop warmth. "
        "Bold, graphic, lo-fi charm — like a hand-pulled zine poster. "
        "No photographic elements, no smooth gradients, no digital perfection. Square 1:1 composition."
    ),
}

DEFAULT_IMAGE_STYLE = "conceptual_sketch"

IMAGE_PROMPT_SYNTHESIS = """\
You are an expert visual director for digital advertising. Your job is to write rich, \
detailed image generation prompts for DALL-E 3 — each grounded in the company's real identity.

## Company Research
{research_data}

## Ads to generate image prompts for
{ads_json}

## Visual Style
{style_directive}

## Prompt Formula
Each prompt MUST follow this structure in 3-5 sentences:
1. **Subject & focal metaphor** — the central visual element representing the ad's concept
2. **Environment & setting** — where the subject exists (abstract space, textured background, scene)
3. **Style & materials** — match the Visual Style above precisely (medium, texture, finish)
4. **Lighting & mood** — specify direction (e.g. "soft top-left key light"), quality (diffused, dramatic), and emotional tone
5. **Composition & camera** — angle (bird's-eye, eye-level, isometric), depth of field, foreground/background relationship

## Color Integration
- Each ad entry includes a `color_palette` array of hex colors. Weave these brand colors naturally into the prompt (e.g. "dominant #3B82F6 blue gradient background", "accents of #F59E0B amber on the focal element").
- If the palette is empty, derive colors from the company's brand identity in the research.

## Uniqueness Rules
- Every prompt MUST use a DIFFERENT focal metaphor AND a DIFFERENT composition/camera angle.
- No two prompts should share the same primary visual element or spatial arrangement.

## What to AVOID (include as negative guidance in each prompt)
- Do NOT include any text, words, letters, numbers, logos, or watermarks in the image.
- Do NOT render realistic human hands, fingers, or faces.
- Do NOT create cluttered compositions — keep a clear focal hierarchy.
- Do NOT use photographic realism unless the style explicitly calls for it.

Return ONLY a JSON array of objects, one per ad, in the same order as the input:
[
  {{"ref": "segment + platform or ad_copy_ref + variant", "image_prompt": "the prompt"}}
]
No markdown, no explanation.
"""
