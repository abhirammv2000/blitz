"""Prompt templates for Agent 0 (Research).

Two templates:
1. COMPETITOR_EXTRACTION_PROMPT — extracts structured competitor data from raw Tavily results
2. AEO_CHECK_PROMPT — probes whether an LLM mentions a company in a natural customer query
"""

COMPETITOR_EXTRACTION_PROMPT = """\
You are a competitive intelligence analyst.

## Company being analyzed
{company_name} — a {category} company.

## What {company_name} does
{company_description}

## Raw search results (may contain noise — use your judgment)
{raw_results}

Task: Identify 3-5 distinct competitors to {company_name}.

IMPORTANT RULES:
1. A valid competitor MUST be in the same product category ({category}) and serve a similar audience.
2. Ignore companies from unrelated industries — even if they appear in the search results.
   For example, a marketing agency is NOT a competitor to a cashback app.
3. If the search results lack good competitors, USE YOUR OWN KNOWLEDGE of the {category} \
   space to identify well-known competitors. Real competitors are better than bad search results.
4. Do NOT include {company_name} itself as a competitor.

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

# ---------- AEO (Answer Engine Optimization) ----------
# Three blind prompt angles — the company name is NOT in the question.
# We feed the category description (extracted from the site) so the LLM
# answers a realistic customer query. After receiving the response we
# check whether the company was organically mentioned and at what position.

AEO_BLIND_PROMPTS = [
    # Angle 1: "Best tools" discovery query
    """\
You are a knowledgeable business advisor. A potential buyer asks:

"What are the best {category} tools or platforms available right now? \
Give me a ranked list of the top 5-8 options with a short explanation for each."

Answer naturally and thoroughly. Only recommend solutions you genuinely know about — \
do NOT make up products. Number your recommendations (1, 2, 3, …).""",

    # Angle 2: Recommendation for a specific use case
    """\
You are a tech consultant helping a mid-size company. They ask:

"We need a {category} solution. What would you recommend and why? \
List the top options with pros and cons for each."

Answer naturally. Only recommend real products you know about.""",

    # Angle 3: Comparison / "which should I pick" query
    """\
You are helping a startup founder evaluate tools. They ask:

"I'm comparing {category} solutions for my team. What are the leading \
options in this space and how do they differ? Which one would you pick?"

Answer with a practical comparison. Only mention real products.""",
]

# Prompt to extract the company's category (fast, no site content needed)
AEO_CATEGORY_PROMPT = """\
What category of product or service does {company_name} ({domain}) offer? \
Describe it in 3-8 words. Be specific (e.g. "frontend deployment and hosting platform", \
"corporate expense management software", "AI meeting notes tool"). \
Return ONLY the category, nothing else."""

CATEGORY_FROM_CONTENT_PROMPT = """\
Based on this website content, what category of product or service does {company_name} offer? \
Describe it in 3-8 words. Be specific (e.g. "consumer cashback and rewards app", \
"frontend deployment and hosting platform", "corporate expense management software"). \
Return ONLY the category, nothing else.

Website content:
{site_excerpt}"""
