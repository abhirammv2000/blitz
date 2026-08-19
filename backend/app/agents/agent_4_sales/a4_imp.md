# Agent 4 (Sales Enablement)

## What This Agent Does

Agent 4 generates a complete sales enablement toolkit from Agent 1's profile and Agent 2's audience segments. It makes a single GPT-4o call to produce:

1. **Email sequences** — 3-step consultative outreach per segment (Insight → Value → Ask)
2. **LinkedIn templates** — connection request + 2 follow-ups per segment
3. **Lead scoring** — Hot/Warm/Cold tiers with behavioral signals
4. **Pipeline stages** — 4-stage funnel (prospect → contacted → engaged → converted)

Unlike Agent 3 (Content), Agent 4 does NOT read Agent 0's research data — it only needs the brand profile and audience segments.

---

## Key Design Decisions

### Consultative Outreach Pattern
The email sequences enforce a strict Insight→Value→Ask progression:
- Step 1: Share an industry observation. No product mention.
- Step 2: Connect insight to a benefit. Soft product reference.
- Step 3: Low-friction ask (demo, quick call).

This avoids the typical cold-email failure mode where the first touch is a pitch.

### LinkedIn Character Limit
Connection requests are constrained to 300 chars (LinkedIn's actual limit). The prompt enforces this and the test validates it.

### Single LLM Call
Same pattern as Agent 3 — one prompt produces all four asset types to ensure consistency across email tone, LinkedIn voice, and pipeline definitions.

---

## Test Results (Ramp — 2025-02-26)

| Metric | Value |
|--------|-------|
| Time | 26.4s |
| Email sequences | 3 (one per segment, 3 emails each) |
| LinkedIn templates | 3 |
| Lead scoring tiers | 3 (Hot, Warm, Cold) |
| Pipeline stages | 4 |

### Quality Observations
- Email delays followed the spec: step 1 = 0d, step 2 = 3-5d, step 3 = 4-5d
- LinkedIn connection requests: 80-91 chars (well under 300 limit)
- Persona names from audience segments (Alex, Jamie, Morgan) used correctly in emails and LinkedIn
- Lead scoring signals are behavioral (not demographic) — good for actual scoring
- Pipeline stages have clear entry/exit criteria

### All Segments Covered

| Segment | Emails | LinkedIn |
|---------|--------|----------|
| Series B SaaS Finance Leads | ✓ | ✓ |
| Small Business Owners in Retail | ✓ | ✓ |
| Enterprise CFOs in Manufacturing | ✓ | ✓ |

---

## Files

| File | Purpose |
|------|---------|
| `node.py` | LangGraph node |
| `prompts.py` | `SALES_SYNTHESIS_PROMPT` with consultative voice rules |
| `schemas.py` | `SalesOutput` + nested models (EmailSequence, LinkedInTemplate, LeadScoringTier, PipelineStage) |
| `test_agent4.py` | Standalone test — reads agent 1-2 outputs, calls GPT-4o directly |

---

## Test Commands

```bash
cd backend

# Full Agent 4 test (requires agent 1-2 outputs to exist)
python -m agents.agent_4_sales.test_agent4
```
