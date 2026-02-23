# Blitz Pipeline — End-to-End Architecture

## The One-Liner

User enters a company URL → 6 AI agents run sequentially, each building on the last → out comes a full marketing package (research dossier, brand profile, audience segments, content calendar, sales sequences, ad creative) → then an AI voice agent can *call prospects live* using the generated sales script.

---

## Frontend Flow

### `main.tsx` → `App.tsx` — Entry Gate
- Mounts React app, shows either **Landing** or **Wizard** based on whether a pipeline run exists.

### `pages/Landing.tsx` — URL Input
- Simple form: user pastes a company URL, clicks "Launch."
- Calls `useBlitzStore.startPipeline(url)` which POSTs to the backend and opens an **SSE stream**.

### `store/useBlitzStore.ts` — The Brain (Zustand)
This is the most important frontend file. It:
- POSTs to `POST /pipeline/start` with the URL
- Opens a **ReadableStream** and parses SSE events in real-time
- Routes events to state:
  - `init` → stores `runId`
  - `progress` → updates the research sub-step timeline (Tavily, Firecrawl, AEO...)
  - `state` → caches agent outputs into `agentOutputs[0-5]` using a key map (`research_output→0`, `profile_output→1`, etc.)
  - `interrupted` → pipeline paused for human review
  - `error` → displays error

### `components/Wizard.tsx` — Two-Panel Layout
- **Left sidebar**: 6 steps with status badges (pending/active/done). Clicking a completed step navigates back (sets `viewStep`).
- **Right panel**: renders `AgentStep` for steps 0-5, or `SummaryPage` for step 6.
- **Key logic**: if `viewStep < currentStep`, passes `readOnly=true` to AgentStep (hides approval gates, but keeps the voice panel visible).

### `components/AgentStep.tsx` — Step Router
Routes to the correct view component per step:

| Step | Component | What it shows |
|------|-----------|---------------|
| 0 | `DossierView` | Research dossier + AEO gauge + competitors |
| 1 | `ProfileView` | Brand DNA, USPs, marketing gaps |
| 2 | `AudienceView` | Synthetic audience segments |
| 3 | `ContentView` | Social posts, emails, blog outlines, calendar |
| 4 | `SalesView` + **`VoiceAgentPanel`** | Email sequences, LinkedIn templates, + live voice calling |
| 5 | `AdsView` | Ad copy, visuals, A/B variants |

Each step shows a **ProgressTimeline** while loading, then the output + an **ApprovalGate** (approve/reject/edit).

### `components/VoiceAgent/` — The Wow Factor

| File | Role |
|------|------|
| `VoiceAgentPanel.tsx` | Orchestrates the 4-stage flow: select segment → preview script → live call → transcript |
| `SegmentCards.tsx` | Pick which audience segment to call |
| `ScriptPreview.tsx` | Edit the sales script + opening line before starting |
| `TranscriptCard.tsx` | Live transcript with speaking indicator, or completed transcript review |
| `hooks/useVoiceSession.ts` | Wraps `@11labs/react` SDK — handles mic access, WebSocket connection, real-time transcript |

**Flow**: Pick segment → edit script → confirm → browser gets mic access → connects to ElevenLabs WebSocket → "Alex" (AI voice) starts the call using your generated script → live transcript appears → end call → review transcript.

---

## Backend Flow

### `main.py` — FastAPI App + SSE Streaming

| Endpoint | What it does |
|----------|-------------|
| `POST /pipeline/start` | Creates `run_id`, starts `graph.astream()`, multiplexes progress queue + graph state into SSE stream |
| `POST /pipeline/{run_id}/resume` | Resumes after human approval/rejection, streams remaining steps |
| `POST /ads/{run_id}/generate-image` | Triggers DALL-E 3 image gen (capped at 3 per run) |
| `GET /voice/setup-check` | Validates ElevenLabs env vars are set |
| `POST /voice/signed-url` | Builds agent prompt from sales script + research dossier → gets signed WebSocket URL from ElevenLabs |
| `GET /voice/transcript/{id}` | Fetches conversation transcript from ElevenLabs API |

The **SSE streaming** is the clever part: it concurrently reads from two sources — the research node's `asyncio.Queue` (sub-step progress) and the graph's state stream (node outputs) — and interleaves them into one event stream.

### `graph.py` — LangGraph Pipeline

```
START → research → profile → audience → content → sales → ads → END
```

Linear graph, compiled with `AsyncSqliteSaver` checkpointer. Each node can call `interrupt()` to pause for human review. State persists to `blitz.db` so the pipeline survives server restarts.

### `state.py` — Shared State Schema

`BlitzState` TypedDict with: `run_id`, `company_url`, `current_step`, `research_output` through `ads_output`, `human_feedback`, `approved`. Each node reads upstream outputs and writes its own.

### `db.py` — ChromaDB Storage

Single collection `"blitz_pipeline"`, documents keyed by `"{run_id}::{agent}"`. Used for **cross-agent context sharing** — each agent stores its output, downstream agents retrieve it. This is how agent 3 (content) knows about agent 1's brand profile.

