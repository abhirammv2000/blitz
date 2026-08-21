"""Tracks which run and agent the current LLM call belongs to.

The telemetry callback needs to know who made a call, but LiteLLM doesn't tell
it. We stash the answer in a contextvar instead of passing it to every
acompletion() call, so a call added later still gets tagged.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager

_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("blitz_run_id", default=None)
_agent: contextvars.ContextVar[str | None] = contextvars.ContextVar("blitz_agent", default=None)


def current_run_id() -> str | None:
    return _run_id.get()


def current_agent() -> str | None:
    return _agent.get()


@contextmanager
def agent_context(run_id: str | None, agent: str | None):
    """Tag every LLM call made inside this block.

    Each asyncio task gets its own copy, so two pipeline runs happening at once
    don't get each other's labels.
    """
    run_token = _run_id.set(run_id)
    agent_token = _agent.set(agent)
    try:
        yield
    finally:
        _run_id.reset(run_token)
        _agent.reset(agent_token)
