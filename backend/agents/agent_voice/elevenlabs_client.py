"""ElevenLabs Conversational AI client for browser-based voice.

Uses raw httpx (already a project dependency) -- no ElevenLabs SDK needed.

Environment variables required:
  ELEVENLABS_API_KEY         -- ElevenLabs API key
Optional:
  ELEVENLABS_VOICE_ID        -- Voice ID (defaults to Sarah)
"""

from __future__ import annotations

import json as _json
import os

import httpx

from agents.agent_voice.models import SetupCheckResponse

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

_REQUIRED_ENV_VARS = [
    "ELEVENLABS_API_KEY",
]

# ElevenLabs "Sarah" voice — warm, professional female
_DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

_PERSONALITY_TEMPLATE = """\
You are Ava, a friendly and enthusiastic sales representative who works at {company_name}. You are making an outbound sales call to a potential customer.

CRITICAL RULES:
- You ARE part of {company_name}. Always say "we", "our", "my team" — NEVER refer to {company_name} in the third person.
- Never say "{company_name} offers..." or "{company_name} provides..." — instead say "We offer..." or "We built..."
- Never mention you are an AI or a bot under any circumstances.
- Introduce yourself as "Ava from {company_name}".

Personality:
- Cheerful, warm, and genuinely enthusiastic — like a real salesperson who loves what she does
- Keep responses concise and conversational — this is a phone call, not a presentation
- Listen actively and adapt to the prospect's tone

CALL FLOW (follow this structure):

1. **Opening Pitch** (2-3 sentences): After your greeting, immediately pitch what {company_name} does and why it matters. Lead with the core value proposition from the sales script.

2. **Qualify Interest**: Ask one focused question to understand the prospect's situation. If they're not interested, thank them warmly and end the call.

3. **Collect Name**: "That's great! And who am I speaking with today?" — get their full name.

4. **Collect Email**: "Perfect! What's the best email to reach you at?" — get their email address.

5. **Spell Back Email**: THIS IS MANDATORY. After they give their email, spell it back letter by letter for confirmation. Example: "Let me make sure I have that right — that's J - dot - S - M - I - T - H - at - G - M - A - I - L - dot - C - O - M. Did I get that right?" Use dashes between each letter. Say "dot" for periods and "at" for @.

6. **Collect Phone**: "And what's the best phone number to reach you?" — get their phone number.

7. **Collect Callback Time**: "When would be a good time for our team to follow up with you?" — get their preferred callback time.

8. **Close**: Thank them warmly, confirm you'll have someone follow up, and end on a positive note.

IMPORTANT RULES FOR LEAD COLLECTION:
- If the prospect shows ANY interest, you MUST collect their name, email, phone, and callback time before ending the call.
- Do NOT end the call early if they're interested — complete all collection steps.
- If they decline to share info, respect that and move on to the next field.
- When asked something you can't answer confidently, say: "Great question — let me have someone from our team follow up on that." Then pivot back to collecting their info.

IMPORTANT: The sales script below may be written in third person (e.g. email format). You MUST adapt it to first person. Convert any "{company_name} offers X" to "We offer X". Replace "[Your Name]" with "Ava".

"""


_SUMMARIZE_PROMPT = """\
You are preparing a concise knowledge brief for a sales agent making a cold call.

Below are outputs from multiple research agents about a company. Synthesize ALL of this into a single, focused knowledge brief that a salesperson can use during a live phone call.

Structure your output exactly like this:
- **Company Pitch**: A 2-3 sentence pitch of what the company does and why it matters (this will be the agent's opening)
- **Company**: What the company does in 1-2 sentences
- **Key Value Props**: 3-5 bullet points on why customers choose them
- **Target Audience**: Who they sell to, key segments
- **Competitive Edge**: What makes them different from alternatives
- **Talking Points**: 5-7 specific facts, stats, or features the salesperson can reference
- **Objection Handlers**: 3-4 common objections and how to respond

Keep it under 800 words. Be specific — use real product names, features, and stats from the data. No filler.

--- AGENT OUTPUTS ---

{agent_outputs}
"""


