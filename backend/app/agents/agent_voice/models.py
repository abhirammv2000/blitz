"""Pydantic models for voice agent API requests and responses."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class VoiceSessionRequest(BaseModel):
    """Request body for POST /voice/session."""

    run_id: str
    segment_name: str
    script_text: str
    first_message: str


class VoiceSessionResponse(BaseModel):
    """Response body for POST /voice/session."""

    agent_id: str
    token: str


class LeadExtractRequest(BaseModel):
    """Request body for POST /voice/leads/extract."""

    run_id: str
    conversation_id: str


class LeadRecord(BaseModel):
    """A single lead captured from a voice conversation."""

    id: Optional[int] = None
    run_id: str
    company_name: Optional[str] = None
    caller_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    callback_time: Optional[str] = None
    conversation_id: Optional[str] = None
    interested: Optional[bool] = None
    extracted_at: Optional[str] = None


class LeadExtractResponse(BaseModel):
    """Response body for POST /voice/leads/extract."""

    success: bool
    lead: Optional[LeadRecord] = None
    message: str


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
