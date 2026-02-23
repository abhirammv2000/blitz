# Kana Campaign Engine - Ideation & System Design

## Executive Summary

**One-liner:** "Pomelli goes end-to-end." Enter a company URL and an AI-powered multi-agent system deeply researches the business, builds a marketing profile, identifies target audiences, creates targeted content, generates a sales pipeline (with optional AI voice calling), and produces ad creatives. Human approves at every step.

**What this is:** A full-funnel agentic marketing platform that takes a single URL input and delivers a complete marketing package through 6 specialized AI agents sharing context via a persistent vector database.

**Why it exists:** Google's Pomelli (launched Oct 2025) proved the "URL → marketing assets" concept works. But it has critical limitations:
1. Uses Google search — we use Tavily for deeper, structured research
2. Stops at generating social media posts — we go from research through sales
3. No audience intelligence — we identify and profile target segments
4. No competitive analysis — we map the competitive landscape
5. No sales pipeline — we generate outreach and optionally deploy AI voice callers
6. No human approval gates — we have governance-first design with approve/edit/override at every step
7. Monolithic — we use specialized agents that share context via VDB

**Built for the Kana AI Solutions Builder interview.** This single project covers all four Kana product pillars:
| Kana Pillar | Coverage |
|-------------|----------|
| #1 Synthetic Data Enrichment | Audience Identifier generates expanded synthetic profiles from small seed signals |
| #2 AI-Powered Analytics | Research Scout + AEO visibility scoring = analytics agent in action |
| #3 Answer Engine Optimization | AEO check during research shows brand visibility across AI chatbots |
| #4 Agentic Execution | The entire system IS agentic execution with human-in-the-loop governance |

---

## The Problem (Vivek Framing)

**"What problem are you trying to solve?"**

Small-to-medium businesses need marketing. The current options are:
1. **Hire an agency** — $5-50K/month, weeks to onboard, slow iteration
2. **DIY with tools** — Canva, Mailchimp, HubSpot — steep learning curve, fragmented, no strategy
3. **Pomelli** — Enter URL, get social posts. Fast, but stops at asset generation. No audience thinking, no sales funnel, no competitive intelligence.

The real problem isn't "generate a social media post." The real problem is: **"I have a product and a website. Turn that into customers."** That's the end-to-end gap.

This project solves the complete journey: URL → understanding → strategy → content → outreach → ads → customers.

---

## System Architecture

### Pipeline Overview

```
[URL Input]
    │
    ▼
Agent 0: Research Scout ──────────────────────────┐
    │ (Tavily + web crawl + AEO check)            │
    │ [HUMAN APPROVAL GATE]                        │
    ▼                                              │
Agent 1: Marketing Profile Creator                 │
    │ (Brand DNA, positioning, gaps)               │
    │ [HUMAN APPROVAL GATE]                        │
    ▼                                              ├──► Vector Database
Agent 2: Audience Identifier                       │    (ChromaDB)
    │ (Segments, demographics, channels)           │    Shared context
    │ [HUMAN APPROVAL GATE]                        │    Persistent memory
    ▼                                              │    Agent communication
Agent 3: Content Strategist                        │
    │ (Posts, emails, calendar)                    │
    │ [HUMAN APPROVAL GATE]                        │
    ▼                                              │
Agent 4: Sales Agent                               │
    │ (Outreach + optional ElevenLabs voice agent) │
    │ [HUMAN APPROVAL GATE]                        │
    ▼                                              │
Agent 5: Ad Creative Generator ────────────────────┘
    │ (Ad copy + AI-generated images/video)
    │ [HUMAN APPROVAL GATE]
    ▼
[Export: Complete Marketing Package]
```

### Human Approval Gates

At each agent handoff, the user can:
- **Approve** — accept output, proceed to next agent
- **Edit** — modify the agent's output manually, then proceed
- **Reject + Retry** — send back with feedback, agent regenerates
- **Override** — replace agent output entirely with custom input

All decisions logged in VDB for audit trail and future learning.

