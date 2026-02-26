"""FastAPI app — Blitz pipeline backend.

Endpoints:
  POST /pipeline/start           — Start a pipeline run; returns SSE stream
  GET  /health                   — Health check

CORS is configured for the Vite dev server (localhost:5173+).

SSE event types emitted by /pipeline/start:
  {"type": "init", "run_id": "..."}          — immediately on start
  {"type": "progress", "step": "...", ...}   — sub-step progress from research queue
  {"type": "state", "data": {...}}           — after each node updates state
  {"type": "done"}                           — pipeline completed successfully
  {"type": "error", "message": "..."}       — on unexpected exceptions
"""

import asyncio
import json
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.agent_0_research.progress import cleanup_queue, get_queue
from agents.agent_voice.models import (
    SetupCheckResponse,
    VoiceSessionRequest,
    VoiceSessionResponse,
    TranscriptMessage,
    TranscriptResponse,
)
from agents.agent_voice.elevenlabs_client import (
    build_agent_prompt,
    check_setup,
    get_agent_id,
    get_conversation_token,
    get_transcript,
    update_agent_prompt,
)
from db import get_agent_output
from graph import build_graph

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{port}" for port in range(5173, 5200)],
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
    """Async generator that multiplexes progress queue events with graph state events.

    Yields SSE-formatted strings for:
      - progress events from asyncio.Queue
      - state events from graph chunks
      - done event when graph completes
      - error event on unexpected exception
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

    try:
        while not task.done():
            while True:
                try:
                    evt = queue.get_nowait()
                    yield sse_event({"type": "progress", **evt})
                except asyncio.QueueEmpty:
                    break

            while results:
                chunk = results.pop(0)
                safe = {k: v for k, v in chunk.items() if not k.startswith("__")}
                yield sse_event({"type": "state", "data": safe})

            await asyncio.sleep(0.05)

        if graph_error is not None:
            yield sse_event({"type": "error", "message": str(graph_error)})
            return

        # Drain remaining progress events
        while True:
            try:
                evt = queue.get_nowait()
                yield sse_event({"type": "progress", **evt})
            except asyncio.QueueEmpty:
                break

        # Drain remaining state results
        while results:
            chunk = results.pop(0)
            safe = {k: v for k, v in chunk.items() if not k.startswith("__")}
            yield sse_event({"type": "state", "data": safe})

        yield sse_event({"type": "done"})

    finally:
        cleanup_queue(run_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/pipeline/start")
async def pipeline_start(payload: PipelineStartRequest):
    """Start a new pipeline run and stream state + progress updates as SSE."""
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

    raw_research = get_agent_output(req.run_id, "research_decision")
    company_name = "our company"
    if raw_research:
        import json as _json
        try:
            research_data = _json.loads(raw_research)
            company_name = research_data.get("company_name") or research_data.get("name") or "our company"
            research_dossier_text = (
                research_data.get("executive_summary")
                or research_data.get("summary")
                or str(research_data)[:3000]
            )
        except (ValueError, TypeError):
            research_dossier_text = str(raw_research)[:3000]
    else:
        research_dossier_text = ""

    agent_prompt = build_agent_prompt(req.script_text, research_dossier_text, company_name)

    try:
        await update_agent_prompt(agent_prompt, req.first_message)
        token = await get_conversation_token()
    except Exception as exc:  # noqa: BLE001
        import httpx as _httpx
        if isinstance(exc, _httpx.HTTPStatusError):
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs API error: {exc.response.status_code} {exc.response.text}",
            ) from exc
        raise

    return VoiceSessionResponse(
        agent_id=get_agent_id(),
        token=token,
        overrides={},
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
