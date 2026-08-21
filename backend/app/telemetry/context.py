"""Ambient run/agent identity for telemetry.

Design note — why contextvars rather than passing metadata at each call site:

LiteLLM will attach anything you hand it in `metadata=` to the logging callback,
which works but requires every `acompletion(...)` to remember to do it. The
moment someone adds a call and forgets, that spend disappears from the numbers,
and a cost dashboard that silently under-reports is worse than none at all.

A contextvar set once per agent is inherited by everything that runs underneath
it, including the Router's own retry and fallback attempts — which are exactly
the calls a naive instrumentation misses, and exactly the ones worth seeing.

contextvars are async-safe: each task gets its own copy, so concurrent pipeline
runs do not read each other's identity.
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
    """Tag every LLM call made inside this block with a run and agent.

    Restores the previous values on exit so nested or sequential agents cannot
    leak identity into one another.
    """
    run_token = _run_id.set(run_id)
    agent_token = _agent.set(agent)
    try:
        yield
    finally:
        _run_id.reset(run_token)
        _agent.reset(agent_token)