---

## Agent Deep Dives

### Agent 0: Research Scout

**Purpose:** Deep research on the company — far beyond Pomelli's "extract brand colors and fonts."

**Input:** Company URL

**Process:**
1. **Web crawl** the target URL: extract all product pages, about page, blog posts, team page, press/news, testimonials
2. **Tavily search** for external intelligence: press coverage, reviews, social mentions, industry reports, competitor mentions
3. **AEO visibility check**: query Claude + GPT-4 with customer-style questions ("What's the best [product category]?", "What is [company name]?") to assess current brand visibility in AI chatbot answers
4. **Competitive landscape**: identify 3-5 competitors from search results, extract their positioning

**Output — Company Intelligence Dossier:**
```json
{
  "company_name": "...",
  "url": "...",
  "description": "...",
  "products_services": [...],
  "value_propositions": [...],
  "brand_voice_samples": [...],
  "target_market_signals": [...],
  "competitive_landscape": [
    {"competitor": "...", "positioning": "...", "strength": "...", "weakness": "..."}
  ],
  "aeo_visibility": {
    "score": 2/10,
    "queries_tested": [...],
    "mentioned_in": ["Claude: yes", "GPT-4: no"],
    "brand_perception": "...",
    "gaps": [...]
  },
  "current_marketing_presence": {
    "social_media": [...],
    "content_marketing": "...",
    "paid_ads": "..."
  }
}
```

**Why separate from Agent 1:** Research is expensive (web crawling, multiple API calls, AEO queries). Caching it in VDB means other agents can query context without re-crawling. Also allows the human to verify research accuracy before it propagates through the pipeline.

---

### Agent 1: Marketing Profile Creator

**Purpose:** Synthesize raw research into a structured marketing strategy foundation.

**Input:** Company Intelligence Dossier (from VDB)

**Process:**
1. Analyze the dossier to extract brand positioning
2. Define unique selling propositions (USPs) based on product analysis + competitive gaps
3. Establish brand voice/tone guidelines from website copy samples
4. Identify marketing gaps and opportunities (e.g., "strong product, zero AEO presence, no email marketing")
5. Create a positioning statement

**Output — Marketing Profile:**
```json
{
  "brand_dna": {
    "mission": "...",
    "values": [...],
    "tone": "playful, trustworthy, eco-conscious",
    "visual_style": "bright, clean, natural materials"
  },
  "positioning_statement": "For [target] who [need], [company] is the [category] that [differentiation] because [reason].",
  "usps": [...],
  "competitive_advantages": [...],
  "identified_gaps": [
    "No AEO presence — brand invisible to AI chatbots",
    "No email marketing infrastructure",
    "Social media active but no paid strategy"
  ],
  "recommended_focus_areas": [...]
}
```

---

### Agent 2: Audience Identifier

**Purpose:** Identify who to market to, with reasoning.

**Input:** Marketing Profile + Company Dossier (from VDB)

**Process:**
1. Analyze product/service to identify 3-5 target customer segments
2. For each segment: define demographics, psychographics, pain points, buying triggers
3. Identify which channels each segment is active on
4. Explain reasoning for each segment ("why this segment fits this product")
5. Generate synthetic expanded attributes for each segment (lookalike profiles)

**Output — Audience Segments:**
```json
{
  "segments": [
    {
      "name": "Eco-Conscious New Parents",
      "demographics": {"age": "25-35", "income": "...", "location": "..."},
      "psychographics": ["values sustainability", "researches products heavily", "..."],
      "pain_points": ["worried about chemicals in toys", "..."],
      "buying_triggers": ["safety certifications", "organic materials", "..."],
      "channels": ["Instagram", "Pinterest", "parenting forums", "..."],
      "reasoning": "This segment aligns because...",
      "estimated_reach": "..."
    }
  ]
}
```

---

### Agent 3: Content Strategist

**Purpose:** Create actual marketing content targeted to identified audiences.

**Input:** Marketing Profile + Audience Segments (from VDB)

