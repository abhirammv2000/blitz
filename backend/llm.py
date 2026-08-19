"""LiteLLM Router singleton — all LLM calls in the pipeline go through this.

Two model groups, so cost tier is a routing decision rather than a hardcoded
model name at each call site:

    "primary"  — the reasoning-heavy agent synthesis calls
    "mini"     — small utility calls (entity extraction, categorisation,
                 summarisation) that do not need the expensive model

Each group has an automatic cross-provider fallback, so no single provider
being down or out of credits is fatal to a run.

Reliability is configured on the Router itself (timeout, retries, retry policy)
rather than hand-rolled at every call site.

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

# Every model is overridable by environment variable so the deployment can swap
# providers — including making Gemini primary — without a code change.
PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "openai/gpt-4o")
PRIMARY_FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "gemini/gemini-3.6-flash")
MINI_MODEL = os.environ.get("MINI_MODEL", "openai/gpt-4o-mini")
MINI_FALLBACK_MODEL = os.environ.get("MINI_FALLBACK_MODEL", "gemini/gemini-3.5-flash-lite")


def _api_key_for(model: str) -> str:
    """Pick the API key matching the model's provider prefix.

    Necessary because the model names are environment-overridable: hardcoding
    OPENAI_API_KEY to the "primary" slot silently sends an OpenAI key to Gemini
    when PRIMARY_MODEL is switched, which fails in a way that looks like the
    primary working while every request is actually served by the fallback.
    """
    if model.startswith("gemini/"):
        return os.environ.get("GEMINI_API_KEY", "")
    return os.environ.get("OPENAI_API_KEY", "")


def _entry(name: str, model: str) -> dict:
    return {
        "model_name": name,
        "litellm_params": {"model": model, "api_key": _api_key_for(model)},
    }


def get_router() -> Router:
    """Get or create the shared LiteLLM Router.

    Thread-safe via Python's GIL for the simple singleton assignment.
    Returns the same Router instance on every call after initialization.

    Call it with model="primary" for agent synthesis or model="mini" for cheap
    utility calls; the Router handles retries, rate-limit backoff, and failover
    to the other provider transparently.
    """
    global _router
    if _router is None:
        _router = Router(
            model_list=[
                _entry("primary", PRIMARY_MODEL),
                _entry("fallback", PRIMARY_FALLBACK_MODEL),
                _entry("mini", MINI_MODEL),
                _entry("mini_fallback", MINI_FALLBACK_MODEL),
            ],
            fallbacks=[
                {"primary": ["fallback"]},
                {"mini": ["mini_fallback"]},
            ],
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
