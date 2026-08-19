"""
FastAPI Backend — The engine driving the Blitz pipeline.

This is the main entry point for the backend. It provides endpoints to:
  - Start a new pipeline run (and stream real-time updates back to the browser)
  - Perform health checks
  - Handle voice agent interactions (setting up, getting transcripts, extracting leads)

We use Server-Sent Events (SSE) to stream data back to the frontend. Think of it like a 
one-way walkie-talkie where the server can continuously push updates (like "agent finished", 
"new step started") to the browser without the browser having to constantly ask "are you done yet?".
"""

import asyncio
import json
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.agent_0_research.progress import cleanup_queue, get_queue
from agents.agent_voice.models import (
    LeadExtractRequest,
    LeadExtractResponse,
    LeadRecord,
    SetupCheckResponse,
    VoiceSessionRequest,
    VoiceSessionResponse,
    TranscriptMessage,
    TranscriptResponse,
)
from agents.agent_voice.elevenlabs_client import (
    build_agent_prompt,
    check_setup,
    create_agent,
    extract_lead_from_transcript,
    get_conversation_token,
    get_transcript,
    summarize_agent_outputs,
)
from db import get_agent_context, get_agent_output
from graph import build_graph
from llm import describe_exception
from leads_db import get_leads_for_run, init_leads_table, insert_lead

from pathlib import Path
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env", override=True)
load_dotenv(_backend_dir.parent / ".env", override=True)

# ---------------------------------------------------------------------------
# App-level graph instance (set during startup)
# ---------------------------------------------------------------------------

graph = None  # type: ignore[assignment]


app = FastAPI(title="Blitz Pipeline API")


@app.on_event("startup")
async def startup():
    global graph  # noqa: PLW0603
    graph = build_graph()
    init_leads_table()


