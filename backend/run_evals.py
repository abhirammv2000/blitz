"""Eval report: schema conformance under malformed model responses, and how
well a fixed set of example ad copy grounds itself in its research.

Neither section makes a network call. The conformance check stubs the model
response directly (see app/evals/schema_conformance.py); the grounding check
scores a fixed example set of copy against a fixed research fixture, not live
generation. This measures the detectors, the same way reliability_benchmark.py
measures the retry config rather than a real provider.

    cd backend
    python run_evals.py
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("OPENAI_API_KEY", "eval-dummy")
os.environ.setdefault("GEMINI_API_KEY", "eval-dummy")

for _noisy in ("LiteLLM", "LiteLLM Router", "litellm"):
    logging.getLogger(_noisy).setLevel(logging.CRITICAL)

# Every agent logs a warning when its upstream context is missing - expected
# and harmless here, since "eval-run" was never a real pipeline run, but noisy
# enough to defeat the point of a report over pytest's silent pass/fail.
for _agent_module in (
    "app.agents.agent_1_profile.node",
    "app.agents.agent_2_audience.node",
    "app.agents.agent_3_content.node",
    "app.agents.agent_4_sales.node",
    "app.agents.agent_5_ads.node",
):
    logging.getLogger(_agent_module).setLevel(logging.ERROR)

from app.config import settings  # noqa: E402
from app.evals.grounding import score_grounding  # noqa: E402
from app.evals.schema_conformance import (  # noqa: E402
    AGENT_RUN_TARGETS,
    check_malformed_responses_are_rejected,
    check_well_formed_fenced_response_is_accepted,
)

# A fixed research fixture and a fixed set of example ad copy - not a live
# pipeline run. Grounded/ungrounded examples are mixed on purpose so the rates
# below are not just 0% or 100%.
_RESEARCH = {
    "company_name": "Acme",
    "competitors": [{"name": "Globex"}, {"name": "Initech"}],
    "summary": "Acme has grown to 50,000 users with a 4.8 rating.",
    "executive_summary": "Acme leads the category with 92% retention.",
    "site_content": "",
    "press_coverage": [{"title": "t", "url": "u", "snippet": "Acme raised $12M in seed funding."}],
}

_EXAMPLE_COPY = [
    "Acme helps your team ship faster than Globex ever could.",
    "Join the 50,000 users who already switched to Acme.",
    "The best solution for all your business needs.",
    "Transform your workflow today with cutting-edge technology.",
    "Trusted by 92% of teams who tried it, Acme just works.",
]


def _setup_chroma() -> None:
    import app.db.chroma as db

    settings.chroma_in_memory = True
    settings.chroma_disable_embeddings = True
    db.reset_client()


async def _run_conformance_section() -> None:
    print("SCHEMA CONFORMANCE - malformed model responses, per agent")
    print(f"  {'agent':<24}{'rejected':<10}{'accepted well-formed':<22}")

    for module_path, run_fn_name in AGENT_RUN_TARGETS:
        module = importlib.import_module(module_path)
        conformance = await check_malformed_responses_are_rejected(module, run_fn_name)

        from tests.test_schemas import ADS, AUDIENCE, CONTENT, PROFILE, SALES

        valid_payload = {
            "app.agents.agent_1_profile.node": PROFILE,
            "app.agents.agent_2_audience.node": AUDIENCE,
            "app.agents.agent_3_content.node": CONTENT,
            "app.agents.agent_4_sales.node": SALES,
            "app.agents.agent_5_ads.node": ADS,
        }[module_path]

        try:
            await check_well_formed_fenced_response_is_accepted(module, run_fn_name, valid_payload)
            accepted = "yes"
        except Exception as exc:  # noqa: BLE001
            accepted = f"NO ({type(exc).__name__})"

        agent_name = module_path.rsplit(".", 2)[-2]
        print(f"  {agent_name:<24}{conformance['rejection_rate']:<10.0%}{accepted:<22}")

        for scenario in conformance["scenarios"]:
            if not scenario["rejected"]:
                print(f"      FAILED: {scenario['scenario']} was not rejected (raised {scenario['raised']})")


def _run_grounding_section() -> None:
    print("\nGROUNDING - fixed example copy against a fixed research fixture")
    result = score_grounding(_EXAMPLE_COPY, _RESEARCH)
    print(f"  {result['count']} example items")
    print(f"  named_entity_rate:  {result['named_entity_rate']:.0%}  (mentions the company or a named competitor)")
    print(
        f"  source_number_rate: {result['source_number_rate']:.0%}  "
        "(reuses a number that is actually in the research)"
    )
    print("\n  This is not a random or representative sample - it is a fixed set of")
    print("  hand-written examples chosen to include both grounded and generic copy,")
    print("  so the rates above show the detector working, not a real batch's quality.")


async def main() -> None:
    _setup_chroma()
    await _run_conformance_section()
    _run_grounding_section()


if __name__ == "__main__":
    asyncio.run(main())
