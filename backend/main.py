"""FastAPI app — Blitz pipeline backend.

Endpoints:
  POST /pipeline/start           — Start a pipeline run; returns SSE stream
  POST /pipeline/{run_id}/resume — Resume from interrupt with a human decision
  GET  /health                   — Health check

CORS is configured for the Vite dev server (localhost:5173). Without this,
the browser EventSource will be blocked by CORS policy.

graph.astream() is used (async) inside async FastAPI endpoints to avoid blocking
the event loop.

The AsyncSqliteSaver context manager is opened via build_graph() in FastAPI's
lifespan event and kept alive for the app's entire lifetime so the checkpointer
connection is never dropped between requests.
"""

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

from graph import build_graph

load_dotenv()

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
    allow_origins=["http://localhost:5173"],
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
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/pipeline/start")
async def pipeline_start(payload: PipelineStartRequest):
    """Start a new pipeline run and stream state updates as SSE.

    The SSE stream yields events in order:
      {"type": "init", "run_id": "..."}   — immediately, before graph starts
      {"type": "state", "data": {...}}    — after each node updates state
      {"type": "interrupted", "step": N} — when interrupt() pauses the graph
      {"type": "error", "message": "..."}— on unexpected exceptions
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

        try:
            interrupted_step = 0
            was_interrupted = False
            # astream() yields the full state dict after each node executes.
            # When interrupt() is called, the graph emits a chunk containing
            # '__interrupt__' with Interrupt objects (not JSON-serializable).
            # We strip '__interrupt__' before emitting the SSE state event.
            async for chunk in graph.astream(
                initial_state,
                config=config,
                stream_mode="values",
            ):
                if isinstance(chunk, dict):
                    interrupted_step = chunk.get("current_step", 0)
                    if "__interrupt__" in chunk:
                        # Graph paused — emit interrupted event and stop streaming
                        was_interrupted = True
                        yield sse_event({"type": "interrupted", "step": interrupted_step})
                        break
                    yield sse_event({"type": "state", "data": chunk})
            # Stream ended naturally — emit interrupted if not already done
            if not was_interrupted:
                yield sse_event({"type": "interrupted", "step": interrupted_step})
        except Exception as exc:  # noqa: BLE001
            yield sse_event({"type": "error", "message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/pipeline/{run_id}/resume")
async def pipeline_resume(run_id: str, body: ResumeRequest):
    """Resume a paused pipeline run from its interrupt point.

    Uses Command(resume=...) to inject the human decision back into the graph.
    AsyncSqliteSaver restores the checkpoint for the given thread_id (run_id),
    allowing execution to continue from the interrupted node.
    """
    config = {"configurable": {"thread_id": run_id}}
    async for _chunk in graph.astream(
        Command(resume=body.decision),
        config=config,
        stream_mode="values",
    ):
        pass  # drain the stream until next interrupt or completion
    return {"status": "resumed", "run_id": run_id}