# Dev defaults cover the Vite dev-server port range. Any real deployment must set
# CORS_ORIGINS (comma-separated) — the hardcoded localhost list silently blocked
# every non-localhost origin, including the built frontend on its preview port.
_DEV_ORIGINS = [f"http://localhost:{port}" for port in range(5173, 5200)]
_configured_origins = os.environ.get("CORS_ORIGINS", "").strip()
ALLOWED_ORIGINS = (
    [o.strip() for o in _configured_origins.split(",") if o.strip()]
    if _configured_origins
    else _DEV_ORIGINS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PipelineStartRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def sse_event(data: dict) -> str:
    """Format a dict as an SSE data event string."""
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Shared streaming helper
# ---------------------------------------------------------------------------


async def stream_graph_with_progress(run_id: str, graph_input: dict, config: dict):
    """
    The magic behind our real-time updates! 
    
    This function listens to two things at once:
      1. The LangGraph pipeline (which outputs the final result of each agent)
      2. A progress queue (which outputs granular, sub-step updates while agents are "thinking")

    It takes both of these streams, mixes them together, and sends them back to the frontend
    as a single, continuous stream of Server-Sent Events (SSE).
    """
    queue = get_queue(run_id)
    results: list[dict] = []
    graph_error: Exception | None = None

    async def graph_runner() -> None:
        nonlocal graph_error
        try:
            async for chunk in graph.astream(
                graph_input,
                config=config,
                stream_mode="values",
            ):
                if isinstance(chunk, dict):
                    results.append(chunk)
        except Exception as exc:  # noqa: BLE001
            graph_error = exc

    task = asyncio.create_task(graph_runner())

    def drain_progress() -> list[str]:
        events = []
        while True:
            try:
                events.append(sse_event({"type": "progress", **queue.get_nowait()}))
            except asyncio.QueueEmpty:
                return events

    def drain_results() -> list[str]:
        events = []
        while results:
            chunk = results.pop(0)
            safe = {k: v for k, v in chunk.items() if not k.startswith("__")}
            events.append(sse_event({"type": "state", "data": safe}))
        return events

    try:
        while not task.done():
            for evt in drain_progress():
                yield evt
            for evt in drain_results():
                yield evt
            await asyncio.sleep(0.05)

        # Always flush what did complete before reporting anything. A failure in
        # agent 5 must not throw away the five agents that already succeeded —
        # the client has paid for that work and should receive it.
        for evt in drain_progress():
            yield evt
        for evt in drain_results():
            yield evt

        if graph_error is not None:
            # str(asyncio.TimeoutError()) is "", which reached users as a blank
            # error message. describe_exception() always yields something useful.
            yield sse_event({"type": "error", "message": describe_exception(graph_error)})
            return

        yield sse_event({"type": "done"})

    finally:
        # If the client disconnected, this generator is closed mid-stream and the
        # graph task would otherwise keep running to completion — burning API
        # spend on a result nobody will receive. Cancel it.
        if not task.done():
            task.cancel()
        cleanup_queue(run_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/pipeline/start")
async def pipeline_start(payload: PipelineStartRequest):
    """
    Kick off a new pipeline run! 
    When the frontend says "go", this endpoint spins up a new LangGraph process
    and immediately opens up an SSE stream to send live updates back to the browser.
    """
    run_id = str(uuid.uuid4())

    async def event_stream():
        yield sse_event({"type": "init", "run_id": run_id})

        initial_state = {
            "run_id": run_id,
            "company_url": payload.url,
            "current_step": 0,
        }
        config = {"configurable": {"thread_id": run_id}}

        async for event in stream_graph_with_progress(run_id, initial_state, config):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Ad image generation (user-triggered, capped at 3 per run)
# ---------------------------------------------------------------------------

_image_counts: dict[str, int] = {}
IMAGE_CAP = 3


class ImageGenRequest(BaseModel):
    prompt: str


@app.post("/ads/{run_id}/generate-image")
async def generate_ad_image_endpoint(run_id: str, body: ImageGenRequest):
    """Generate a single DALL-E 3 image from a user-edited prompt.

    Capped at IMAGE_CAP (3) generations per run_id to control costs.
    """
    count = _image_counts.get(run_id, 0)
    if count >= IMAGE_CAP:
        return {"error": f"Image generation limit ({IMAGE_CAP}) reached for this run.", "image_url": None}

    from agents.agent_5_ads.node import generate_ad_image

    image_url = await generate_ad_image(body.prompt)
    if image_url:
        _image_counts[run_id] = count + 1

    remaining = IMAGE_CAP - _image_counts.get(run_id, 0)
    return {"image_url": image_url, "remaining": remaining}


# ---------------------------------------------------------------------------
# Voice agent endpoints (ElevenLabs Conversational AI — browser WebSocket)
# ---------------------------------------------------------------------------


@app.get("/voice/setup-check", response_model=SetupCheckResponse)
async def voice_setup_check():
    return check_setup()


@app.post("/voice/session", response_model=VoiceSessionResponse)
async def voice_session(req: VoiceSessionRequest):
    setup = check_setup()
    if not setup.configured:
        raise HTTPException(
            status_code=503,
            detail={"detail": "ElevenLabs not configured", "missing": setup.missing},
        )

    # Pull all upstream agent outputs from ChromaDB
    import json as _json

    agent_keys = [
        ("research_decision", "Research Dossier"),
        ("profile", "Brand Profile"),
        ("audience", "Audience Segments"),
        ("content", "Content Strategy"),
        ("sales", "Sales Playbook"),
    ]
    agent_outputs: dict[str, str] = {}
    company_name = "our company"

    for db_key, label in agent_keys:
        # Trimmed: this feeds a summarization prompt, not a stored artifact.
        raw = get_agent_context(req.run_id, db_key)
        if raw:
            agent_outputs[label] = raw
            # Extract company name from research output
            if db_key == "research_decision":
                try:
                    research_data = _json.loads(raw)
                    company_name = research_data.get("company_name") or research_data.get("name") or "our company"
                except (ValueError, TypeError):
                    pass

    # Summarize all agent knowledge into a concise brief via gpt-4o-mini
    if agent_outputs:
        knowledge_brief = await summarize_agent_outputs(agent_outputs)
    else:
        knowledge_brief = ""

    agent_prompt = build_agent_prompt(req.script_text, knowledge_brief, company_name)

    try:
        agent_id = await create_agent(agent_prompt, req.first_message)
        token = await get_conversation_token(agent_id)
    except Exception as exc:  # noqa: BLE001
        import httpx as _httpx
        if isinstance(exc, _httpx.HTTPStatusError):
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs API error: {exc.response.status_code} {exc.response.text}",
            ) from exc
        raise

    return VoiceSessionResponse(
        agent_id=agent_id,
        token=token,
    )


@app.get("/voice/transcript/{conversation_id}", response_model=TranscriptResponse)
async def voice_transcript(conversation_id: str):
    raw = await get_transcript(conversation_id)

    raw_messages = raw.get("messages") or []
    messages = []
    for msg in raw_messages:
        role = msg.get("role", "")
        content = msg.get("message") or msg.get("content") or ""
        if role in ("agent", "user") and content:
            messages.append(TranscriptMessage(role=role, content=content))

    status: str
    if messages:
        status = "completed"
    elif raw.get("status") == "unknown":
        status = "unknown"
    else:
        status = "in_progress"

    return TranscriptResponse(
        conversation_id=conversation_id,
        status=status,  # type: ignore[arg-type]
        messages=messages,
    )


@app.post("/voice/leads/extract", response_model=LeadExtractResponse)
async def voice_leads_extract(req: LeadExtractRequest):
    """Extract lead data from a completed conversation and store it."""
    raw = await get_transcript(req.conversation_id)
    raw_messages = raw.get("messages") or []

    if not raw_messages:
        return LeadExtractResponse(success=False, lead=None, message="No transcript available yet")

    # Get company name from research output
    import json as _json
    company_name = "our company"
    research_raw = get_agent_output(req.run_id, "research_decision")
    if research_raw:
        try:
            research_data = _json.loads(research_raw)
            company_name = research_data.get("company_name") or research_data.get("name") or "our company"
        except (ValueError, TypeError):
            pass

    lead_data = await extract_lead_from_transcript(raw_messages, company_name)

    transcript_text = "\n".join(
        f"{m.get('role', 'unknown')}: {m.get('message') or m.get('content', '')}"
        for m in raw_messages
    )

    row_id = insert_lead(
        run_id=req.run_id,
        company_name=company_name,
        conversation_id=req.conversation_id,
        caller_name=lead_data.get("caller_name"),
        email=lead_data.get("email"),
        phone=lead_data.get("phone"),
        callback_time=lead_data.get("callback_time"),
        raw_transcript=transcript_text,
        interested=lead_data.get("interested"),
    )

    lead = LeadRecord(
        id=row_id,
        run_id=req.run_id,
        company_name=company_name,
        caller_name=lead_data.get("caller_name"),
        email=lead_data.get("email"),
        phone=lead_data.get("phone"),
        callback_time=lead_data.get("callback_time"),
        conversation_id=req.conversation_id,
        interested=lead_data.get("interested"),
    )

    return LeadExtractResponse(success=True, lead=lead, message="Lead extracted successfully")


@app.get("/voice/leads/{run_id}")
async def voice_leads_list(run_id: str):
    """Return all leads captured for a given pipeline run."""
    return get_leads_for_run(run_id)
