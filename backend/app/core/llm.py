"""Shared LiteLLM router. Every model call in the pipeline goes through here.

There are two groups. "primary" is for the agent write-ups that need a good
model; "mini" is for the small stuff like pulling a company name out of a page.
Each one falls back to the other provider if the first is down or out of credit.

Retries and timeouts are set on the router instead of at each call site.

Careful with the timeout. The sales call takes anywhere from 15 to 34 seconds
and the fallback is slower again, so anything near 30s starts killing calls that
would have finished. Gemini 2.5 models 404 now, so don't put them back without
checking they still work.
"""

import os

from litellm import Router
from litellm.router import RetryPolicy

from app.config import settings

_router: Router | None = None
_langfuse_installed = False

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


def build_router(resilience_disabled: bool = False) -> Router:
    """Construct a Router with the production config.

    ``resilience_disabled`` strips the retries, the per-error policy and the
    cross-provider fallback, leaving a bare single-attempt call. Only the
    reliability benchmark uses it, as the "before" baseline; production always
    calls this with the default.
    """
    if resilience_disabled:
        return Router(
            model_list=[
                _entry("primary", settings.primary_model),
                _entry("mini", settings.mini_model),
            ],
            timeout=settings.request_timeout_seconds,
            num_retries=0,
        )

    return Router(
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
        # deterministic - retrying them just burns latency before the same error.
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
        _router = build_router()
    return _router


def install_langfuse_tracing() -> None:
    """Add Langfuse tracing alongside the existing telemetry callback.

    No-ops if no Langfuse keys are configured, the same way the app boots
    fine without OpenAI/Gemini keys and fails at the call that needs one -
    tracing is additive, not a requirement to run the pipeline. Safe to call
    twice.

    litellm's bundled Langfuse integration reads LANGFUSE_HOST from the
    environment specifically - verified against its source, not assumed -
    while Langfuse's own onboarding UI calls the same value LANGFUSE_BASE_URL.
    That env var is set here rather than asked of whoever deploys this, so
    the .env file can hold exactly what Langfuse's UI told them to paste.
    """
    global _langfuse_installed
    if _langfuse_installed:
        return
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return

    import litellm

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_base_url)

    # Verified directly that a plain string entry here coexists on the same
    # list as an already-instantiated custom logger object - litellm resolves
    # "langfuse" to its own bundled integration wherever it appears.
    litellm.callbacks = [*(litellm.callbacks or []), "langfuse"]
    _langfuse_installed = True


def describe_exception(exc: BaseException) -> str:
    """Render an exception as a message that is actually useful in the UI.

    asyncio.TimeoutError - the most common pipeline failure - has an empty
    str(), which surfaced to users as a blank error. Always include the type.
    """
    detail = str(exc).strip()
    name = type(exc).__name__
    return f"{name}: {detail}" if detail else name
