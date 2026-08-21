"""Hooks into LiteLLM so every model call gets written to the telemetry table.

This is a LiteLLM callback rather than a wrapper around our own code because the
router retries and falls back on its own. Those extra attempts get billed, and a
wrapper around our call sites would never see them.
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
    """Writes a row for each call LiteLLM finishes, successful or not."""

    def _record(self, kwargs: dict, response_obj, start_time, end_time, status: str, error_type=None):
        try:
            params = kwargs.get("litellm_params") or {}
            metadata = params.get("metadata") or {}

            # We store both: `model` is what answered, `model_group` is what we
            # asked for. If they disagree, the fallback kicked in.
            model = kwargs.get("model")
            # The AEO probes skip the router and name a model directly, so they
            # have no group. Call that "direct" rather than leaving it blank.
            model_group = metadata.get("model_group") or params.get("model_group") or "direct"

            usage = getattr(response_obj, "usage", None)
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

            # LiteLLM works the price out for us. Don't hardcode rates here,
            # they change.
            cost = kwargs.get("response_cost") or 0.0

            record_call(
                run_id=metadata.get("run_id") or current_run_id(),
                agent=metadata.get("agent") or current_agent(),
                model_group=model_group,
                model=model,
                provider=_provider_of(model),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=float(cost),
                latency_ms=_duration_ms(start_time, end_time),
                status=status,
                error_type=error_type,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telemetry callback failed: %s", exc)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._record(kwargs, response_obj, start_time, end_time, "success")

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        exc = kwargs.get("exception")
        self._record(
            kwargs, response_obj, start_time, end_time,
            "failure", type(exc).__name__ if exc else "UnknownError",
        )

    # LiteLLM calls the sync pair for sync requests, so both need to exist.
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
    """Register the callback with LiteLLM. Safe to call twice."""
    global _installed
    if _installed:
        return

    import litellm

    from app.telemetry.store import init_telemetry_table

    init_telemetry_table()
    litellm.callbacks = [*(litellm.callbacks or []), BlitzTelemetryLogger()]
    _installed = True
    logger.info("Telemetry enabled")