**Process:**
1. For each audience segment, recommend content types and channels
2. Generate draft content: 3-5 social media posts per segment, email subject lines + body copy, blog post outlines
3. Create a content calendar mapping: which content → which segment → which channel → when
4. Include hashtag suggestions, posting time recommendations

**Output — Content Strategy + Drafts:**
```json
{
  "content_calendar": [...],
  "social_posts": [
    {
      "segment": "Eco-Conscious New Parents",
      "platform": "Instagram",
      "type": "carousel",
      "copy": "...",
      "hashtags": [...],
      "posting_time": "Tuesday 9am EST"
    }
  ],
  "email_campaigns": [
    {
      "segment": "...",
      "subject_line": "...",
      "body": "...",
      "cta": "..."
    }
  ],
  "blog_outlines": [...]
}
```

---

### Agent 4: Sales Agent

**Purpose:** Generate outreach pipeline and optionally deploy an AI voice sales agent.

**Input:** Audience Segments + Content Strategy + Marketing Profile (from VDB)

**Process:**

**Written Outreach (standard):**
1. Generate cold email sequences (3-email cadence) per audience segment
2. Create LinkedIn DM templates personalized per segment
3. Define lead scoring criteria based on segment fit signals
4. Build pipeline stage definitions (prospect → contacted → engaged → converted)
5. Draft follow-up sequences for each stage

**AI Voice Agent (optional, premium):**
1. Compile product knowledge from VDB (research dossier, USPs, competitive advantages)
2. Generate a sales script per audience segment (intro, pitch, objection handling, close)
3. Create an ElevenLabs Conversational AI agent pre-loaded with:
   - Product knowledge base
   - Segment-specific sales script
   - Brand voice/tone matching
   - Objection handling responses based on competitive landscape
4. Accept a list of phone numbers
5. Deploy the ElevenLabs agent to make outbound sales calls

**Output:**
```json
{
  "email_sequences": [...],
  "linkedin_templates": [...],
  "lead_scoring": {...},
  "pipeline_stages": [...],
  "voice_agent": {
    "status": "deployed" | "not_configured",
    "agent_id": "...",
    "script": "...",
    "knowledge_base": "..."
  }
}
```

**Note:** The voice agent is an optional feature gated behind a UI toggle. For the demo, we can show the agent creation flow and optionally make a test call.

---

### Agent 5: Ad Creative Generator

**Purpose:** Generate platform-ready ad copy and visuals.

**Input:** Marketing Profile + Audience Segments + Content Strategy (from VDB)

**Process:**
1. Generate ad copy for each platform: Google Ads (headlines + descriptions), Meta Ads (primary text + headline + description), LinkedIn Ads
2. Create visual ad concepts using AI image generation (Flux/DALL-E) — product in context, lifestyle shots, brand-styled graphics
3. Generate A/B test variations (2-3 per ad)
4. Optionally: video storyboard concepts or short animated clips

**Output:**
```json
{
  "google_ads": [...],
  "meta_ads": [
    {
      "segment": "...",
      "primary_text": "...",
      "headline": "...",
      "image_url": "...",
      "ab_variant": "A"
    }
  ],
  "linkedin_ads": [...],
  "generated_images": [...],
  "video_concepts": [...]
}
```

---

### Vector Database (Shared Context Layer)

**Technology:** ChromaDB (embedded, persistent)

**Purpose:**
1. **Cross-agent context sharing:** Each agent reads relevant context from VDB before executing
2. **Agent communication log:** All agent outputs, reasoning, and human edits stored as embeddings
3. **Persistent memory:** Across sessions, the system retains industry knowledge, what worked for similar companies, audience patterns
4. **Audit trail:** Every agent decision + human override is logged with timestamps

