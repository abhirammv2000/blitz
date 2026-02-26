"""ElevenLabs Conversational AI client for browser-based voice.

Uses raw httpx (already a project dependency) -- no ElevenLabs SDK needed.

Environment variables required:
  ELEVENLABS_API_KEY         -- ElevenLabs API key
  ELEVENLABS_AGENT_ID        -- ElevenLabs Conversational AI agent ID
"""

from __future__ import annotations

import os

import httpx

from agents.agent_voice.models import SetupCheckResponse

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

_REQUIRED_ENV_VARS = [
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_AGENT_ID",
]

_PERSONALITY_TEMPLATE = """\
You are Alex, a sales rep who works at {company_name}. You are making an outbound sales call to a potential customer.

CRITICAL RULES:
- You ARE part of {company_name}. Always say "we", "our", "my team" — NEVER refer to {company_name} in the third person.
- Never say "{company_name} offers..." or "{company_name} provides..." — instead say "We offer..." or "We built..."
- Never mention you are an AI or a bot under any circumstances.
- Introduce yourself as "Alex from {company_name}".

Personality:
- Casual, energetic, and enthusiastic — like a real salesperson who genuinely believes in the product
- Keep responses concise and conversational — this is a phone call, not a presentation
- Ask questions to understand the prospect's needs before pitching
- When asked something you can't answer confidently, say:
  "Great question — let me have someone from our team follow up on that."
  Then pivot back to a key talking point.
- Listen actively and adapt to the prospect's tone

IMPORTANT: The sales script below may be written in third person (e.g. email format). You MUST adapt it to first person. Convert any "{company_name} offers X" to "We offer X". Replace "[Your Name]" with "Alex".

"""


def build_agent_prompt(script_text: str, research_dossier: str, company_name: str = "our company") -> str:
    """Combine personality instructions, sales script, and research dossier into a single agent system prompt."""
    truncated_dossier = research_dossier[:3000] if len(research_dossier) > 3000 else research_dossier

    personality = _PERSONALITY_TEMPLATE.format(company_name=company_name)

    prompt = (
        personality
        + "## Your Sales Script\n\n"
        + script_text.strip()
        + "\n\n"
        + "## Product Knowledge Base\n\n"
        + "Use the following research to answer deeper product questions:\n\n"
        + truncated_dossier.strip()
    )
    return prompt


def get_agent_id() -> str:
    """Return the configured ElevenLabs agent ID."""
    return os.environ["ELEVENLABS_AGENT_ID"]


async def update_agent_prompt(prompt: str, first_message: str) -> None:
    """PATCH the agent's system prompt and first message before starting a call.

    Client-side overrides are rejected by the ElevenLabs platform, so we
    update the agent config server-side instead.
    """
    api_key = os.environ["ELEVENLABS_API_KEY"]
    agent_id = os.environ["ELEVENLABS_AGENT_ID"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            f"{_ELEVENLABS_BASE}/convai/agents/{agent_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "conversation_config": {
                    "agent": {
                        "prompt": {"prompt": prompt},
                        "first_message": first_message,
                    },
                    "tts": {
                        "model_id": "eleven_multilingual_v2",
                        "stability": 0.8,
                        "similarity_boost": 0.9,
                    },
                }
            },
        )
        response.raise_for_status()


async def get_conversation_token() -> str:
    """Get a short-lived conversation token for browser WebRTC connection.

    The frontend uses this token with the @11labs/react SDK:
      conversation.startSession({ conversationToken: token, connectionType: "webrtc" })

    Returns:
        A conversation token string.

    Raises:
        httpx.HTTPStatusError: If ElevenLabs returns a non-2xx status.
    """
    api_key = os.environ["ELEVENLABS_API_KEY"]
    agent_id = os.environ["ELEVENLABS_AGENT_ID"]

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


def check_setup() -> SetupCheckResponse:
    """Validate that all required ElevenLabs environment variables are configured."""
    missing = [var for var in _REQUIRED_ENV_VARS if not os.environ.get(var)]
    return SetupCheckResponse(configured=len(missing) == 0, missing=missing)
