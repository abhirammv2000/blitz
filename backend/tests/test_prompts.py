"""Every prompt template must survive .format() with its real placeholders.

This exists because of a bug that broke the whole pipeline: the ads critic
prompt embedded a literal JSON example, `{"approved": true, ...}`, and str.format
read those braces as a replacement field. Every run died at the last node with
KeyError: '"approved"'.

That failure mode is invisible on inspection and catastrophic at runtime, and it
will recur the moment someone pastes a JSON example into a prompt. These tests
make it impossible to merge.
"""

from __future__ import annotations

import string

import pytest

from agents.agent_0_research.prompts import (
    AEO_CATEGORY_PROMPT,
    CATEGORY_FROM_CONTENT_PROMPT,
    COMPETITOR_EXTRACTION_PROMPT,
    RESEARCH_SYNTHESIS_PROMPT,
)
from agents.agent_1_profile.prompts import PROFILE_SYNTHESIS_PROMPT
from agents.agent_2_audience.prompts import AUDIENCE_SYNTHESIS_PROMPT
from agents.agent_3_content.prompts import CONTENT_SYNTHESIS_PROMPT
from agents.agent_4_sales.prompts import SALES_SYNTHESIS_PROMPT
from agents.agent_5_ads.critic import CRITIC_PROMPT
from agents.agent_5_ads.prompts import ADS_SYNTHESIS_PROMPT, IMAGE_PROMPT_SYNTHESIS

# (template, the exact kwargs the production call site passes)
TEMPLATES = [
    ("agent0.research_synthesis", RESEARCH_SYNTHESIS_PROMPT, {
        "company_name": "Acme", "company_url": "https://acme.com", "site_excerpt": "...",
        "press_summary": "...", "competitor_summary": "...", "aeo_score": "7.5", "aeo_summary": "...",
    }),
    ("agent0.competitor_extraction", COMPETITOR_EXTRACTION_PROMPT, {
        "raw_results": "...", "company_name": "Acme", "category": "widgets", "company_description": "...",
    }),
    ("agent0.aeo_category", AEO_CATEGORY_PROMPT, {"company_name": "Acme", "domain": "acme.com"}),
    ("agent0.category_from_content", CATEGORY_FROM_CONTENT_PROMPT, {
        "company_name": "Acme", "site_excerpt": "...",
    }),
    ("agent1.profile", PROFILE_SYNTHESIS_PROMPT, {"research_data": "{}", "feedback": ""}),
    ("agent2.audience", AUDIENCE_SYNTHESIS_PROMPT, {
        "profile_data": "{}", "research_data": "{}", "feedback": "",
    }),
    ("agent3.content", CONTENT_SYNTHESIS_PROMPT, {
        "research_data": "{}", "profile_data": "{}", "audience_data": "{}", "feedback": "",
    }),
    ("agent4.sales", SALES_SYNTHESIS_PROMPT, {
        "research_data": "{}", "profile_data": "{}", "audience_data": "{}", "feedback": "",
    }),
    ("agent5.ads", ADS_SYNTHESIS_PROMPT, {
        "research_data": "{}", "profile_data": "{}", "audience_data": "{}", "feedback": "",
    }),
    ("agent5.image_prompts", IMAGE_PROMPT_SYNTHESIS, {
        "research_data": "{}", "ads_json": "[]", "style_directive": "...",
    }),
    ("agent5.critic", CRITIC_PROMPT, {"ads_json": "{}"}),
]


@pytest.mark.parametrize("name,template,kwargs", TEMPLATES, ids=[t[0] for t in TEMPLATES])
def test_template_formats_without_error(name, template, kwargs):
    """The regression guard: .format() must not raise on any prompt."""
    result = template.format(**kwargs)
    assert result, f"{name} formatted to an empty string"


@pytest.mark.parametrize("name,template,kwargs", TEMPLATES, ids=[t[0] for t in TEMPLATES])
def test_template_declares_exactly_the_expected_fields(name, template, kwargs):
    """Catch drift in both directions.

    A placeholder added to a template without updating its call site raises
    KeyError in production; one removed leaves dead arguments behind. Either way
    the template's fields and the call site's kwargs should agree exactly.
    """
    declared = {
        field
        for _, field, _, _ in string.Formatter().parse(template)
        if field is not None and field != ""
    }
    assert declared == set(kwargs), (
        f"{name}: template fields {sorted(declared)} != call-site kwargs {sorted(kwargs)}"
    )


def test_critic_prompt_keeps_its_json_example_literal():
    """The specific bug, pinned.

    The critic prompt shows the model an example of the JSON it should return.
    Those braces must be escaped so they survive .format() as literal text — if
    they reach the model mangled, or blow up formatting, the critic is useless.
    """
    rendered = CRITIC_PROMPT.format(ads_json='{"ad_copies": []}')
    assert '{"approved": true' in rendered
    assert '{"approved": false' in rendered
    assert '{"ad_copies": []}' in rendered
