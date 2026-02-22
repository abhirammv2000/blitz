"""FastAPI app — Blitz pipeline backend.

Endpoints:
  POST /pipeline/start           — Start a pipeline run; returns SSE stream
  POST /pipeline/{run_id}/resume — Resume from interrupt with a human decision; returns SSE stream
  GET  /health                   — Health check

CORS is configured for the Vite dev server (localhost:5173). Without this,
the browser EventSource will be blocked by CORS policy.

graph.astream() is used (async) inside async FastAPI endpoints to avoid blocking
the event loop.

The AsyncSqliteSaver context manager is opened via build_graph() in FastAPI's
lifespan event and kept alive for the app's entire lifetime so the checkpointer
connection is never dropped between requests.

SSE event types emitted by both /pipeline/start and /pipeline/{run_id}/resume:
  {"type": "init", "run_id": "..."}          — immediately on start (start only)
  {"type": "progress", "step": "...", ...}   — sub-step progress from research queue
  {"type": "state", "data": {...}}           — after each node updates state
  {"type": "interrupted", "step": N}        — when interrupt() pauses the graph
  {"type": "error", "message": "..."}       — on unexpected exceptions
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel

from agents.agent_0_research.progress import cleanup_queue, get_queue
from graph import build_graph

from pathlib import Path
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env", override=True)
load_dotenv(_backend_dir.parent / ".env", override=True)

# ---------------------------------------------------------------------------
# App-level graph instance (set during lifespan startup)
# ---------------------------------------------------------------------------

graph = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Open AsyncSqliteSaver + compile graph for the app's lifetime."""
    global graph  # noqa: PLW0603
    async with build_graph() as compiled_graph:
        graph = compiled_graph
        yield
    # build_graph() context manager closes SQLite connection on exit


app = FastAPI(title="Blitz Pipeline API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PipelineStartRequest(BaseModel):
    url: str


class ResumeRequest(BaseModel):
    decision: dict[str, Any]


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def sse_event(data: dict) -> str:
    """Format a dict as an SSE data event string."""
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Shared streaming helper
# ---------------------------------------------------------------------------


async def stream_graph_with_progress(run_id: str, graph_input: Any, config: dict):
    """Async generator that multiplexes progress queue events with graph state events.

    Runs graph.astream() as a background asyncio task while concurrently draining
    the run's progress queue. This lets sub-step events from the research node
    (tavily, firecrawl, aeo) reach the client in real time, interleaved with
    node-boundary state events.

    Yields SSE-formatted strings for:
      - progress events from asyncio.Queue ({"type": "progress", "step": ..., ...})
      - state events from graph chunks   ({"type": "state", "data": {...}})
      - interrupted event when graph pauses ({"type": "interrupted", "step": N})
      - error event on unexpected exception  ({"type": "error", "message": "..."})

    Cleans up the progress queue for this run_id after the stream ends.

    Args:
        run_id: The pipeline run identifier (used to look up the progress queue).
        graph_input: Initial state dict or Command(resume=...) passed to graph.astream().
        config: LangGraph config dict with configurable thread_id.
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
            # Drain progress events from research node's asyncio.Queue
            while True:
                try:
                    evt = queue.get_nowait()
                    yield sse_event({"type": "progress", **evt})
                except asyncio.QueueEmpty:
                    break

            # Drain graph state results accumulated by graph_runner
            while results:
                chunk = results.pop(0)
                step = chunk.get("current_step", 0)
                if "__interrupt__" in chunk:
                    # Extract interrupt payload (contains agent output for HITL review)
                    interrupts = chunk["__interrupt__"]
                    interrupt_data = None
                    if interrupts and len(interrupts) > 0:
                        iv = interrupts[0]
                        interrupt_data = iv.value if hasattr(iv, 'value') else iv
                    yield sse_event({"type": "interrupted", "step": step, "data": interrupt_data})
                    return
                safe = {k: v for k, v in chunk.items() if not k.startswith("__")}
                yield sse_event({"type": "state", "data": safe})

            await asyncio.sleep(0.05)

        # Task finished — surface any exception
        if graph_error is not None:
            yield sse_event({"type": "error", "message": str(graph_error)})
            return

        # Drain remaining progress events after graph completes
        while True:
            try:
                evt = queue.get_nowait()
                yield sse_event({"type": "progress", **evt})
            except asyncio.QueueEmpty:
                break

        # Drain remaining state results
        interrupted_step = 0
        while results:
            chunk = results.pop(0)
            step = chunk.get("current_step", 0)
            if "__interrupt__" in chunk:
                interrupts = chunk["__interrupt__"]
                interrupt_data = None
                if interrupts and len(interrupts) > 0:
                    iv = interrupts[0]
                    interrupt_data = iv.value if hasattr(iv, 'value') else iv
                yield sse_event({"type": "interrupted", "step": step, "data": interrupt_data})
                return
            interrupted_step = step
            safe = {k: v for k, v in chunk.items() if not k.startswith("__")}
            yield sse_event({"type": "state", "data": safe})

        # If stream ended without an explicit interrupt event, emit it now
        # (graph completed normally or all chunks were drained)
        yield sse_event({"type": "interrupted", "step": interrupted_step})

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
    """Start a new pipeline run and stream state + progress updates as SSE.

    The SSE stream yields events in order:
      {"type": "init", "run_id": "..."}          — immediately, before graph starts
      {"type": "progress", "step": "...", ...}   — sub-step progress from research node
      {"type": "state", "data": {...}}           — after each node updates state
      {"type": "interrupted", "step": N}        — when interrupt() pauses the graph
      {"type": "error", "message": "..."}       — on unexpected exceptions
    """
    run_id = str(uuid.uuid4())

    async def event_stream():
        # Emit init immediately so frontend can store run_id before graph starts
        yield sse_event({"type": "init", "run_id": run_id})

        initial_state: dict[str, Any] = {
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

# Track image generation count per run to enforce server-side cap
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


@app.post("/pipeline/{run_id}/resume")
async def pipeline_resume(run_id: str, body: ResumeRequest):
    """Resume a paused pipeline run and stream progress as SSE.

    Uses Command(resume=...) to inject the human decision back into the graph.
    AsyncSqliteSaver restores the checkpoint for the given thread_id (run_id),
    allowing execution to continue from the interrupted node.

    On reject, the research node re-runs and publishes new progress events to
    the run's asyncio.Queue. The SSE stream drains these alongside graph state
    events so the frontend can track re-generation progress in real time.

    The SSE stream yields the same event types as /pipeline/start (no init event).
    """
    config = {"configurable": {"thread_id": run_id}}

    async def event_stream():
        async for event in stream_graph_with_progress(
            run_id, Command(resume=body.decision), config
        ):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")
