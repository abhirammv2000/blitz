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

from litellm import Router
from litellm.router import RetryPolicy

from app.config import settings

_router: Router | None = None

# Kept as module attributes for readability at the call sites below; the values
# themselves are owned by config.Settings and sourced from the environment.
REQUEST_TIMEOUT_SECONDS = settings.request_timeout_seconds


def api_key_for_model(model: str) -> str:
    """Pick the API key matching the model's provider prefix.

    Necessary because the model names are environment-overridable: hardcoding
    OPENAI_API_KEY to the "primary" slot silently sends an OpenAI key to Gemini
    when PRIMARY_MODEL is switched, which fails in a way that looks like the
    primary working while every request is actually served by the fallback.
    """
    if model.startswith("gemini/"):
        return settings.gemini_api_key
    return settings.openai_api_key


# Kept as a private alias so existing callers and tests keep working.
_api_key_for = api_key_for_model


def _entry(name: str, model: str) -> dict:
    return {
        "model_name": name,
        "litellm_params": {"model": model, "api_key": api_key_for_model(model)},
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
                _entry("primary", settings.primary_model),
                _entry("fallback", settings.fallback_model),
                _entry("mini", settings.mini_model),
                _entry("mini_fallback", settings.mini_fallback_model),
            ],
            fallbacks=[
                {"primary": ["fallback"]},
                {"mini": ["mini_fallback"]},
            ],
            timeout=settings.request_timeout_seconds,
            num_retries=settings.llm_num_retries,
            # Retry what is worth retrying. Bad requests and auth failures are
            # deterministic — retrying them just burns latency before the same error.
            retry_policy=RetryPolicy(
                TimeoutErrorRetries=settings.timeout_retries,
                RateLimitErrorRetries=settings.rate_limit_retries,
                InternalServerErrorRetries=settings.server_error_retries,
                BadRequestErrorRetries=0,
                AuthenticationErrorRetries=0,
                ContentPolicyViolationErrorRetries=0,
            ),
            # Take a route out of rotation briefly after repeated failures so a
            # provider outage fails over instead of retrying into a wall.
            allowed_fails=settings.router_allowed_fails,
            cooldown_time=settings.router_cooldown_seconds,
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
