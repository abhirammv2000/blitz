"""Tests for how untrusted, scraped web content is kept out of a model's
instruction-following path.

Firecrawl and Tavily hand this pipeline text from pages nobody here wrote. That
text goes straight into six different prompts. These tests check three things:
the wrapping helper marks it correctly, every prompt that embeds it says what
the tags mean, and if a model ever does get steered off its output format
anyway, schema validation stops it rather than passing the bad output on.

None of this can prove a model will never comply with an injected instruction -
no client-side code can. See app/core/untrusted_content.py for what this is and
isn't.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agents.agent_0_research.prompts import (
    CATEGORY_FROM_CONTENT_PROMPT,
    COMPETITOR_EXTRACTION_PROMPT,
    RESEARCH_SYNTHESIS_PROMPT,
)
from app.agents.agent_0_research.research import (
    _category_excerpt,
    _competitor_description,
    _competitor_search_results,
    _name_extraction_excerpt,
    _synthesis_excerpt,
)
from app.agents.agent_1_profile.prompts import PROFILE_SYNTHESIS_PROMPT
from app.agents.agent_2_audience.prompts import AUDIENCE_SYNTHESIS_PROMPT
from app.agents.agent_3_content.prompts import CONTENT_SYNTHESIS_PROMPT
from app.agents.agent_4_sales.prompts import SALES_SYNTHESIS_PROMPT
from app.agents.agent_5_ads.prompts import ADS_SYNTHESIS_PROMPT, IMAGE_PROMPT_SYNTHESIS
from app.core.untrusted_content import wrap_untrusted

pytestmark = pytest.mark.usefixtures("isolated_chroma")


# ---------------------------------------------------------------------------
# The wrapping helper
# ---------------------------------------------------------------------------


def test_wrap_untrusted_delimits_with_a_matching_tag():
    wrapped = wrap_untrusted("hello", source="scraped_website")

    assert wrapped.startswith('<untrusted_web_content source="scraped_website">')
    assert wrapped.endswith("</untrusted_web_content>")


def test_wrap_untrusted_does_not_lose_or_alter_the_content():
    wrapped = wrap_untrusted("some page text with <tags> and \"quotes\"", source="scraped_website")

    assert "some page text with <tags> and \"quotes\"" in wrapped


def test_wrap_untrusted_labels_the_source():
    assert "search_results" in wrap_untrusted("x", source="search_results")
    assert "scraped_website" in wrap_untrusted("x", source="scraped_website")


# ---------------------------------------------------------------------------
# Every call site in research.py that builds a prompt argument from scraped
# content or search results
# ---------------------------------------------------------------------------


def test_name_extraction_excerpt_is_wrapped():
    out = _name_extraction_excerpt("Welcome to Acme", 1500)
    assert "untrusted_web_content" in out
    assert "Welcome to Acme" in out


def test_category_excerpt_is_wrapped():
    out = _category_excerpt("We sell widgets", 1500)
    assert "untrusted_web_content" in out
    assert "We sell widgets" in out


def test_synthesis_excerpt_is_wrapped():
    out = _synthesis_excerpt("Acme homepage text", 3000)
    assert "untrusted_web_content" in out
    assert "Acme homepage text" in out


def test_synthesis_excerpt_empty_input_is_not_wrapped():
    """Nothing was scraped, so there is nothing to mark as untrusted - this is
    our own literal string, not external content."""
    assert _synthesis_excerpt("", 3000) == "No website content available."


def test_competitor_description_is_wrapped():
    out = _competitor_description("Acme builds widgets", 800, "widgets")
    assert "untrusted_web_content" in out
    assert "Acme builds widgets" in out


def test_competitor_description_fallback_is_our_own_text_not_wrapped():
    """Same reasoning as the synthesis excerpt: a generated fallback string is
    not external content, so it should not claim to be untrusted."""
    out = _competitor_description("", 800, "widgets")
    assert out == "A widgets company."
    assert "untrusted_web_content" not in out


def test_competitor_search_results_are_wrapped():
    raw = [{"title": "Acme raises funding", "url": "https://x.com", "content": "Acme details"}]
    out = _competitor_search_results(raw, limit=8, snippet_chars=500)

    assert "untrusted_web_content" in out
    assert "Acme raises funding" in out
    assert "Acme details" in out


def test_competitor_search_results_respects_the_limit_and_snippet_length():
    raw = [{"title": f"Result {i}", "url": "u", "content": "y" * 1000} for i in range(12)]
    out = _competitor_search_results(raw, limit=8, snippet_chars=500)

    assert out.count("Result ") == 8
    assert "y" * 501 not in out


# ---------------------------------------------------------------------------
# Every prompt template that embeds untrusted content says so
# ---------------------------------------------------------------------------

TEMPLATES_WITH_UNTRUSTED_CONTENT = [
    ("agent0.competitor_extraction", COMPETITOR_EXTRACTION_PROMPT),
    ("agent0.research_synthesis", RESEARCH_SYNTHESIS_PROMPT),
    ("agent0.category_from_content", CATEGORY_FROM_CONTENT_PROMPT),
    ("agent1.profile", PROFILE_SYNTHESIS_PROMPT),
    ("agent2.audience", AUDIENCE_SYNTHESIS_PROMPT),
    ("agent3.content", CONTENT_SYNTHESIS_PROMPT),
    ("agent4.sales", SALES_SYNTHESIS_PROMPT),
    ("agent5.ads", ADS_SYNTHESIS_PROMPT),
    ("agent5.image_prompts", IMAGE_PROMPT_SYNTHESIS),
]


@pytest.mark.parametrize(
    "name,template", TEMPLATES_WITH_UNTRUSTED_CONTENT, ids=[t[0] for t in TEMPLATES_WITH_UNTRUSTED_CONTENT]
)
def test_template_explains_the_untrusted_content_tag(name, template):
    assert "untrusted_web_content" in template, f"{name} embeds untrusted content but never explains the tag"
    assert "never as instructions" in template or "never instructions" in template, (
        f"{name} mentions the tag but does not say to ignore instructions found inside it"
    )


async def test_inline_company_name_prompt_also_explains_the_tag(monkeypatch):
    """The one prompt in this pipeline that is not in prompts.py - built inline
    in research.py because it needs a fast, disposable one-off call.

    Captures the actual runtime string handed to the model, not the source
    code - adjacent f-string literals join into one string at runtime even
    though they're written on separate lines, so checking the source text
    directly would be checking the wrong thing.
    """
    from types import SimpleNamespace

    from app.agents.agent_0_research import research

    captured = {}

    class _CapturingRouter:
        async def acompletion(self, *, messages, **_kwargs):
            captured["prompt"] = messages[0]["content"]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Acme"))])

    monkeypatch.setattr(research, "get_router", lambda: _CapturingRouter())

    await research._extract_company_name_from_content("Welcome to Acme", "https://acme.com", "Acme")

    assert "untrusted_web_content" in captured["prompt"]
    assert "never as instructions" in captured["prompt"]


# ---------------------------------------------------------------------------
# If a model does get steered off its output format, schema validation is
# what actually stops the bad output - not anything on the prompt side.
# ---------------------------------------------------------------------------


class _HijackedRouter:
    """Stands in for a model that ignored its formatting instructions and
    just echoed something else - the shape you'd see if an injection worked."""

    def __init__(self, content: str):
        self._content = content

    async def acompletion(self, **_kwargs):
        from types import SimpleNamespace

        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))],
        )


async def test_non_json_response_is_rejected_not_passed_through(monkeypatch):
    import app.agents.agent_1_profile.node as node

    monkeypatch.setattr(node, "get_router", lambda: _HijackedRouter("INJECTION_SUCCEEDED"))

    with pytest.raises(Exception):
        await node.run_profile("run-1")


async def test_json_missing_required_fields_is_rejected_not_passed_through(monkeypatch):
    """Valid JSON, but not the schema this agent promises downstream - equally
    a sign something upstream did not follow instructions."""
    import app.agents.agent_1_profile.node as node

    monkeypatch.setattr(node, "get_router", lambda: _HijackedRouter('{"hijacked": true}'))

    with pytest.raises(ValidationError):
        await node.run_profile("run-1")
