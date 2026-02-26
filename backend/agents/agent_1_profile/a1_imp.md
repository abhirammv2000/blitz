# Agent 1 (Profile Creator)

## What This Agent Does

Agent 1 takes the research dossier from Agent 0 and synthesizes it into a structured marketing profile. It reads the approved research output from ChromaDB, sends it to GPT-4o with a brand strategist prompt, and produces:

- **Brand DNA** - Mission, values, tone, voice example, visual style
- **Positioning Statement** - Follows "For [target] who [need], [company] is the [category] that [differentiator]" format
- **Target Audiences** - 2-3 segments with pain points and decision drivers
- **USPs** - 3-5 concrete differentiators specific to this company
- **Competitive Edges** - How the company compares vs top 2-3 competitors (advantages and honest vulnerabilities)
- **Messaging Pillars** - 3-4 key themes for all marketing content
- **Marketing Gaps** - Weaknesses with evidence from research data and actionable recommendations

The output is stored in ChromaDB and feeds into Agent 2 (Audience Identifier) and all downstream agents.

---

## Improvements Log

### Date: 2025-02-25

---

## 1. Schema - Added Richer Output Fields

### Problem
- Only 4 fields: brand_dna, positioning_statement, usps, marketing_gaps
- No target audience detail, no competitive positioning, no brand voice examples, no messaging framework
- Downstream agents (content, sales, ads) didn't have enough to work with

### Fix
Added to `schemas.py`:
- `BrandDNA.voice_example` - A sample sentence written in the brand's voice
- `TargetAudience` - Segment name, pain points, decision drivers (2-3 audiences)
- `CompetitiveEdge` - Per-competitor advantage and vulnerability
- `MarketingGap.evidence` - What from the research supports this gap
- `messaging_pillars` - 3-4 key themes for content consistency

### Result
Output went from 4 fields to 7 top-level fields with richer sub-structures.

---

## 2. Prompt - Rewrote for Specificity and Evidence

### Problem
- Old prompt said "Analyze it deeply" with no guidance on using specific research data
- USPs were generic ("Easy to use", "Developer-friendly tools")
- Marketing gaps had no evidence backing
- Output could apply to any company in the same category

### Fix
Rewrote `PROFILE_SYNTHESIS_PROMPT` with:
- Explicit instruction to use AEO scores, competitor data, press coverage, and funding info
- Each field has detailed guidance on what "good" looks like
- USP instruction: "Each USP must be specific enough that it could NOT describe a competitor"
- Gap evidence must cite specific data ("AEO score of 4.5/10", "Competitor X has stronger Y")
- Rule: "Do NOT write anything that could apply to any company in the same category"

### Before vs After (Vercel example)

| Field | Before | After |
|-------|--------|-------|
| Values | "innovation, developer-centricity, performance" | "Developer-centric innovation, Scalability and performance, AI integration" |
| Tone | "authoritative and approachable" | "Technical yet accessible, with a focus on developer empowerment and efficiency" |
| USP | "Seamless integration with Next.js" | "Zero-config deployments from Git push with automatic preview URLs for every PR" |
| Positioning | No evidence | References "$300M investment" and Next.js integration |
| Gaps | No evidence field | Cites press coverage, competitor analysis, AEO data |

---

## 3. Generalization Testing

Tested on two different companies/industries:
- **Vercel** (developer tools / frontend cloud)
- **Ramp** (fintech / corporate expense management)

Both produced company-specific output with concrete data points, different brand voices, and industry-appropriate audiences. No hardcoded industry terms in the prompt.

---

## Files Changed

| File | Change |
|------|--------|
| `schemas.py` | Added TargetAudience, CompetitiveEdge models; added voice_example, evidence, messaging_pillars, target_audiences, competitive_edges fields |
| `prompts.py` | Rewrote PROFILE_SYNTHESIS_PROMPT with evidence requirements and field-level guidance |
| `node.py` | Simplified import (only MarketingProfile needed) |
| `test_agent1.py` | New standalone test script |
| `test_agent1_output.json` | Last test run output |

---

## Test Commands

```bash
cd backend

# Must run Agent 0 first to generate research input
python -m agents.agent_0_research.test_agent0 "https://vercel.com"

# Then run Agent 1
python -m agents.agent_1_profile.test_agent1
```
