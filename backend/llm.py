"""LiteLLM Router singleton — all load-bearing LLM calls go through this.

Design decisions:
- Single shared Router instance (module-level singleton via get_router())
- Primary model: openai/gpt-4o — best reasoning for agent tasks
- Fallback model: gemini/gemini-3.6-flash — automatic when the primary fails
- Reliability is configured on the Router itself (timeout, retries, retry policy)
  rather than hand-rolled at each of the ~7 agent call sites.

Timeout sizing is based on measured latency, not guesswork. Observed p50 for the
agent synthesis calls on an idle system: profile 11.5s, audience 12.9s,
content 29.5s, ads 29.5s, sales 15-34s. The same sales call has been observed at
both 15.6s and 33.5s on identical input, so per-attempt timeouts must absorb
several multiples of p50 or normal variance reads as failure. The fallback is
slower than the primary on large prompts (44.1s vs 28.6s on the sales prompt),
so the timeout must leave the fallback room to actually finish.

NOTE: The `gemini/` prefix is required by LiteLLM for Google Gemini models.
Gemini 2.5 models return 404 ("no longer available to new users") — do not
reintroduce them here without re-verifying against the live API.
"""

import os

from litellm import Router
from litellm.router import RetryPolicy

_router: Router | None = None

# Per-attempt ceiling. Generous by design: a slow call that succeeds is far
# cheaper than a fast failure that discards the whole pipeline run.
REQUEST_TIMEOUT_SECONDS = 90.0

PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "openai/gpt-4o")
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "gemini/gemini-3.6-flash")


def get_router() -> Router:
    """Get or create the LiteLLM Router with primary (OpenAI) and fallback (Gemini).

    Thread-safe via Python's GIL for the simple singleton assignment.
    Returns the same Router instance on every call after initialization.

    Call it with model="primary"; the Router handles retries, rate-limit backoff,
    and failover to Gemini transparently.
    """
    global _router
    if _router is None:
        _router = Router(
            model_list=[
                {
                    "model_name": "primary",
                    "litellm_params": {
                        "model": PRIMARY_MODEL,
                        "api_key": os.environ.get("OPENAI_API_KEY", ""),
                    },
                },
                {
                    "model_name": "fallback",
                    "litellm_params": {
                        "model": FALLBACK_MODEL,
                        "api_key": os.environ.get("GEMINI_API_KEY", ""),
                    },
                },
            ],
            fallbacks=[{"primary": ["fallback"]}],
            timeout=REQUEST_TIMEOUT_SECONDS,
            num_retries=2,
            # Retry what is worth retrying. Bad requests and auth failures are
            # deterministic — retrying them just burns latency before the same error.
            retry_policy=RetryPolicy(
                TimeoutErrorRetries=2,
                RateLimitErrorRetries=3,
                InternalServerErrorRetries=2,
                BadRequestErrorRetries=0,
                AuthenticationErrorRetries=0,
                ContentPolicyViolationErrorRetries=0,
            ),
            # Take a route out of rotation briefly after repeated failures so a
            # provider outage fails over instead of retrying into a wall.
            allowed_fails=3,
            cooldown_time=30,
        )
    return _router


def describe_exception(exc: BaseException) -> str:
    """Render an exception as a message that is actually useful in the UI.

    asyncio.TimeoutError — the most common pipeline failure — has an empty
    str(), which surfaced to users as a blank error. Always include the type.
    """
    detail = str(exc).strip()
    name = type(exc).__name__
    return f"{name}: {detail}" if detail else name