_LEAD_EXTRACTION_PROMPT = """\
Extract lead information from this sales call transcript. The call was made by a sales agent from {company_name}.

Return a JSON object with these fields (use null for any field not mentioned):
- "caller_name": string or null — the prospect's full name
- "email": string or null — the prospect's email address
- "phone": string or null — the prospect's phone number
- "callback_time": string or null — when they want to be contacted back
- "interested": boolean — whether the prospect showed interest in the product/service

Transcript:
{transcript}

Return ONLY valid JSON, no markdown formatting or explanation.
"""


async def summarize_agent_outputs(agent_outputs: dict[str, str]) -> str:
    """Summarize all upstream agent outputs into a concise knowledge brief via gpt-4o-mini."""
    import litellm

    combined = ""
    for agent_name, output_text in agent_outputs.items():
        combined += f"\n### {agent_name}\n{output_text}\n"

    response = await litellm.acompletion(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a concise business analyst."},
            {"role": "user", "content": _SUMMARIZE_PROMPT.format(agent_outputs=combined)},
        ],
        max_tokens=1200,
        temperature=0.3,
    )
    return response.choices[0].message.content


def build_agent_prompt(script_text: str, knowledge_brief: str, company_name: str = "our company") -> str:
    """Combine personality instructions, sales script, and knowledge brief into a single agent system prompt."""
    personality = _PERSONALITY_TEMPLATE.format(company_name=company_name)

    prompt = (
        personality
        + "## Your Sales Script\n\n"
        + script_text.strip()
        + "\n\n"
        + "## Product Knowledge Base\n\n"
        + "Use the following knowledge brief to answer any product questions confidently:\n\n"
        + knowledge_brief.strip()
    )
    return prompt


async def create_agent(prompt: str, first_message: str, voice_id: str | None = None) -> str:
    """Create a new ElevenLabs Conversational AI agent and return its agent_id.

    POST /v1/convai/agents creates a disposable agent with the given prompt.
    """
    api_key = os.environ["ELEVENLABS_API_KEY"]
    vid = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{_ELEVENLABS_BASE}/convai/agents/create",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "conversation_config": {
                    "agent": {
                        "prompt": {"prompt": prompt},
                        "first_message": first_message,
                    },
                    "tts": {
                        "voice_id": vid,
                    },
                },
                "name": f"Blitz Sales Agent - {first_message[:40]}",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["agent_id"]


async def get_conversation_token(agent_id: str) -> str:
    """Get a short-lived conversation token for browser WebRTC connection.

    The frontend uses this token with the @11labs/react SDK:
      conversation.startSession({ conversationToken: token })
    """
    api_key = os.environ["ELEVENLABS_API_KEY"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{_ELEVENLABS_BASE}/convai/conversation/token",
            params={"agent_id": agent_id},
            headers={"xi-api-key": api_key},
        )
        response.raise_for_status()
        data = response.json()
        return data["token"]


async def get_transcript(conversation_id: str) -> dict:
    """Fetch the transcript for a completed ElevenLabs conversation."""
    api_key = os.environ["ELEVENLABS_API_KEY"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{_ELEVENLABS_BASE}/convai/conversations/{conversation_id}",
                headers={"xi-api-key": api_key},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"conversation_id": conversation_id, "messages": []}
            raise


async def extract_lead_from_transcript(messages: list[dict], company_name: str) -> dict:
    """Use gpt-4o-mini to extract structured lead data from a conversation transcript."""
    import litellm

    transcript_text = "\n".join(
        f"{m.get('role', 'unknown')}: {m.get('message') or m.get('content', '')}"
        for m in messages
    )

    response = await litellm.acompletion(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You extract structured data from sales call transcripts. Return only valid JSON."},
            {"role": "user", "content": _LEAD_EXTRACTION_PROMPT.format(
                company_name=company_name,
                transcript=transcript_text,
            )},
        ],
        max_tokens=300,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        return _json.loads(raw)
    except _json.JSONDecodeError:
        return {
            "caller_name": None,
            "email": None,
            "phone": None,
            "callback_time": None,
            "interested": False,
        }


def check_setup() -> SetupCheckResponse:
    """Validate that all required ElevenLabs environment variables are configured."""
    missing = [var for var in _REQUIRED_ENV_VARS if not os.environ.get(var)]
    return SetupCheckResponse(configured=len(missing) == 0, missing=missing)
