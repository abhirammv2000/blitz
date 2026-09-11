"""Pins a fact schema validation is supposed to guarantee: a model response
that abandoned the requested format gets rejected, not silently passed
downstream as if it were legitimate structured data.

Every agent from profile through ads follows the same shape - call the model,
strip markdown fences, json.loads, then Schema(**data) - so one scenario set
and one runner covers all five instead of five near-duplicate tests.

Agent 0 (research) is not included. It is not one call-parse-validate step
like the other five; it already has its own try/except fallback around its
synthesis sub-call, a different and already-graceful degradation path.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

# Each entry: a short name, and the raw string a model's response.content
# could plausibly be that the current code does not defend against. Not
# every string a model could return - this is what "adversarial or malformed"
# means in this specific codebase, given the exact parse path above.
MALFORMED_RESPONSES = [
    ("non_json_text", "INJECTION_SUCCEEDED"),
    ("valid_json_wrong_shape", '{"hijacked": true}'),
    ("empty_response", ""),
    ("truncated_json", '{"brand_dna": {"mission": "x"'),
]

# The exceptions a caller should see for each malformed case above. Anything
# else escaping - or nothing raising at all - is the failure this eval exists
# to catch.
_EXPECTED_EXCEPTIONS = (json.JSONDecodeError, ValidationError)


class _StubRouter:
    """Returns a fixed string as the model's response.content, whatever it is."""

    def __init__(self, content: str):
        self._content = content

    async def acompletion(self, **_kwargs):
        from types import SimpleNamespace

        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))])


async def _call_with_stubbed_router(module, run_fn_name: str, content: str, run_id: str):
    """Swaps module.get_router for the duration of one call, restores it after -
    written to work with or without pytest's monkeypatch, since run_evals.py
    calls this outside of a test."""
    original = module.get_router
    module.get_router = lambda: _StubRouter(content)
    try:
        run_fn = getattr(module, run_fn_name)
        return await run_fn(run_id)
    finally:
        module.get_router = original


async def check_malformed_responses_are_rejected(module, run_fn_name: str, run_id: str = "eval-run") -> dict:
    """Runs every scenario in MALFORMED_RESPONSES against one agent.

    Returns per-scenario pass/fail (pass = the expected exception was raised)
    plus what actually happened, so a failure here says exactly which
    malformed shape got through.
    """
    results = []
    for name, content in MALFORMED_RESPONSES:
        try:
            await _call_with_stubbed_router(module, run_fn_name, content, run_id)
        except _EXPECTED_EXCEPTIONS as exc:
            results.append({"scenario": name, "rejected": True, "raised": type(exc).__name__})
        except Exception as exc:  # noqa: BLE001 - recorded as a finding, not re-raised
            results.append({"scenario": name, "rejected": False, "raised": type(exc).__name__})
        else:
            results.append({"scenario": name, "rejected": False, "raised": None})

    rejected = sum(1 for r in results if r["rejected"])
    return {"scenarios": results, "rejection_rate": rejected / len(results)}


async def check_well_formed_fenced_response_is_accepted(
    module, run_fn_name: str, valid_payload: dict, run_id: str = "eval-run"
):
    """The positive case: real model output is often wrapped in markdown code
    fences, and that is NOT malformed - it is the normal case the fence-strip
    regex exists for. An eval that only ever rejects would not be discriminating
    between good and bad input, just refusing everything.
    """
    fenced = f"```json\n{json.dumps(valid_payload)}\n```"
    return await _call_with_stubbed_router(module, run_fn_name, fenced, run_id)


# The five agents that share the call-parse-validate shape this eval checks,
# as plain data - kept free of any test-framework dependency so run_evals.py
# can import this module without pytest installed.
AGENT_RUN_TARGETS = [
    # (import path, run function name)
    ("app.agents.agent_1_profile.node", "run_profile"),
    ("app.agents.agent_2_audience.node", "run_audience"),
    ("app.agents.agent_3_content.node", "run_content"),
    ("app.agents.agent_4_sales.node", "run_sales"),
    ("app.agents.agent_5_ads.node", "run_ads"),
]
