"""Tests for get_agent_context, which trims big fields before they hit a prompt.

The research output carries the whole scraped page, and every later agent pastes
that JSON into its prompt. Trimming it saves a lot of tokens, but trimming the
wrong field would quietly make the output worse, so both sides are checked.
"""

from __future__ import annotations

import json

import pytest

from app.db import get_agent_context, get_agent_output, store_agent_output
from app.db.chroma import _PROMPT_TRIMMED_FIELDS

pytestmark = pytest.mark.usefixtures("isolated_chroma")

LIMIT = _PROMPT_TRIMMED_FIELDS["site_content"]


def test_oversized_field_is_trimmed(research_payload):
    store_agent_output("run1", "research_decision", json.dumps(research_payload))

    trimmed = json.loads(get_agent_context("run1", "research_decision"))

    assert len(trimmed["site_content"]) < len(research_payload["site_content"])
    assert trimmed["site_content"].startswith("x" * 100)
    assert "truncated" in trimmed["site_content"]


def test_stored_copy_is_left_intact(research_payload):
    """We only trim the copy going into a prompt, not what's saved."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))

    get_agent_context("run1", "research_decision")
    stored = json.loads(get_agent_output("run1", "research_decision"))

    assert stored["site_content"] == research_payload["site_content"]


def test_every_other_field_survives_untouched(research_payload):
    """These fields are what the later agents actually read, so leave them be."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))

    trimmed = json.loads(get_agent_context("run1", "research_decision"))

    assert set(trimmed) == set(research_payload)
    for field in research_payload:
        if field == "site_content":
            continue
        assert trimmed[field] == research_payload[field], f"{field} was altered"


def test_short_field_is_returned_byte_identical(research_payload):
    """Nothing over the limit means nothing to rewrite."""
    research_payload["site_content"] = "short enough"
    raw = json.dumps(research_payload)
    store_agent_output("run1", "research_decision", raw)

    assert get_agent_context("run1", "research_decision") == raw


def test_missing_run_returns_none():
    assert get_agent_context("no-such-run", "research_decision") is None


def test_non_json_document_passes_through_unchanged():
    """Not everything we store is JSON, so leave the rest alone."""
    store_agent_output("run1", "notes", "plain text, not json")

    assert get_agent_context("run1", "notes") == "plain text, not json"


def test_json_scalar_document_passes_through_unchanged():
    store_agent_output("run1", "count", "42")

    assert get_agent_context("run1", "count") == "42"


def test_runs_are_isolated_from_each_other(research_payload):
    """One run should never see another run's data."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))
    other = dict(research_payload, company_name="Globex")
    store_agent_output("run2", "research_decision", json.dumps(other))

    got1 = json.loads(get_agent_context("run1", "research_decision"))
    got2 = json.loads(get_agent_context("run2", "research_decision"))

    assert got1["company_name"] == "Acme"
    assert got2["company_name"] == "Globex"


def test_trimming_actually_saves_a_worthwhile_amount(research_payload):
    """A 40k-character field should come back a lot smaller than it went in."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))

    full = get_agent_output("run1", "research_decision")
    trimmed = get_agent_context("run1", "research_decision")

    assert len(trimmed) < len(full) * 0.5
