"""ElevenLabs Conversational AI client for browser-based WebSocket voice.

Uses raw httpx (already a project dependency) — no ElevenLabs SDK needed.

Environment variables required:
  ELEVENLABS_API_KEY         — ElevenLabs API key
  ELEVENLABS_AGENT_ID        — ElevenLabs Conversational AI agent ID
  ELEVENLABS_VOICE_ID        — (optional) ElevenLabs voice ID; defaults to Sarah
"""

from __future__ import annotations

import os

import httpx

from agents.agent_voice.models import SetupCheckResponse

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
_DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah

_REQUIRED_ENV_VARS = [
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_AGENT_ID",
]

_PERSONALITY_PREFIX = """\
You are Alex, a startup founder calling on behalf of a company to introduce our product.

Personality guidelines:
- Casual, energetic, and enthusiastic — like a founder pitching their product, not a corporate rep
- Never mention you are an AI or a bot under any circumstances
- Introduce yourself as Alex
- Keep responses concise and conversational — this is a phone call, not a presentation
- When asked a question you cannot answer confidently, say:
  "Great question — let me have someone from the team follow up on that."
  Then pivot back to a key talking point.
- Listen actively and adapt to the prospect's tone

"""


def build_agent_prompt(script_text: str, research_dossier: str) -> str:
    """Combine personality instructions, sales script, and research dossier into a single agent system prompt."""
    truncated_dossier = research_dossier[:3000] if len(research_dossier) > 3000 else research_dossier

    prompt = (
        _PERSONALITY_PREFIX
        + "## Your Sales Script\n\n"
        + script_text.strip()
        + "\n\n"
        + "## Product Knowledge Base\n\n"
        + "Use the following research to answer deeper product questions:\n\n"
        + truncated_dossier.strip()
    )
    return prompt


async def get_signed_url(agent_prompt: str, first_message: str) -> str:
    """Get a signed WebSocket URL for browser-based conversation.

    POSTs to the ElevenLabs signed-url endpoint with conversation_config_override
    to inject the per-session agent prompt and first message.

    Returns:
        A signed WebSocket URL the browser can connect to directly.

    Raises:
        httpx.HTTPStatusError: If ElevenLabs returns a non-2xx status.
    """
    api_key = os.environ["ELEVENLABS_API_KEY"]
    agent_id = os.environ["ELEVENLABS_AGENT_ID"]
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)

    payload = {
        "agent_id": agent_id,
        "conversation_config_override": {
            "agent": {
                "prompt": {
                    "prompt": agent_prompt,
                },
                "first_message": first_message,
            },
            "tts": {
                "voice_id": voice_id,
            },
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{_ELEVENLABS_BASE}/convai/conversation/get-signed-url",
            json=payload,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["signed_url"]


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