### `llm.py` — LiteLLM Router

GPT-4o as primary, Gemini 2.5 Pro as fallback. Single shared router instance. All agent LLM calls go through this (except AEO check which explicitly calls both models).

---

## The 6 Agents

### Agent 0: Research Scout (`agent_0_research/`)
- **Consumes**: Company URL
- **Does**: Tavily web search (press + competitors), Firecrawl website scrape, AEO check (queries GPT-4o + Gemini to see if they mention the company), LLM synthesis of all findings
- **Produces**: `ResearchOutput` — strategic summary, executive summary, press coverage, site content, competitor profiles, AEO score + per-model details

### Agent 1: Marketing Profile (`agent_1_profile/`)
- **Consumes**: Research output from ChromaDB
- **Does**: GPT-4o synthesis
- **Produces**: `MarketingProfile` — brand DNA (mission, values, tone, visual style), positioning statement, USPs, marketing gaps

### Agent 2: Audience Identifier (`agent_2_audience/`)
- **Consumes**: Marketing profile from ChromaDB
- **Does**: GPT-4o synthesis
- **Produces**: `AudienceOutput` — 3-5 synthetic audience segments with demographics, psychographics, pain points, buying triggers, channels, fit scores

### Agent 3: Content Strategist (`agent_3_content/`)
- **Consumes**: Profile + audience from ChromaDB
- **Does**: GPT-4o synthesis
- **Produces**: `ContentOutput` — social posts (platform-optimized), email campaigns, blog outlines, 30-day content calendar

### Agent 4: Sales Enablement (`agent_4_sales/`)
- **Consumes**: Profile + audience from ChromaDB
- **Does**: GPT-4o synthesis
- **Produces**: `SalesOutput` — 3-email consultative sequences per segment, LinkedIn DM templates, lead scoring tiers, pipeline stages

### Agent 5: Ad Creative (`agent_5_ads/`)
- **Consumes**: Profile + audience from ChromaDB
- **Does**: GPT-4o synthesis + user-triggered DALL-E 3 image gen (up to 3)
- **Produces**: `AdsOutput` — ad copy variants, visual direction briefs, A/B test variations

---

## The Voice Agent (end-to-end)

This is the full path when you click "Start Conversation":

```
Frontend                           Backend                          ElevenLabs
────────                           ───────                          ──────────
1. User picks segment
2. User edits script
3. Click "Confirm & Start"
4. POST /voice/signed-url ──────→ 5. Fetch research dossier
   {run_id, segment,                  from ChromaDB
    script_text,                   6. build_agent_prompt()
    first_message}                    (persona + script + dossier)
                                   7. POST /v1/convai/             ──→ 8. Creates session
                                      get-signed-url                     Returns signed WSS URL
                                   ←─ {signed_url}
←── {signed_url}
9. useVoiceSession.start()
10. getUserMedia({audio: true})
11. Connect to signed WSS URL ───────────────────────────────────→ 12. WebSocket live
13. Real-time audio exchange  ←──────────────────────────────────→     (bidirectional)
14. onMessage callbacks update
    transcript in real-time
15. User clicks "End"
16. conversation.endSession()
17. Show completed transcript
```

The backend never touches audio — it's a broker. It builds the prompt, gets a signed URL, and hands it off. The browser talks directly to ElevenLabs via WebSocket.

Every voice call is unique. `build_agent_prompt()` injects the specific sales script for the chosen segment plus the research dossier, so "Alex" knows about the actual company and can answer product questions.

The pipeline is a dependency chain, not a monolith. Each agent's output is stored in ChromaDB and retrieved by downstream agents. This means you could re-run agent 3 without re-running agents 0-2 — the data is already there.

---

## Changes Made (2026-02-23)

- **LLM synthesis added to Research Scout**: Agent 0 now runs a GPT-4o synthesis step after gathering data — produces a strategic summary + executive summary instead of mechanical copy-paste
- **AEO prompt rewritten**: Now asks "Is {company} a good choice in its space?" instead of hardcoded "marketing automation tools" — works for any company category
- **AEO raw response visibility**: UI shows per-model raw LLM responses via "View raw response" expandable section
- **Press relevance filter**: Title + domain matching filters out irrelevant Tavily results; shows "No relevant press coverage found" instead of garbage
- **Tavily press search fix**: Dropped `topic="news"` (returns trending news, not company press). Now runs two searches — company's own site (`include_domains`) + third-party coverage (`exclude_domains`) — ranked by relevance instead of recency
- **Company name extraction**: Expanded TLD list (added `.so`, `.me`, `.us`, `.xyz`, `.gg`, `.ly`, `.to`)
- **Voice agent panel**: Removed `readOnly` gate so voice panel stays visible when reviewing completed steps
- **AeoGauge labels**: Changed to "Brand awareness" / "Confidence" for clarity
- **`requirements.txt` created**: Added for pip-based installs as alternative to `uv sync`
