"""asyncio.Queue registry for Agent 0 research sub-step progress events.

Each pipeline run gets its own queue, keyed by run_id.
The SSE endpoint reads from this queue to stream progress to the frontend.

Design:
- Module-level dict avoids threading issues (event loop is shared)
- get_queue() creates on demand — call before starting research
- cleanup_queue() removes after SSE stream closes to free memory
"""

from __future__ import annotations

import asyncio

_queues: dict[str, asyncio.Queue] = {}


def get_queue(run_id: str) -> asyncio.Queue:
    """Get or create the asyncio.Queue for a given run_id.

    Creates a new queue if one doesn't exist for this run_id.
    The queue holds progress event dicts: {"step": str, "status": str, ...}

    Args:
        run_id: The pipeline run identifier (UUID4).

    Returns:
        The asyncio.Queue for this run_id.
    """
    if run_id not in _queues:
        _queues[run_id] = asyncio.Queue()
    return _queues[run_id]


def cleanup_queue(run_id: str) -> None:
    """Remove the queue for a given run_id from the registry.

    Call this after the SSE stream closes to prevent memory leaks.

    Args:
        run_id: The pipeline run identifier to clean up.
    """
    _queues.pop(run_id, None)
