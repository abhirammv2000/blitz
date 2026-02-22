"""Prompt templates for Agent 2 (Audience Intelligence).

One template:
AUDIENCE_SYNTHESIS_PROMPT — generates 3-5 synthetic audience segments grounded
in the brand's marketing profile, with citation-style reasoning.
"""

AUDIENCE_SYNTHESIS_PROMPT = """\
You are a senior audience strategist and customer intelligence expert.

Below is the marketing profile synthesized from company research. Use it to \
identify and generate 3-5 distinct, high-value audience segments.

Marketing Profile:
{profile_data}

{feedback}

Your task: Generate 3-5 synthetic audience segments. Each segment must:
- Be grounded in specific brand values, USPs, or marketing gaps from the profile above
- Include citation-style reasoning (e.g. "Based on brand value '[value]' and USP '[usp]', this segment...")
- Have realistic psychographics and demographics
- Include synthetic enrichment attributes for demo realism
- Receive a fit label: "High" (perfect ICP match), "Medium" (strong secondary), or "Low" (exploratory)

Return ONLY valid JSON with this exact structure (no markdown, no code fences, no explanation):
{{
  "segments": [
    {{
      "name": "Segment name (e.g. 'Growth-Stage SaaS CMOs')",
      "demographics": {{
        "age_range": "e.g. 35-50",
        "job_titles": ["CMO", "VP Marketing", "Head of Growth"],
        "company_sizes": ["50-200 employees", "Series A-B"],
        "industries": ["SaaS", "B2B Tech", "Fintech"]
      }},
      "psychographics": {{
        "values": ["data-driven decisions", "team empowerment", "measurable ROI"],
        "goals": ["scale pipeline efficiently", "prove marketing attribution"],
        "frustrations": ["tool sprawl", "misaligned sales-marketing", "vanity metrics"],
        "personality_traits": ["analytical", "ambitious", "collaborative"]
      }},
      "pain_points": [
        "Specific pain point 1",
        "Specific pain point 2"
      ],
      "buying_triggers": [
        "Trigger that causes them to buy",
        "Another buying trigger"
      ],
      "active_channels": ["LinkedIn", "G2", "Industry newsletters"],
      "reasoning": "Based on brand value '[specific value]' and USP '[specific usp]', this segment aligns because [specific rationale from profile data].",
      "fit_label": "High",
      "synthetic_attributes": {{
        "avg_deal_size": "$50k-$200k ARR",
        "buying_committee_size": 3,
        "sales_cycle_days": 45,
        "ltv_estimate": "$150k",
        "persona_name": "Michelle, CMO at ScaleHQ"
      }}
    }}
  ]
}}
"""
