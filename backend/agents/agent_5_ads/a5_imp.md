# Agent 5 (Paid Ads)

## What This Agent Does

Agent 5 generates a complete paid advertising toolkit from Agent 1's profile and Agent 2's audience segments. Single GPT-4o call produces:

1. **Ad copies** — one per segment × platform (Google Ads, Meta Ads, LinkedIn Ads)
2. **Ad visuals** — visual direction briefs with color palettes and DALL-E 3 image prompts
3. **A/B variations** — 2-3 per ad testing different selling angles (rational, emotional, social proof)

Image generation is **not** automatic — the LLM produces `image_prompt` fields that users can edit in the UI before triggering DALL-E 3 via `POST /ads/{run_id}/generate-image` (capped at 3 per run).

---

## Key Design Decisions

### User-Triggered Image Generation
Earlier versions auto-generated images during the agent run. This was changed because:
- DALL-E 3 is slow (~15-20s per image) and expensive
- Users often want to edit prompts before generating
- Capping at 3 images per run controls costs

### Platform-Specific Ad Tone
The prompt enforces different tones per platform:
- **Google Ads**: keyword-focused, intent-driven, concise headlines (≤30 chars)
- **Meta Ads**: emotional, visual storytelling, conversational
- **LinkedIn Ads**: professional, ROI-focused, authority-building

### Abstract Visual Style
All image prompts enforce "bold colors, geometric shapes, abstract and conceptual, NOT literal product shots" to avoid generic stock-photo aesthetics.

---

## Test Results (Ramp — 2025-02-26)

| Metric | Value |
|--------|-------|
| Time | 55.9s |
| Ad copies | 12 (4 segments × 3 platforms) |
| Ad visuals | 12 |
| A/B variations | 9 (3 per ad, testing rational/emotional/social proof) |

### Segment Coverage

| Segment | Copies | Visuals |
|---------|--------|---------|
| Series B SaaS Finance Leads | ✓ | ✓ |
| Small Business Owners in Retail | ✓ | ✓ |
| Enterprise CFOs in Manufacturing | ✓ | ✓ |
| Startup Founders in Tech | ✓ | ✓ |

Note: 4 segments appeared (vs 3 in upstream agents) — the LLM inferred an additional "Startup Founders in Tech" segment from the profile data. This is harmless but worth noting.

### Quality Observations
- All Google Ads headlines under 30 chars
- All 3 platforms covered in both copies and visuals
- A/B variations follow A (rational) / B (emotional) / C (social proof) pattern
- Every visual and A/B variation has an image_prompt (0 missing)
- Color palettes are segment-themed (blue for SaaS, green for retail, red for enterprise, orange for startups)

---

## Files

| File | Purpose |
|------|---------|
| `node.py` | LangGraph node with HITL reject loop + `generate_ad_image()` helper |
| `prompts.py` | `ADS_SYNTHESIS_PROMPT` + `build_image_prompt()` helper |
| `schemas.py` | `AdsOutput` + nested models (AdCopy, AdVisual, AbVariation) |
| `test_agent5.py` | Standalone test — reads agent 1-2 outputs, calls GPT-4o directly |

---

## Test Commands

```bash
cd backend

# Full Agent 5 test (requires agent 1-2 outputs to exist)
python -m agents.agent_5_ads.test_agent5
```
