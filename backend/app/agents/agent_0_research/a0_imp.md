# Agent 0 (Research Scout)

## What This Agent Does

Agent 0 is the first step in the Blitz pipeline. Given a company URL, it builds a research dossier by running these tasks concurrently:

1. **Tavily Search** - Finds real press coverage from major publications (TechCrunch, Forbes, CNBC, etc.) and raw competitor data
2. **Firecrawl Scrape** - Extracts the company's website content as markdown
3. **AEO Check (Answer Engine Optimization)** - Measures how visible the company is to AI models by asking blind questions ("What are the best tools in this category?") across GPT-4o and Gemini, then checking if the company appears organically and at what rank position

After the concurrent phase, it sequentially:
4. **Extracts competitors** - Uses GPT-4o to structure 3-5 competitors with positioning, strengths, and weaknesses from the Tavily results
5. **Filters press** - Deduplicates, removes the company's own site pages, and scores articles by relevance
6. **Synthesizes** - GPT-4o generates a strategic summary and executive summary from all gathered data

The output is a `ResearchOutput` object containing: company name, summary, executive summary, press coverage, site content, competitors, AEO score (0-10), and per-model AEO details.

This output feeds into Agent 1 (Profile Creator) and is stored in ChromaDB for all downstream agents to reference.

---

## Improvements Log

### Date: 2025-02-25

---

## 1. Tavily Press Search -Fixed Garbage Results

### Problem
- "Own-site" search (`include_domains=[company domain]`) returned template/product pages instead of real press (e.g. "Top 5 News Bulletin Templates" for Notion)
- External search queries were too generic (`"press coverage news announcement"`)
- Company's own site pages passed through the filter (domain match = auto-pass)
- Duplicate results from different locales (e.g. notion.so vs notion.com/zh-cn)

### Fix
- **Replaced own-site search** with a news-publication-targeted search using `include_domains` for 20 major tech/business outlets (TechCrunch, CNBC, Forbes, VentureBeat, etc.)
- **Added domain to all queries** for disambiguation (e.g. `"Linear" linear.app` ensures results are about Linear the product, not "Linear Technology" the semiconductor company)
- **Excluded company's own domain** from press results -we already get site content from Firecrawl
- **Deduplicated by URL path** -strips locale prefixes (`/en-gb/`, `/zh-cn/`) and query params before comparing
- **Score-based relevance filter**: domain in content (+3) > name in title (+2) > name in body (+1), minimum score 2 to include

### Result
- Before: 8/8 press results were Notion's own template pages
- After: TechCrunch, CNBC, NYTimes, Business Insider, Forbes -zero false positives
- Tested on: notion.so, stripe.com, linear.app, vercel.com

---

## 2. AEO Scoring -Rewrote from Self-Report to Blind Recall

### Problem (old system)
- Asked each LLM directly: "Is {company} a good choice?" -primed the model to say yes
- LLM self-reported `confidence` was unreliable (Vercel 0.90, Ramp 0.90 -no differentiation)
- Only 2 queries total (1 per model) -coarse granularity
- Score clustered at the top: anything the LLM had heard of got ~9/10

### Fix (new system)

**Blind prompts** -company name is NOT in the question:
1. Extract product category from company name + domain (fast gpt-4o-mini call, ~2s)
2. Ask 3 different customer-style questions per model (6 total, concurrent):
   - "What are the best {category} tools?" (discovery)
   - "We need a {category} solution, what do you recommend?" (recommendation)
   - "I'm comparing {category} solutions, which should I pick?" (comparison)
3. Check if the company appears organically in each response
4. Score based on **mention position** (listed #1 = 1.0, #2 = 0.75, #3 = 0.5, #4 = 0.3, #5+ = 0.15)

**Score formula**: `(mention_rate × 0.6 + avg_position_score × 0.4) × 10`

**Models**: GPT-4o + Gemini-2.5-flash (switched from 2.5-pro to save ~10s)

### Result

| Company | Old Score | New Score | Interpretation |
|---------|-----------|-----------|----------------|
| Vercel | 9.5 | **10.0** | Market leader, #1 in all queries |
| Ramp | 9.2 | **7.0** | Known but not dominant (GPT-4o: 1/3, pos #3) |
| Granola | 2.0 | **0.0** | Neither model mentions it organically |

Clear three-tier differentiation: leaders (8-10), known (5-8), niche (0-4).

---

## 4. Performance

| Metric | Before all changes | After all changes |
|--------|-------------------|-------------------|
| Full Agent 0 | ~26s | ~38s |
| AEO alone | ~8s (2 LLM calls) | ~20s (7 LLM calls) |
| Press quality | Garbage (template pages) | Real journalism |
| AEO differentiation | Vercel 9.5 vs Ramp 9.2 (useless) | Vercel 10.0 vs Ramp 7.0 (meaningful) |

AEO is ~12s slower due to 6 blind queries instead of 2 direct queries, but the quality improvement justifies it. Tavily + Firecrawl run concurrently during the AEO wait, so net pipeline impact is ~10s.

### Speed optimizations applied
- Category extraction uses `gpt-4o-mini` instead of `gpt-4o` (~2s saved)
- Blind queries use `gemini-2.5-flash` instead of `gemini-2.5-pro` (~10s saved)
- All 6 blind queries fire concurrently
- Tavily + Firecrawl + AEO all run concurrently (AEO no longer waits for site content)

---

## Files Changed

| File | Change |
|------|--------|
| `research.py` | Rewrote `tavily_search()` queries, press filter, and `aeo_check()` |
| `prompts.py` | Replaced `AEO_CHECK_PROMPT` with `AEO_BLIND_PROMPTS` (3 angles) + `AEO_CATEGORY_PROMPT` |
| `schemas.py` | No changes (aeo_details field still `list[dict]`, structure changed but compatible) |
| `test_agent0.py` | New standalone test script, `load_dotenv(override=True)` |

---

## Test Commands

```bash
cd backend

# Full Agent 0 test
python test_agent0.py "https://vercel.com"

# AEO-only comparison
python -c "
import asyncio, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)
from agents.agent_0_research.research import aeo_check
from agents.agent_0_research.progress import get_queue

async def test(name, domain):
    q = get_queue(f'test-{name}')
    score, details = await aeo_check(name, domain, q)
    print(f'{name}: {score}/10')
    for d in details:
        print(f'  {d[\"model\"]}: {d[\"mention_rate\"]} mentions, pos={d[\"avg_position\"]}')

asyncio.run(test('Vercel', 'vercel.com'))
"
```
