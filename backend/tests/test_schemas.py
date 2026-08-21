"""Checks each agent's schema against the JSON shape its prompt asks for.

If someone renames a schema field without updating the prompt, the run dies
halfway through and the user loses everything. Better to fail here.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agents.agent_0_research.schemas import ResearchOutput
from app.agents.agent_1_profile.schemas import MarketingProfile
from app.agents.agent_2_audience.schemas import AudienceOutput
from app.agents.agent_3_content.schemas import ContentOutput
from app.agents.agent_4_sales.schemas import SalesOutput
from app.agents.agent_5_ads.schemas import AdsOutput

RESEARCH = {
    "company_name": "Acme", "company_url": "https://acme.com",
    "summary": "s", "executive_summary": "e",
    "press_coverage": [{"title": "t", "url": "u", "snippet": "s"}],
    "site_content": "content", "competitors": [{"name": "Globex"}],
    "aeo_score": 7.5, "aeo_details": [{"model": "openai/gpt-4o", "mentioned": True}],
}

PROFILE = {
    "brand_dna": {"mission": "m", "values": ["v"], "tone": "t",
                  "voice_example": "ve", "visual_style": "vs"},
    "positioning_statement": "p",
    "target_audiences": [{"segment": "s", "pain_points": ["p"], "decision_drivers": ["d"]}],
    "usps": ["u"],
    "competitive_edges": [{"competitor": "c", "advantage": "a", "vulnerability": "v"}],
    "messaging_pillars": ["m"],
    "marketing_gaps": [{"gap": "g", "evidence": "e", "recommendation": "r"}],
}

AUDIENCE = {
    "segments": [{
        "name": "n", "demographics": {}, "psychographics": {}, "pain_points": ["p"],
        "buying_triggers": ["b"], "active_channels": ["c"], "reasoning": "r",
        "fit_label": "High", "synthetic_attributes": {},
    }]
}

CONTENT = {
    "social_posts": [{"segment": "s", "platform": "LinkedIn", "post_copy": "c",
                      "hashtags": ["#a"], "cta": "cta"}],
    "email_campaigns": [{"segment": "s", "subject": "subj", "preview_text": "p",
                         "body": "b", "cta": "cta"}],
    "blog_outlines": [{"title": "t", "target_keyword": "k", "sections": ["s"],
                       "audience_segment": "a"}],
    "content_calendar": [{"timing": "Week 1", "channel": "LinkedIn",
                          "content_type": "post", "content_ref": "r", "segment": "s"}],
}

SALES = {
    "email_sequences": [{"segment": "s", "emails": [
        {"step": 1, "subject": "s", "body": "b", "delay_days": 0}]}],
    "linkedin_templates": [{"segment": "s", "connection_request": "c",
                            "follow_up_1": "f1", "follow_up_2": "f2"}],
    "lead_scoring": [{"tier": "Hot", "description": "d", "signals": ["s"], "action": "a"}],
    "pipeline_stages": [{"stage": "prospect", "definition": "d", "entry_criteria": "e",
                         "exit_criteria": "x", "actions": ["a"]}],
}

ADS = {
    "ad_copies": [{"segment": "s", "platform": "Google Ads", "headline": "h",
                   "body": "b", "cta": "c"}],
    "ad_visuals": [{"segment": "s", "platform": "Google Ads", "visual_concept": "v",
                    "color_palette": ["#fff"], "image_prompt": ""}],
    "ab_variations": [{"ad_copy_ref": "r", "variant_label": "A", "headline": "h",
                       "body": "b", "cta": "c", "test_hypothesis": "t", "image_prompt": ""}],
}

CASES = [
    ("research", ResearchOutput, RESEARCH),
    ("profile", MarketingProfile, PROFILE),
    ("audience", AudienceOutput, AUDIENCE),
    ("content", ContentOutput, CONTENT),
    ("sales", SalesOutput, SALES),
    ("ads", AdsOutput, ADS),
]


@pytest.mark.parametrize("name,model,payload", CASES, ids=[c[0] for c in CASES])
def test_schema_accepts_the_documented_shape(name, model, payload):
    assert model(**payload)


@pytest.mark.parametrize("name,model,payload", CASES, ids=[c[0] for c in CASES])
def test_schema_survives_a_round_trip(name, model, payload):
    """Nodes dump to a dict before saving, so that dict has to validate again."""
    assert model(**model(**payload).model_dump())


@pytest.mark.parametrize("name,model,payload", CASES, ids=[c[0] for c in CASES])
def test_schema_rejects_a_missing_required_field(name, model, payload):
    """A schema that accepts anything won't catch the model going off-script."""
    field = next(iter(payload))
    with pytest.raises(ValidationError):
        model(**{k: v for k, v in payload.items() if k != field})


def test_ad_images_default_to_absent():
    """Images are generated on click, so a fresh AdsOutput has none yet."""
    ads = AdsOutput(**ADS)

    assert ads.ad_visuals[0].image_url is None
    assert ads.ab_variations[0].image_url is None
