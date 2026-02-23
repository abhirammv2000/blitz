"""Pydantic models for voice agent API requests and responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SignedUrlRequest(BaseModel):
    """Request body for POST /voice/signed-url."""

    run_id: str
    segment_name: str
    script_text: str
    first_message: str


class SignedUrlResponse(BaseModel):
    """Response body for POST /voice/signed-url."""

    signed_url: str


class TranscriptMessage(BaseModel):
    """A single message turn in a conversation transcript."""

    role: Literal["agent", "user"]
    content: str


class TranscriptResponse(BaseModel):
    """Response body for GET /voice/transcript/{conversation_id}."""

    conversation_id: str
    status: Literal["in_progress", "completed", "unknown"]
    messages: list[TranscriptMessage]


class SetupCheckResponse(BaseModel):
    """Response body for GET /voice/setup-check."""

    configured: bool
    missing: list[str]
