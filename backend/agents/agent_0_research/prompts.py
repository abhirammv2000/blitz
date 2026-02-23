"""Prompt templates for Agent 0 (Research).

Two templates:
1. COMPETITOR_EXTRACTION_PROMPT — extracts structured competitor data from raw Tavily results
2. AEO_CHECK_PROMPT — probes whether an LLM mentions a company in a natural customer query
"""

COMPETITOR_EXTRACTION_PROMPT = """\
You are a competitive intelligence analyst. Below are raw search results about competitors in a market.

Search Results:
{raw_results}

Company being analyzed: {company_name}

Task: Identify 3-5 distinct competitors to {company_name} from the search results.
For each competitor, provide:
- name: The company name
- positioning: 1-2 sentence description of how they position themselves
- strengths: List of 2-3 key strengths
- weaknesses: List of 2-3 known weaknesses or gaps

Return ONLY a valid JSON array with no markdown, no explanation, no code fences.
Example format:
[
  {{
    "name": "CompetitorA",
    "positioning": "A platform for X targeting Y customers.",
    "strengths": ["Strong brand", "Large customer base"],
    "weaknesses": ["Expensive", "Complex onboarding"]
  }}
]
"""

RESEARCH_SYNTHESIS_PROMPT = """\
You are a senior marketing strategist analyzing a company for a go-to-market engagement.

## Company: {company_name}
## Website: {company_url}

## Website Content (scraped)
{site_excerpt}

## Press Coverage
{press_summary}

## Competitive Landscape
{competitor_summary}

## AI Visibility (AEO Score: {aeo_score}/10)
{aeo_summary}

---

Write two outputs:

1. **SUMMARY** (2-3 paragraphs): A strategic intelligence brief covering:
   - What the company does, who they serve, and their core value proposition
   - Their market positioning vs. competitors — strengths and vulnerabilities
   - Their AI discoverability and digital presence gaps
   - One or two non-obvious strategic insights (e.g. underserved segments, messaging misalignment, untapped channels)

2. **EXECUTIVE_SUMMARY** (2-3 sentences): A punchy dashboard headline a CMO would read in 5 seconds. Lead with the most important finding, not a generic description.

Return ONLY valid JSON with no markdown, no code fences:
{{"summary": "...", "executive_summary": "..."}}
"""

AEO_CHECK_PROMPT = """\
You are a knowledgeable business advisor helping someone find the best solutions in a specific market.

A potential buyer asks: "I'm looking for the best alternatives and competitors to {company_name} ({domain}). \
What are the top tools or platforms in {company_name}'s space? Is {company_name} itself a good choice?"

Answer naturally and thoroughly. Recommend the best solutions in this company's market category. \
Mention {company_name} if you genuinely know about it — do NOT make up information.

Then, on the very last line of your response, output ONLY a JSON object (no markdown, no code fences):
{{"mentioned": true_or_false, "confidence": 0.0_to_1.0, "quote": "exact quote if mentioned, else empty string"}}

Where:
- mentioned: true if you recommended or positively referenced {company_name} or {domain} in your answer
- confidence: how well-known {company_name} is in its space (0.0 = never heard of it, 1.0 = market leader everyone knows)
- quote: the exact sentence from your answer where you discussed them, or "" if not mentioned
"""
