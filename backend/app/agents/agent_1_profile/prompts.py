"""Prompt templates for Agent 1 (Marketing Profile).

One template:
PROFILE_SYNTHESIS_PROMPT - synthesizes research dossier into a structured
marketing profile with brand DNA, positioning, audiences, competitive edges, and gaps.
"""

PROFILE_SYNTHESIS_PROMPT = """\
You are a senior brand strategist building a marketing profile for a client.

Below is the research dossier. Use SPECIFIC data from it - competitor names, \
AEO scores, press coverage themes, actual language from the company's website. \
Do not write generic filler that could apply to any company.

## Research Dossier
{research_data}

{feedback}

## Instructions

Synthesize this into a marketing profile. Rules:
- Every field must reference concrete evidence from the research above.
- If the research includes an AEO score, competitor data, press coverage, or funding info, you MUST use it.
- Do NOT write anything that could apply to any company in the same category. Be specific to THIS company.

### 1. Brand DNA
- **mission**: What the company exists to do (infer from their site copy and positioning, not a generic statement)
- **values**: 3-4 values visible in how they operate, what they emphasize on their site, or how press describes them
- **tone**: Describe their communication style based on actual site copy (e.g. "technical but conversational - uses developer slang, avoids corporate jargon")
- **voice_example**: Write one sample sentence in this company's brand voice about their product
- **visual_style**: Describe based on their site (color palette, typography feel, imagery style)

### 2. Positioning Statement
Use the format: "For [specific target] who [specific problem], [company] is the [specific category] that [specific differentiator backed by evidence]."
The differentiator must reference something concrete from the research (e.g. a metric, a partnership, a capability competitors lack).

### 3. Target Audiences (2-3)
For each audience segment:
- **segment**: Specific role + company type (not just "developers" - be precise)
- **pain_points**: 2-3 problems they face that this company solves (infer from the product's features and competitor gaps)
- **decision_drivers**: 2-3 factors that matter when they evaluate solutions in this category

### 4. USPs (3-5)
Each USP must be specific enough that it could NOT describe a competitor. Reference actual capabilities, metrics, or evidence from the research. Bad: "Easy to use". Good: "Zero-config deployments from Git push with automatic preview URLs for every PR".

### 5. Competitive Edges (2-3)
For each major competitor found in the research:
- **competitor**: Name
- **advantage**: What this company does better (reference specific competitor weaknesses from the research)
- **vulnerability**: Where this competitor is genuinely stronger (be honest)

### 6. Messaging Pillars (3-4)
Key themes that should run through all marketing content. Each pillar should connect a company strength to an audience pain point.

### 7. Marketing Gaps (3-4)
For each gap:
- **gap**: The weakness or missed opportunity
- **evidence**: Quote or cite specific data from the research (e.g. "AEO score of 4.5/10", "Competitor X has stronger Y", "Press coverage focuses on Z but not W", "$XM raised but no messaging around enterprise readiness")
- **recommendation**: Specific, actionable next step (not "improve marketing" - say exactly what to do, which channel, what message, what format)

Return ONLY valid JSON matching this structure (no markdown, no code fences):
{{
  "brand_dna": {{
    "mission": "...",
    "values": ["...", "...", "..."],
    "tone": "...",
    "voice_example": "...",
    "visual_style": "..."
  }},
  "positioning_statement": "For ... who ..., [company] is the ... that ...",
  "target_audiences": [
    {{
      "segment": "...",
      "pain_points": ["...", "..."],
      "decision_drivers": ["...", "..."]
    }}
  ],
  "usps": ["...", "...", "..."],
  "competitive_edges": [
    {{
      "competitor": "...",
      "advantage": "...",
      "vulnerability": "..."
    }}
  ],
  "messaging_pillars": ["...", "...", "..."],
  "marketing_gaps": [
    {{
      "gap": "...",
      "evidence": "...",
      "recommendation": "..."
    }}
  ]
}}
"""
