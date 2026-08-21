"""LiteLLM callback that records every LLM call.

Design notes:

- Implemented as a LiteLLM `CustomLogger` rather than a wrapper around our own
  call sites. The Router retries and fails over internally; a wrapper sees one
  logical call where three physical ones were billed. The callback sees each
  attempt, so the numbers reconcile against the provider's invoice — which is
  the whole point of cost telemetry.
- Cost comes from LiteLLM's own `response_cost`, never a local price table.
  Model prices change, and a hardcoded table produces confidently wrong numbers.
- Every handler swallows its own exceptions. Observability must not be able to
  break the thing it observes.
"""

from __future__ import annotations

import logging

from litellm.integrations.custom_logger import CustomLogger

from app.telemetry.context import current_agent, current_run_id
from app.telemetry.store import record_call

logger = logging.getLogger(__name__)


def _provider_of(model: str | None) -> str:
    if not model:
        return "unknown"
    lowered = model.lower()
    if "gemini" in lowered:
        return "gemini"
    if "gpt" in lowered or "openai" in lowered or lowered.startswith("o1"):
        return "openai"
    return lowered.split("/")[0]


def _duration_ms(start, end) -> int:
    try:
        return int((end - start).total_seconds() * 1000)
    except Exception:  # noqa: BLE001
        return 0


class BlitzTelemetryLogger(CustomLogger):
    """Writes one row per LLM call attempt."""

    def _record(self, kwargs: dict, response_obj, start_time, end_time, status: str, error_type=None):
        try:
            params = kwargs.get("litellm_params") or {}
            metadata = params.get("metadata") or {}

            # `model` is what actually served the request; the model group is what
            # we asked for. Keeping both is what makes a failover visible: a row
            # with model_group=primary and a gemini model means the fallback ran.
            model = kwargs.get("model")
            # Calls that bypass the Router — the AEO probes name their model
            # directly on purpose — have no model group. Labelling them "direct"
            # rather than leaving them null keeps them visible as a deliberate
            # choice instead of looking like missing data.
            model_group = metadata.get("model_group") or params.get("model_group") or "direct"

            usage = getattr(response_obj, "usage", None)
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

            cost = kwargs.get("response_cost")
            if cost is None:
                cost = 0.0

            record_call(
                run_id=metadata.get("run_id") or current_run_id(),
                agent=metadata.get("agent") or current_agent(),
                model_group=model_group,
                model=model,
                provider=_provider_of(model),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=float(cost or 0.0),
                latency_ms=_duration_ms(start_time, end_time),
                status=status,
                error_type=error_type,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telemetry callback failed (continuing): %s", exc)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._record(kwargs, response_obj, start_time, end_time, "success")

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        exc = kwargs.get("exception")
        self._record(
            kwargs, response_obj, start_time, end_time,
            "failure", type(exc).__name__ if exc else "UnknownError",
        )

    # Sync variants: LiteLLM picks the matching pair for the call style used.
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._record(kwargs, response_obj, start_time, end_time, "success")

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        exc = kwargs.get("exception")
        self._record(
            kwargs, response_obj, start_time, end_time,
            "failure", type(exc).__name__ if exc else "UnknownError",
        )


_installed = False


def install_telemetry() -> None:
    """Register the callback with LiteLLM. Safe to call more than once."""
    global _installed
    if _installed:
        return

    import litellm

    from app.telemetry.store import init_telemetry_table

    init_telemetry_table()
    litellm.callbacks = [*(litellm.callbacks or []), BlitzTelemetryLogger()]
    _installed = True
    logger.info("Blitz telemetry installed")
