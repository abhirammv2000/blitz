"""Tests for the eval suite itself - the scorers in app/evals/.

These check that the scorers actually discriminate: a grounding check that
scores everything as grounded, or a conformance check that never rejects
anything, would pass its own tests while being useless. Each scorer gets both
a case it should accept and one it should reject.
"""

from __future__ import annotations

import importlib

import pytest

from app.evals.grounding import (
    extract_entities,
    extract_source_numbers,
    mentions_named_entity,
    mentions_source_number,
    score_grounding,
)
from app.evals.schema_conformance import (
    AGENT_RUN_TARGETS,
    MALFORMED_RESPONSES,
    check_malformed_responses_are_rejected,
    check_well_formed_fenced_response_is_accepted,
)
from tests.test_schemas import ADS, AUDIENCE, CONTENT, PROFILE, SALES

pytestmark = pytest.mark.usefixtures("isolated_chroma")

RESEARCH = {
    "company_name": "Acme",
    "competitors": [{"name": "Globex"}, {"name": "Initech"}],
    "summary": "Acme has grown to 50,000 users and a 4.8 rating.",
    "executive_summary": "Acme leads with 92% retention.",
    "site_content": "",
    "press_coverage": [{"title": "t", "url": "u", "snippet": "Acme raised $12M in funding."}],
}

# One valid payload per agent, matched to AGENT_RUN_TARGETS by module path.
_VALID_PAYLOADS = {
    "app.agents.agent_1_profile.node": PROFILE,
    "app.agents.agent_2_audience.node": AUDIENCE,
    "app.agents.agent_3_content.node": CONTENT,
    "app.agents.agent_4_sales.node": SALES,
    "app.agents.agent_5_ads.node": ADS,
}


# ---------------------------------------------------------------------------
# grounding.py
# ---------------------------------------------------------------------------


def test_extract_entities_gets_company_and_competitors():
    entities = extract_entities(RESEARCH)
    assert entities == {"acme", "globex", "initech"}


def test_extract_source_numbers_pulls_from_narrative_fields():
    numbers = extract_source_numbers(RESEARCH)
    assert "50,000" in numbers
    assert "92%" in numbers
    assert "12" in numbers  # from the press snippet, "$12M"


def test_extract_source_numbers_does_not_look_at_structural_fields():
    """aeo_score and aeo_details are not in the source fields on purpose -
    a marketer would never cite an internal visibility score as a stat."""
    research = dict(RESEARCH, aeo_score=7.5, aeo_details=[{"position": 1}])
    numbers = extract_source_numbers(research)
    assert "7.5" not in numbers


def test_mentions_named_entity_is_case_insensitive():
    assert mentions_named_entity("Try ACME today", {"acme"}) is True
    assert mentions_named_entity("Try SomethingElse today", {"acme"}) is False


def test_mentions_source_number_requires_the_exact_source_token():
    """A different, made-up number does not count - reusing an invented stat
    is exactly the failure mode this check exists to catch."""
    assert mentions_source_number("Trusted by 50,000 teams", {"50,000"}) is True
    assert mentions_source_number("Trusted by 8,000,000 teams", {"50,000"}) is False


def test_score_grounding_discriminates_grounded_from_generic_copy():
    items = [
        "Acme helps teams move faster than Globex.",  # named entity
        "Join 50,000 users who switched.",  # source number
        "The best solution for your business needs.",  # neither - pure boilerplate
    ]
    result = score_grounding(items, RESEARCH)

    assert result["count"] == 3
    assert result["named_entity_rate"] == pytest.approx(1 / 3)
    assert result["source_number_rate"] == pytest.approx(1 / 3)


def test_score_grounding_on_an_empty_batch_is_zero_not_a_crash():
    assert score_grounding([], RESEARCH) == {"count": 0, "named_entity_rate": 0.0, "source_number_rate": 0.0}


def test_score_grounding_all_generic_scores_zero():
    """The all-boilerplate case has to score 0%, not some nonzero floor -
    otherwise the metric can't tell a bad batch from a good one."""
    items = ["The best solution for your business.", "Transform your workflow today."]
    result = score_grounding(items, RESEARCH)

    assert result["named_entity_rate"] == 0.0
    assert result["source_number_rate"] == 0.0


# ---------------------------------------------------------------------------
# schema_conformance.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_path,run_fn_name", AGENT_RUN_TARGETS, ids=[p for p, _ in AGENT_RUN_TARGETS])
async def test_every_malformed_response_is_rejected(module_path, run_fn_name):
    module = importlib.import_module(module_path)

    result = await check_malformed_responses_are_rejected(module, run_fn_name)

    failures = [r for r in result["scenarios"] if not r["rejected"]]
    assert not failures, f"{module_path} accepted malformed input instead of rejecting it: {failures}"
    assert result["rejection_rate"] == 1.0
    assert len(result["scenarios"]) == len(MALFORMED_RESPONSES)


@pytest.mark.parametrize("module_path,run_fn_name", AGENT_RUN_TARGETS, ids=[p for p, _ in AGENT_RUN_TARGETS])
async def test_well_formed_fenced_response_is_accepted(module_path, run_fn_name):
    """The positive case, so this eval is proven to discriminate rather than
    just reject everything it's shown."""
    module = importlib.import_module(module_path)
    valid_payload = _VALID_PAYLOADS[module_path]

    output = await check_well_formed_fenced_response_is_accepted(module, run_fn_name, valid_payload)

    assert output is not None
