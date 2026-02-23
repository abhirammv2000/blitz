# Blitz

**Enter a company URL. Get a complete marketing pipeline.**

Blitz is a multi-agent AI marketing platform that transforms a single company URL into a full marketing package — research dossier, brand profile, audience segments, content strategy, sales outreach, and ad creatives — with human approval at every step.

Built as a working demo for the **Kana AI Solutions Builder** role (super{set} portfolio company).

## What It Does

```
Company URL
    ↓
┌─────────────────────────────────────────────┐
│  Agent 0: Research Scout                    │
│  Tavily search + Firecrawl crawl + AEO     │
│  + GPT-4o LLM synthesis                    │
│  → Company Intelligence Dossier            │
├─────────── ✓ Human Approval ───────────────┤
│  Agent 1: Marketing Profile Creator         │
│  → Brand DNA, positioning, USPs, gaps      │
├─────────── ✓ Human Approval ───────────────┤
│  Agent 2: Audience Identifier               │
│  → 3-5 segments with synthetic profiles    │
├─────────── ✓ Human Approval ───────────────┤
│  Agent 3: Content Strategist                │
│  → Social posts, emails, blog, calendar    │
├─────────── ✓ Human Approval ───────────────┤
│  Agent 4: Sales Agent                       │
│  → Cold sequences, LinkedIn DMs, scoring   │
│  + Optional: Browser voice agent (ElevenLabs) │
├─────────── ✓ Human Approval ───────────────┤
│  Agent 5: Ad Creative Generator             │
│  → Google/Meta/LinkedIn ads + A/B tests    │
│  + Optional: DALL-E 3 ad visuals           │
└─────────────────────────────────────────────┘
    ↓
Complete Marketing Package (export JSON)
```

## Kana Pillar Coverage

| Kana Pillar | Blitz Implementation |
|-------------|---------------------|
| Synthetic Data Enrichment | Audience segments with expanded synthetic lookalike profiles |
| AI-Powered Analytics | Research Scout + competitor analysis + AEO scoring |
| Answer Engine Optimization | Multi-LLM AEO check — "Is X a good choice in its space?" across GPT-4o and Gemini (0-10 score, per-model raw response visibility) |
| Agentic Execution | 6-agent LangGraph pipeline with human-in-the-loop governance |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | LangGraph (StateGraph + interrupt gates) |
| LLM Routing | LiteLLM Router (GPT-4o primary, Gemini 2.5 Pro fallback) |
| Vector DB | ChromaDB (cross-agent context sharing + audit trail) |
| Backend | Python, FastAPI, SSE streaming, Pydantic |
| Frontend | React, TypeScript, Vite, Tailwind CSS v4, Zustand, Headless UI |
| Research | Tavily API, Firecrawl |
| Voice | ElevenLabs Conversational AI via WebSocket (optional, browser-based) |
| Image Gen | DALL-E 3 via LiteLLM (user-triggered, 3/run cap) |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- API keys: OpenAI, Gemini, Tavily, Firecrawl

### 1. Clone and set up backend

```bash
cd backend
cp .env.example .env
# Add your API keys to .env

uv sync                # or: pip install -r requirements.txt
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Set up frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Open the app

Navigate to `http://localhost:5173`, enter a company URL, and watch the pipeline run.

### Demo Mode (no API keys needed)

To run with pre-cached outputs (no live API calls):

```bash
# In frontend/
cp .env.demo .env.local
npm run dev
```

This replays the full 6-agent pipeline from cached fixture data. Perfect for demos and interviews.

## Project Structure

```
superset/
├── backend/
│   ├── agents/
│   │   ├── agent_0_research/      # Tavily + Firecrawl + AEO
│   │   ├── agent_1_profile/       # Brand DNA + positioning
│   │   ├── agent_2_audience/      # Segments + synthetic expansion
│   │   ├── agent_3_content/       # Social, email, blog, calendar
│   │   ├── agent_4_sales/         # Sequences, DMs, lead scoring
│   │   ├── agent_5_ads/           # Ad copy + DALL-E 3 visuals
│   │   └── agent_voice/           # ElevenLabs browser voice agent
│   ├── main.py                    # FastAPI app + SSE endpoints
│   ├── graph.py                   # LangGraph pipeline definition
│   ├── llm.py                     # LiteLLM Router config
│   ├── state.py                   # BlitzState TypedDict
│   └── db.py                      # ChromaDB client
├── frontend/
│   └── src/
│       ├── components/            # React UI components
│       ├── pages/Landing.tsx      # URL input landing page
│       ├── store/                 # Zustand state management
│       └── demo/                  # Cached fixture data
└── .planning/                     # Architecture docs & phase plans
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/pipeline/start` | Start pipeline (returns SSE stream) |
| `POST` | `/pipeline/{run_id}/resume` | Resume with human decision (approve/edit/reject/override) |
| `POST` | `/ads/{run_id}/generate-image` | Generate DALL-E 3 ad visual |
| `GET` | `/voice/setup-check` | Check ElevenLabs configuration |
| `POST` | `/voice/signed-url` | Get signed WebSocket URL for browser voice session |
| `GET` | `/voice/transcript/{id}` | Get conversation transcript |
| `GET` | `/health` | Health check |

## Key Architecture Decisions

- **AI-agnostic**: LiteLLM Router abstracts LLM providers. Swap models without code changes.
- **Sequential pipeline**: Each agent depends on the previous agent's output. ChromaDB provides cross-agent context.
- **HITL governance**: LangGraph `interrupt()` pauses the pipeline at each agent. Users approve, edit, reject (with feedback for re-generation), or override before advancing.
- **SSE streaming**: Real-time progress updates as each agent runs. No polling.
- **Demo mode**: `VITE_DEMO_MODE=cached` replays fixture JSON — eliminates API rate limit risk during live demos.

## Environment Variables

```env
# Required
OPENAI_API_KEY=        # GPT-4o for content, sales, ads
GEMINI_API_KEY=        # Gemini 2.5 Pro fallback
TAVILY_API_KEY=        # Web search for Research Scout
FIRECRAWL_API_KEY=     # Website crawling

# Optional
ELEVENLABS_API_KEY=    # Voice agent
ELEVENLABS_AGENT_ID=   # Conversational AI agent ID
```

## License

Private project — built for interview demonstration.