**Collections:**
- `company_research` — raw research data, crawled pages, external intel
- `marketing_profiles` — brand DNA, positioning, competitive analysis
- `audience_segments` — segment profiles, synthetic expansions
- `content_assets` — generated content, performance data
- `sales_pipeline` — outreach templates, lead data
- `agent_reasoning` — why each agent made each decision (for transparency)

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Backend** | Python 3.11+, FastAPI | Kana's stack, async for multi-API calls |
| **Frontend** | React 18, Tailwind CSS | Kana's stack, step-by-step wizard UI |
| **Agent Orchestration** | LangGraph | State machines, human-in-the-loop gates, agent handoffs |
| **LLM (primary)** | Claude API (Sonnet) | Kana's preferred tool (Claude Code in JD), structured outputs |
| **Web Research** | Tavily API | Purpose-built for agent research, superior to raw Google search |
| **Web Crawling** | Firecrawl or BeautifulSoup | Extract structured content from company websites |
| **Vector Database** | ChromaDB (embedded) | Zero-config, Python-native, persistent, free |
| **AEO Queries** | Claude API + OpenAI API | Multi-LLM querying for AEO visibility scoring |
| **Image Generation** | Flux (via Replicate) or DALL-E 3 | AI-generated ad visuals |
| **Voice Agent** | ElevenLabs Conversational AI API | Outbound AI voice sales caller (optional feature) |
| **Structured Data** | SQLite | Lightweight storage for leads, campaigns, pipeline |
| **Data Validation** | Pydantic | Structured outputs from every agent |
| **Deployment** | Docker, Render | Quick deploy, shareable demo URL, free tier |

---

## User Flow (Demo Walkthrough)

### Step 1: Landing Page
User enters company URL. Clean, minimal interface — one input field, one button.

### Step 2: Research Scout (~30-60 seconds)
- Live progress indicators: "Crawling website... Found 12 pages", "Searching external sources...", "Checking AEO visibility..."
- Displays: Company Intelligence Dossier in structured, editable cards
- Highlight: AEO score prominently — "Your brand appears in 1/5 AI chatbot responses for 'best baby toys'"
- **[APPROVE] / [EDIT] / [RE-RESEARCH]**

### Step 3: Marketing Profile (~15 seconds)
- Displays: Brand DNA card, positioning statement, USPs, competitive gaps
- Gaps highlighted in orange (actionable opportunities)
- **[APPROVE] / [EDIT]**

### Step 4: Audience Segments (~20 seconds)
- Displays: 3-5 segment cards with demographics, psychographics, reasoning
- Each card expandable for detail
- **[APPROVE] / [EDIT] / [ADD SEGMENT] / [REMOVE SEGMENT]**

### Step 5: Content Strategy (~30 seconds)
- Displays: Content calendar grid view (segment x channel x week)
- Draft posts rendered as platform previews (Instagram-style card, email preview, etc.)
- **[APPROVE] / [EDIT] / [REGENERATE SPECIFIC PIECE]**

### Step 6: Sales Pipeline (~20 seconds)
- Displays: Email sequences as timeline, DM templates as cards, lead scoring criteria
- Optional: "Create AI Sales Caller" toggle
  - If enabled: deploys ElevenLabs agent, shows "Test Call" button
- **[APPROVE] / [EDIT]**

### Step 7: Ad Creatives (~45 seconds with image generation)
- Displays: Ad copy + AI-generated visuals per platform
- Side-by-side A/B variations
- **[APPROVE] / [DOWNLOAD ALL] / [REGENERATE]**

### Step 8: Export
- Download complete Marketing Package: PDF report + all assets + content calendar + outreach templates + ad creatives
- All data persisted in VDB for future reference

---

## Wow Factors (What Makes This Stand Out)

