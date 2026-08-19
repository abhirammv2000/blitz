"""Tests for the prompt-facing context trimming in db.get_agent_context.

Background: the research output embeds the raw scraped page markdown, which
measured ~32k chars — 80% of the blob. Every downstream agent puts the whole
research JSON in its prompt, so the page was sent to the model five times per
run, about 37k wasted tokens. get_agent_context trims that for prompt use while
leaving the stored artifact whole.

Both halves matter: trimming too little wastes money, trimming the wrong field
silently degrades output quality.
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
    """The trim is for prompts only — the stored artifact must not lose data."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))

    get_agent_context("run1", "research_decision")
    stored = json.loads(get_agent_output("run1", "research_decision"))

    assert stored["site_content"] == research_payload["site_content"]


def test_every_other_field_survives_untouched(research_payload):
    """The grounding lives in these fields. Trimming must not disturb them."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))

    trimmed = json.loads(get_agent_context("run1", "research_decision"))

    assert set(trimmed) == set(research_payload)
    for field in research_payload:
        if field == "site_content":
            continue
        assert trimmed[field] == research_payload[field], f"{field} was altered"


def test_short_field_is_returned_byte_identical(research_payload):
    """No rewrite when nothing exceeds the limit — avoids needless churn."""
    research_payload["site_content"] = "short enough"
    raw = json.dumps(research_payload)
    store_agent_output("run1", "research_decision", raw)

    assert get_agent_context("run1", "research_decision") == raw


def test_missing_run_returns_none():
    assert get_agent_context("no-such-run", "research_decision") is None


def test_non_json_document_passes_through_unchanged():
    """Not every stored document is a JSON object; those must survive as-is."""
    store_agent_output("run1", "notes", "plain text, not json")

    assert get_agent_context("run1", "notes") == "plain text, not json"


def test_json_scalar_document_passes_through_unchanged():
    store_agent_output("run1", "count", "42")

    assert get_agent_context("run1", "count") == "42"


def test_runs_are_isolated_from_each_other(research_payload):
    """Multi-tenancy depends on this: one run must never read another's data."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))
    other = dict(research_payload, company_name="Globex")
    store_agent_output("run2", "research_decision", json.dumps(other))

    got1 = json.loads(get_agent_context("run1", "research_decision"))
    got2 = json.loads(get_agent_context("run2", "research_decision"))

    assert got1["company_name"] == "Acme"
    assert got2["company_name"] == "Globex"


def test_trimming_actually_saves_a_worthwhile_amount(research_payload):
    """Guards the point of the change: a 40k-char field must shrink a lot."""
    store_agent_output("run1", "research_decision", json.dumps(research_payload))

    full = get_agent_output("run1", "research_decision")
    trimmed = get_agent_context("run1", "research_decision")

    assert len(trimmed) < len(full) * 0.5
