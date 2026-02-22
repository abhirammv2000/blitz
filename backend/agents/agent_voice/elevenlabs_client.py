"""ElevenLabs Conversational AI client for outbound voice calls.

Uses raw httpx (already a project dependency) — no ElevenLabs SDK needed.

Environment variables required:
  ELEVENLABS_API_KEY         — ElevenLabs API key
  ELEVENLABS_AGENT_ID        — ElevenLabs Conversational AI agent ID
  ELEVENLABS_PHONE_NUMBER_ID — ElevenLabs phone number ID (imported Twilio number)
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
    "ELEVENLABS_PHONE_NUMBER_ID",
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
    """Combine personality instructions, sales script, and research dossier into a single agent system prompt.

    Args:
        script_text: The segment-specific sales script / talking points.
        research_dossier: Company research output (executive summary or raw research).

    Returns:
        A complete system prompt string for the ElevenLabs Conversational AI agent.
    """
    # Truncate dossier to 3000 chars to stay within prompt limits
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


async def initiate_outbound_call(
    to_number: str,
    agent_prompt: str,
    first_message: str,
) -> dict:
    """Initiate an outbound call via ElevenLabs Conversational AI + Twilio integration.

    POSTs to https://api.elevenlabs.io/v1/convai/twilio/outbound-call with
    conversation_config_override to inject the per-call agent prompt and first message.

    Args:
        to_number: E.164-formatted phone number to call (e.g. "+14155551234").
        agent_prompt: System prompt built by build_agent_prompt().
        first_message: Opening line the agent speaks when the prospect picks up.

    Returns:
        Response JSON dict from ElevenLabs (contains conversation_id, call_sid, etc.).

    Raises:
        httpx.HTTPStatusError: If ElevenLabs returns a non-2xx status.
    """
    api_key = os.environ["ELEVENLABS_API_KEY"]
    agent_id = os.environ["ELEVENLABS_AGENT_ID"]
    phone_number_id = os.environ["ELEVENLABS_PHONE_NUMBER_ID"]
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)

    payload = {
        "agent_id": agent_id,
        "agent_phone_number_id": phone_number_id,
        "to_number": to_number,
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
            f"{_ELEVENLABS_BASE}/convai/twilio/outbound-call",
            json=payload,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()


async def get_transcript(conversation_id: str) -> dict:
    """Fetch the transcript for a completed ElevenLabs conversation.

    Args:
        conversation_id: The ElevenLabs conversation ID returned from initiate_outbound_call.

    Returns:
        Response JSON dict. On 404, returns a dict with empty messages list to allow
        graceful polling before the conversation record exists.
    """
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
    """Validate that all required ElevenLabs environment variables are configured.

    Returns:
        SetupCheckResponse with configured=True if all vars present,
        or configured=False with a list of missing variable names.
    """
    missing = [var for var in _REQUIRED_ENV_VARS if not os.environ.get(var)]
    return SetupCheckResponse(configured=len(missing) == 0, missing=missing)
