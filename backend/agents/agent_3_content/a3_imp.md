# Agent 3 (Content Strategist)

## What This Agent Does

Agent 3 generates a full content marketing package from the outputs of Agents 0–2. It reads:

1. **Agent 0's research dossier** — competitors, press coverage, AEO data
2. **Agent 1's marketing profile** — brand DNA, tone, voice, USPs, gaps
3. **Agent 2's audience segments** — personas with pain points and buying triggers

It makes a single GPT-4o call with a heavily-constrained prompt (9 quality rules) to produce:

- **Social posts** — 3 per segment (LinkedIn, Twitter, Instagram), each with a different hook structure
- **Email campaigns** — 1 per segment, human-sounding with persona-name greetings
- **Blog outlines** — 1 per segment, varied formats (listicle, comparison, how-to, etc.)
- **Content calendar** — ~10 entries across 4 weeks, mixing segments and channels

The output is a `ContentOutput` Pydantic model with nested typed models (no loose dicts).

This output feeds into the frontend wizard for HITL review and is stored in ChromaDB for downstream agents.

---

## Key Design Decisions

### Single LLM Call
Unlike Agent 0 (which runs multiple concurrent tasks), Agent 3 uses one large prompt that produces all four asset types at once. This ensures cross-referencing — the calendar can reference blog titles and email subjects by name.

### 9 Quality Rules in the Prompt
The prompt embeds strict rules to prevent common LLM content generation failures:
- Brand voice enforcement (no generic "streamline" / "revolutionize" language)
- Real competitor names required (grounded in Agent 0 data)
- Varied hook structures per post (not the same pain→solution→CTA pattern)
- Platform-specific constraints (LinkedIn 150-200 words, Twitter <280 chars)
- Human-sounding emails (no "Dear valued customer" energy)

### HITL Reject Loop
The LangGraph node implements approve/edit/override/reject. On reject, user feedback is injected into the prompt and the LLM re-runs. This is the same pattern used by Agents 1 and 2.

---

## Test Results (Ramp — 2025-02-26)

| Metric | Value |
|--------|-------|
| Time | 28.1s |
| Social posts | 9 (3 segments × 3 platforms) |
| Email campaigns | 3 |
| Blog outlines | 3 |
| Calendar entries | 10 |

### Segment Coverage

| Segment | Posts | Emails | Blogs | Calendar |
|---------|-------|--------|-------|----------|
| Series B SaaS Finance Leads | ✓ | ✓ | ✓ | ✓ |
| Small Business Owners in Retail | ✓ | ✓ | ✓ | ✓ |
| Enterprise CFOs in Manufacturing | ✓ | ✓ | ✓ | — |

The calendar caps at ~10 entries, so the third segment doesn't get calendar slots. This is acceptable — the calendar is a starting template, not a rigid plan.

### Quality Observations
- LinkedIn posts hit the 150-200 word range with narrative arcs
- Twitter posts stayed under 280 chars
- Emails used persona names (Alex, Jamie, Morgan) from audience segments
- Blog outlines varied structure (how-to, listicle, optimization guide)
- Hashtags were industry-specific, not generic

---

## Files

| File | Purpose |
|------|---------|
| `node.py` | LangGraph node with HITL reject loop |
| `prompts.py` | Single `CONTENT_SYNTHESIS_PROMPT` with 9 quality rules |
| `schemas.py` | `ContentOutput` + nested models (SocialPost, EmailCampaign, BlogOutline, CalendarEntry) |
| `test_agent3.py` | Standalone test — reads agent 0-2 outputs, calls GPT-4o directly |

---

## Test Commands

```bash
cd backend

# Full Agent 3 test (requires agent 0-2 outputs to exist)
python -m agents.agent_3_content.test_agent3
```
