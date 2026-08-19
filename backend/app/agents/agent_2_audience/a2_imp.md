# Agent 2 (Audience Identifier)

## What This Agent Does

Agent 2 takes the research dossier (Agent 0) and marketing profile (Agent 1) and generates 4-5 synthetic audience segments. Each segment includes:

- **Demographics** - Age range, job titles, company sizes, industries
- **Psychographics** - Values, goals, frustrations, personality traits
- **Pain points** - Specific to the segment's daily reality
- **Buying triggers** - Events that cause them to search for a solution now
- **Active channels** - Specific platforms, communities, and events where this segment can be reached
- **Reasoning** - Why this segment was identified, citing specific data from the research
- **Fit label** - High (ideal ICP), Medium (strong secondary), or Low (exploratory opportunity)
- **Synthetic attributes** - Deal size, sales cycle, LTV, buying committee size, persona name

The output feeds into Agent 3 (Content Strategist) and Agent 4 (Sales Agent).

---

## Improvements Log

### Date: 2025-02-25

---

## 1. Added Agent 0 Research as Input

### Problem
- Agent 2 only read Agent 1's marketing profile from ChromaDB
- Lost access to competitor data, AEO scores, press coverage, and site content
- Less data = more generic segments

### Fix
- `node.py` now reads both `research_decision` (Agent 0) and `profile` (Agent 1) from ChromaDB
- Both are passed into the prompt so the LLM can reference competitor names, funding data, press themes, and AEO visibility

---

## 2. Prompt Rewrite - Seven Explicit Rules

### Problem
- Pain points were copied verbatim from Agent 1's output
- Buying triggers were needs ("Need for better integration") not events
- Channels were generic B2B boilerplate ("LinkedIn", "Industry conferences")
- All segments got "High" fit label
- Psychographics were identical across segments

### Fix
Added 7 explicit rules to the prompt:
1. Segments must be meaningfully different (vary seniority, company stage, industry)
2. Pain points must be NEW - not copied from the marketing profile
3. Buying triggers must be EVENTS with examples of good vs bad
4. Channels must be SPECIFIC - named communities, subreddits, conferences
5. Fit labels must be distributed - at least one Medium or Low
6. Reasoning must cite specific data from the inputs
7. Psychographics must differ between segments

### Before vs After (Ramp)

| Aspect | Before | After |
|--------|--------|-------|
| Segments | 3 (all High) | 4 (2 High, 1 Medium, 1 Low) |
| Buying triggers | "Need for better integration" | "Raised Series B and need to professionalize expense tracking before board audit" |
| Channels | "LinkedIn, Finance industry forums" | "Modern CFO Slack community", "r/fintech subreddit", "SaaStr Annual" |
| Psychographics | Same across all segments | Different per segment (startup = "move fast" vs CFO = "precision, control") |
| Pain points | Copied from Agent 1 | New and segment-specific |

---

## Files Changed

| File | Change |
|------|--------|
| `prompts.py` | Rewrote AUDIENCE_SYNTHESIS_PROMPT with 7 rules, added research_data input |
| `node.py` | Now reads both research_decision and profile from ChromaDB |
| `test_agent2.py` | New standalone test script, feeds both Agent 0 and Agent 1 data |
| `test_agent2_output.json` | Last test run output |

---

## Test Commands

```bash
cd backend

# Must run Agent 0 and Agent 1 first
python -m agents.agent_0_research.test_agent0 "https://ramp.com"
python -m agents.agent_1_profile.test_agent1

# Then run Agent 2
python -m agents.agent_2_audience.test_agent2
```
