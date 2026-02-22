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

AEO_CHECK_PROMPT = """\
You are a potential customer researching solutions for your business.

Question: "What are the best AI-powered marketing automation tools for {company_name}'s use case? \
Are there any tools specifically for companies like {company_name} at {domain}?"

Answer the question naturally as a knowledgeable advisor would. Then, on the very last line of your response, \
output ONLY a JSON object (no markdown, no code fences) with this exact structure:
{{"mentioned": true_or_false, "confidence": 0.0_to_1.0, "quote": "exact quote if mentioned, else empty string"}}

Where:
- mentioned: true if you referenced {company_name} or {domain} as a recommended solution
- confidence: your confidence level that {company_name} is well-known in the AI marketing space (0.0 = unknown, 1.0 = very well known)
- quote: the exact text from your answer where you mentioned them, or "" if not mentioned
"""
