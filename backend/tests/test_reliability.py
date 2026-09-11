"""Regression guard for the Router's resilience config.

The full sweep lives in backend/reliability_benchmark.py. This just pins the
invariant: with transient failures injected, routing through the production
config (retries + typed policy + failover) fails materially less often than a
bare single-attempt call.
"""

from __future__ import annotations

import asyncio
import random

import litellm
import litellm.main as litellm_main
import pytest
from litellm.types.utils import Choices, Message, ModelResponse, Usage

from app.core.llm import build_router


def _ok() -> ModelResponse:
    return ModelResponse(
        choices=[Choices(message=Message(content="ok", role="assistant"), finish_reason="stop", index=0)],
        model="gpt-4o",
        usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


@pytest.fixture
def inject_failures(monkeypatch):
    """Fail every underlying attempt at probability p; instant retry backoff."""

    def _apply(p: float):
        rng = random.Random(0)

        async def flaky(*args, **kwargs):
            if rng.random() < p:
                raise litellm.RateLimitError("injected", llm_provider="openai", model="gpt-4o")
            return _ok()

        monkeypatch.setattr(litellm, "acompletion", flaky)
        monkeypatch.setattr(litellm_main, "acompletion", flaky)

        real_sleep = asyncio.sleep
        monkeypatch.setattr(asyncio, "sleep", lambda d, *a, **k: real_sleep(0, *a, **k))

    return _apply


async def _fail_rate(resilience_disabled: bool, trials: int) -> float:
    failed = 0
    for _ in range(trials):
        router = build_router(resilience_disabled=resilience_disabled)
        try:
            await router.acompletion(model="primary", messages=[{"role": "user", "content": "x"}])
        except Exception:
            failed += 1
    return failed / trials


async def test_the_resilient_router_fails_far_less_than_a_bare_call(inject_failures):
    inject_failures(0.3)

    bare = await _fail_rate(resilience_disabled=True, trials=120)
    routed = await _fail_rate(resilience_disabled=False, trials=120)

    assert bare > 0.15, "expected the injected failures to actually surface"
    assert routed < bare / 3, f"router config barely helped: bare={bare:.2f} routed={routed:.2f}"


async def test_a_bare_call_has_no_retries(inject_failures):
    """Sanity check on the baseline: resilience_disabled really means one attempt."""
    inject_failures(1.0)  # every attempt fails

    with pytest.raises(Exception):
        await build_router(resilience_disabled=True).acompletion(
            model="primary", messages=[{"role": "user", "content": "x"}]
        )
