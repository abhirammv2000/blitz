"""Fault-injection benchmark: how much do the Router's retries reduce failures?

The pipeline's `core/llm.py` sets `num_retries`, a typed `RetryPolicy`, timeouts
and cross-provider fallback on the LiteLLM Router. This measures what that buys.

It builds the *real* production Router, patches the underlying model call to
fail transiently at a chosen rate, and measures the per-call failure rate for a
bare single-attempt call versus the full config (retries + typed policy +
cross-provider failover). It projects that onto a K-call pipeline run and sweeps
a few failure rates. No network, no spend.

    cd backend
    python reliability_benchmark.py
    python reliability_benchmark.py --trials 1000 --calls-per-run 12

The injected failure rate is an assumption, not a measurement of any real
provider, and failures are injected independently per attempt. A real
rate-limit storm is correlated (a retry 100ms later hits the same wall), so this
flatters retries; the cross-provider failover is what carries a correlated
outage. Read the output as "given independent transient failures at rate p, the
resilient Router takes run failures from X% to Y%".
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("OPENAI_API_KEY", "benchmark-dummy")
os.environ.setdefault("GEMINI_API_KEY", "benchmark-dummy")

import litellm  # noqa: E402
import litellm.main as litellm_main  # noqa: E402
from litellm.types.utils import Choices, Message, ModelResponse, Usage  # noqa: E402

from app.core.llm import build_router  # noqa: E402

litellm.set_verbose = False
for _noisy in ("LiteLLM", "LiteLLM Router", "litellm"):
    logging.getLogger(_noisy).setLevel(logging.CRITICAL)

# Retryable errors, rotated so the RetryPolicy's per-type limits all get hit.
_TRANSIENT = [
    lambda: litellm.RateLimitError("injected rate limit", llm_provider="openai", model="gpt-4o"),
    lambda: litellm.Timeout("injected timeout", model="gpt-4o", llm_provider="openai"),
    lambda: litellm.InternalServerError("injected 500", llm_provider="openai", model="gpt-4o"),
]

_n = 0


def _ok() -> ModelResponse:
    return ModelResponse(
        choices=[Choices(message=Message(content="ok", role="assistant"), finish_reason="stop", index=0)],
        model="gpt-4o",
        usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def _install(p: float, rng: random.Random) -> None:
    """Patch the underlying model call to fail transiently at rate p, and make
    retry backoff instant so the benchmark finishes in seconds."""
    async def flaky(*args, **kwargs):
        global _n
        _n += 1
        if rng.random() < p:
            raise _TRANSIENT[_n % len(_TRANSIENT)]()
        return _ok()

    litellm.acompletion = flaky
    litellm_main.acompletion = flaky

    _real_sleep = asyncio.sleep
    async def no_backoff(delay, *a, **k):
        await _real_sleep(0, *a, **k)
    asyncio.sleep = no_backoff  # noqa: A001 - benchmark only, restored on exit


async def _call_fail_rate(resilience_disabled: bool, trials: int, p: float, seed: int) -> float:
    """Fraction of single calls that ultimately fail. Fresh Router per trial so
    one trial's cooldowns can't poison the next."""
    rng = random.Random(seed)
    _install(p, rng)
    failed = 0
    for _ in range(trials):
        router = build_router(resilience_disabled=resilience_disabled)
        try:
            await router.acompletion(model="primary", messages=[{"role": "user", "content": "x"}])
        except Exception:
            failed += 1
    return failed / trials


def _run_fail_rate(call_fail_rate: float, k: int) -> float:
    return 1.0 - (1.0 - call_fail_rate) ** k


async def main() -> None:
    ap = argparse.ArgumentParser(description="Router resilience fault-injection benchmark")
    ap.add_argument("--calls-per-run", type=int, default=12,
                    help="LLM calls in one pipeline run, for the projection (default 12)")
    ap.add_argument("--trials", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    k = args.calls_per_run
    print(f"{args.trials} trials per cell. 'run' = {k} sequential calls, projected as "
          f"1-(1-call_failure)^{k}.\n")
    print(f"  {'inject/attempt':<16}{'bare call':<12}{'router call':<13}{'bare run':<12}{'router run'}")

    for p in (0.05, 0.10, 0.20, 0.30):
        bare = await _call_fail_rate(True, args.trials, p, args.seed)
        router = await _call_fail_rate(False, args.trials, p, args.seed)
        print(f"  {p:<16.0%}{bare:<12.1%}{router:<13.2%}"
              f"{_run_fail_rate(bare, k):<12.1%}{_run_fail_rate(router, k):.1%}")

    print("\n'bare call' is one attempt, no retry, no failover. 'router call' is the "
          "production config\n(num_retries + typed RetryPolicy + cross-provider failover).")


if __name__ == "__main__":
    asyncio.run(main())
