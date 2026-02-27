# Blitz — Interview Demo Script

**Duration**: ~8-10 minutes
**Setup**: Have the app running locally (live mode or demo mode)

---

## Pre-Demo Checklist

- [ ] Backend running on port 8001 (`uv run uvicorn main:app --port 8001`)
- [ ] Frontend running (`npm run dev` → localhost:5173)
- [ ] Browser open, mic permissions ready (if showing voice agent)
- [ ] OR: demo mode enabled (`.env.local` with `VITE_DEMO_MODE=cached`) — no backend needed

---

## Opening (30 seconds)

> "So this is Blitz — a multi-agent AI marketing pipeline I built. The idea is simple: you give it a company URL, and it runs 6 AI agents sequentially to generate a full marketing package. Research, brand profile, audience segments, content strategy, sales outreach, and ad creatives — all from a single URL."

> "The pipeline runs fully autonomously — each agent streams its output in real-time, then the next one kicks off automatically. You can watch the whole thing unfold step by step."

---

## Live Demo: Enter URL (30 seconds)

**Action**: Paste `https://www.joinblossomhealth.com/` into the landing page and click Launch.

> "I'll use Blossom Health as our example. The moment I hit Launch, the backend starts streaming SSE events — you can see the progress timeline updating in real-time."

**Point out**: The progress steps (Crawling, Web search, AEO check) appearing live.

---

## Agent 0 — Research Scout (1.5 minutes)

**Wait for research output to appear, then walk through it:**

> "The Research Scout is the most complex agent. It runs four things in parallel:
> - **Firecrawl** scrapes the actual website content
> - **Tavily** runs web searches — both the company's own site and third-party press coverage
> - **AEO check** — this is Answer Engine Optimization. It asks GPT-4o and Gemini 'Is Blossom Health a good choice in its space?' to see if AI models already know about the brand
> - Then a **GPT-4o synthesis** step distills everything into a strategic summary"

**Point out the AEO gauge**: "This gauge shows brand awareness across AI models — basically, if someone asks ChatGPT or Gemini about this category, will they mention this company?"

The pipeline advances automatically once each agent finishes.

---

## Agents 1-3 — Profile, Audience, Content (2 minutes)

Walk through each quickly as they complete:

### Agent 1 — Profile Creator
> "This takes the research dossier and builds a brand DNA — mission, values, tone of voice, visual identity, USPs, and marketing gaps. Everything downstream references this profile."

### Agent 2 — Audience Identifier
> "Now it generates 3-5 synthetic audience segments — each with demographics, psychographics, pain points, buying triggers, and channel preferences. These aren't guesses — they're derived from the actual research data."

### Agent 3 — Content Strategist
> "Content strategy: platform-optimized social posts, email campaigns, blog outlines, and a 30-day content calendar. All tailored to the audience segments from the previous step."

---

## Agent 4 — Sales Agent + Voice (2 minutes)

> "This is where it gets interesting. Agent 4 generates cold email sequences and LinkedIn DM templates for each audience segment. But the cool part is the voice agent."

**Walk through the Voice Agent panel:**

> "Built on ElevenLabs' Conversational AI. Here's what happens under the hood:"

> "When I select a segment and hit Start:
> 1. The backend pulls the research dossier from ChromaDB
> 2. A GPT-4o-mini call summarizes all upstream agent outputs into a knowledge brief
> 3. It dynamically creates a new ElevenLabs agent with the sales script AND the knowledge brief injected into its system prompt
> 4. Gets back a conversation token
> 5. The browser connects directly to ElevenLabs via WebSocket — the backend never touches audio"

> "So the AI voice agent — her name is Ava — doesn't just read a script. She actually knows about the company, can answer product questions, handle objections, and collect lead information: name, email, phone, callback time."

**(If live demo)**: Start a voice call, have a brief exchange, then end it.

**(If demo mode)**: "In demo mode the voice agent isn't active, but in a live run, you'd get real-time transcription right here."

---

## Agent 5 — Ad Creatives (1 minute)

> "Final agent: ad copy for Google, Meta, and LinkedIn — with A/B variants. There's also a DALL-E 3 integration for generating ad visuals, capped at 3 per run to manage costs."

---

## Architecture Talking Points (1-2 minutes)

Use these if the interviewer asks "how does it work" questions:

### On the pipeline architecture:
> "It's a LangGraph StateGraph — 6 nodes, linear, fully autonomous. State persists to SQLite via AsyncSqliteSaver, so the pipeline survives server restarts. Each agent stores its output in ChromaDB keyed by run ID, and downstream agents pull from ChromaDB — so agent 3 can read agent 1's brand profile without it being passed through the graph state."

### On streaming:
> "The SSE streaming is the part I'm most proud of. The backend concurrently reads from two async sources — the research agent's progress queue and the graph's state stream — and interleaves them into one event stream. The Zustand store on the frontend parses these SSE events and routes them to the right state slices."

### On the voice agent:
> "The backend is just a broker. It builds the prompt by combining a personality template, the sales script, and a knowledge brief synthesized from all upstream agent outputs. Then it creates a disposable ElevenLabs agent with that prompt, gets a conversation token, and hands it to the browser. From there, it's a direct WebSocket connection — bidirectional audio, real-time transcription, the whole thing."

### On LLM routing:
> "Everything goes through LiteLLM Router — GPT-4o primary, Gemini 2.5 Pro as fallback. The AEO check intentionally queries both models to test brand awareness across different AI providers."

---

## Closing (30 seconds)

> "So that's Blitz — from a single URL to a complete marketing package, fully automated, plus a voice agent that can actually make sales calls using the generated content. The whole thing is about 15 files of core logic — the rest is prompts and UI."

---

## Potential Questions & Answers

**Q: Why sequential instead of parallel agents?**
> "Each agent depends on the previous one's output. Agent 3 needs the audience segments from agent 2, which needs the brand profile from agent 1. That said, agents 3 and 4 could theoretically run in parallel since they both read from the same upstream data — that's on the roadmap."

**Q: How do you handle hallucination in the research step?**
> "The research agent grounds everything in real data — Firecrawl scrapes the actual website, Tavily pulls real press coverage. The LLM synthesis step only summarizes what was found, it doesn't generate facts. Everything is grounded in retrieved sources."

**Q: Why ChromaDB instead of just passing state through the graph?**
> "Two reasons: first, it lets any agent read any upstream agent's output without threading everything through the graph state. Second, it creates an audit trail — you can query ChromaDB after a run to see exactly what each agent produced."

**Q: What if the voice call goes off-script?**
> "Ava has a structured call flow in her system prompt — opening pitch, qualify interest, collect lead info, close. But she also has the full knowledge brief, so she can handle ad-hoc product questions. If she can't answer something confidently, she's instructed to say 'let me have someone from our team follow up on that' and pivot back to lead collection."

**Q: How does the AEO check work?**
> "We send the same question — 'Is [company] a good choice in its space?' — to both GPT-4o and Gemini. Then we check if the model mentioned the company by name, extract a confidence score, and average them into an AEO score. It's basically testing whether AI assistants already know about and recommend the brand."
