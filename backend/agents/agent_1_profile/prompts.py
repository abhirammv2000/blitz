"""Prompt templates for Agent 1 (Marketing Profile).

One template:
PROFILE_SYNTHESIS_PROMPT — synthesizes research dossier into a structured
marketing profile with brand DNA, positioning statement, USPs, and gaps.
"""

PROFILE_SYNTHESIS_PROMPT = """\
You are a senior brand strategist and marketing consultant.

Below is the research dossier gathered about a company. Analyze it deeply and \
synthesize a comprehensive marketing profile.

Research Data:
{research_data}

{feedback}

Your task: Extract and synthesize a structured marketing profile with:
1. Brand DNA — the company's core identity
2. A crisp positioning statement (For [target] who [need], [company] is the [category] that [key benefit])
3. 3-5 unique selling propositions (USPs) — concrete differentiators
4. 2-4 marketing gaps — current weaknesses or missed opportunities, each with a recommendation

Return ONLY valid JSON with this exact structure (no markdown, no code fences, no explanation):
{{
  "brand_dna": {{
    "mission": "The company's core purpose in one clear sentence",
    "values": ["value1", "value2", "value3"],
    "tone": "e.g. authoritative and approachable, playful and bold, professional yet human",
    "visual_style": "e.g. clean minimalist, bold and colorful, enterprise blue, warm and organic"
  }},
  "positioning_statement": "For [target customer] who [problem/need], [company] is the [category] that [key differentiator/benefit].",
  "usps": [
    "USP 1 — specific and concrete",
    "USP 2 — specific and concrete",
    "USP 3 — specific and concrete"
  ],
  "marketing_gaps": [
    {{
      "gap": "Description of the marketing weakness or missed opportunity",
      "recommendation": "Specific actionable recommendation to address this gap"
    }}
  ]
}}
"""