1. **End-to-end:** URL → customers. Not URL → social media posts. The complete journey.
2. **AEO visibility scoring:** No other tool does this. You see how your brand appears in AI chatbots as part of your marketing strategy. Directly maps to Kana's AEO pillar.
3. **AI voice sales caller:** An agent that creates another agent. Meta-agentic. ElevenLabs integration means the demo can actually make a phone call.
4. **Deep research via Tavily:** Not just brand colors from your CSS. Actual business understanding from crawling your site, reading press, analyzing competitors.
5. **Human-in-the-loop governance:** Approve, edit, or override every agent decision. Audit trail captures everything. This IS Kana's "trusted stewardship" value.
6. **Persistent intelligence:** VDB remembers past analyses. Over time, the system knows industry benchmarks, what audience segments worked for similar companies.
7. **Multi-agent transparency:** See each agent's reasoning. Why did it choose those audience segments? Why that channel mix? Visible, auditable, overridable.
8. **All four Kana pillars in one project:** No other candidate walks in with a project that covers synthetic data, analytics, AEO, and agentic execution simultaneously.

---

## MVP Scope (Build Priority for ~2 Week Demo)

### Phase 1: Core Pipeline (Days 1-10) — MUST HAVE
- [ ] Agent 0: Research Scout (Tavily + web crawl + AEO check)
- [ ] Agent 1: Marketing Profile Creator
- [ ] Agent 2: Audience Identifier (with segment reasoning)
- [ ] Agent 3: Content Strategist (draft posts + channel mapping)
- [ ] VDB: ChromaDB with shared context
- [ ] LangGraph orchestration with human-in-the-loop gates
- [ ] React wizard UI with approve/edit/reject at each step
- [ ] Basic export (JSON + formatted text)

### Phase 2: Visual Impact (Days 10-13) — SHOULD HAVE
- [ ] Agent 5: Ad Creative Generator (AI-generated images)
- [ ] Platform-preview UI for generated content (Instagram-style cards, etc.)
- [ ] PDF export of full marketing package

### Phase 3: Sales Wow (Days 13-15) — NICE TO HAVE
- [ ] Agent 4: Sales Agent (written outreach templates)
- [ ] ElevenLabs voice agent creation (optional toggle)
- [ ] Test call functionality

### Phase 4: Polish — IF TIME
- [ ] Persistent memory across companies
- [ ] Loading animations and progress indicators
- [ ] Responsive design
- [ ] Error handling and retry logic

---

## Kana Interview Narrative

1. **Open with the problem:** "Pomelli proved URL-to-marketing-assets works. But it stops at social posts. The real problem is: I have a product and a website — turn that into customers."
2. **Demo the pipeline:** Live walkthrough with a real company URL. Show each agent's reasoning. Approve, edit one output, show how it propagates.
3. **Highlight AEO:** "As part of research, the system checks how your brand shows up in AI chatbots. This IS Kana's AEO pillar."
4. **Show the judgment skill:** Pause at an agent output, explain what you'd approve vs. correct and why. "This audience segment doesn't make sense because X — watch me override it."
5. **Drop the ElevenLabs wow:** "And for enterprise clients who want to go further — the sales agent can create an AI voice caller." Demo a test call if possible.
6. **Connect to Kana's architecture:** "I used loosely coupled agents with human-in-the-loop approval, shared context via vector database, and governance-first design — the same architecture philosophy Kana uses."
7. **Close with Vivek's philosophy:** "I started by asking 'what problem am I solving?' Not 'how do I generate a social media post' — but 'how do I turn a URL into customers.' That's the end-to-end thinking this role requires."

---

## Sources

- [Pomelli by Google Labs](https://labs.google.com/pomelli/about/)
- [Google Labs and DeepMind launch Pomelli](https://blog.google/technology/google-labs/pomelli/)
- [Pomelli in Practice: Evaluating Google's New AI Tool](https://www.logicalposition.com/blog/pomelli-in-practice-evaluating-googles-new-ai-tool-for-small-businesses)
- [Google Labs Launches Pomelli AI Marketing Tool for SMBs](https://www.techbuzz.ai/articles/google-labs-launches-pomelli-ai-marketing-tool-for-smbs)
- [Kana AI Official Website](https://www.kana.ai)
- [SiliconANGLE: Kana Intelligence scores $15M](https://siliconangle.com/2026/02/18/flexible-agentic-marketing-startup-kana-intelligence-scores-15m-seed-funding/)
