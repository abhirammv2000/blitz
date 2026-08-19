"""Tests for the pure helpers in agent 0.

These run on every pipeline and shape the company identity that all five
downstream agents inherit. If the domain parser is wrong, every agent is wrong.
"""

from __future__ import annotations

import pytest

from agents.agent_0_research.research import _extract_bare_domain, _extract_company_name


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://acme.com", "acme.com"),
        ("http://acme.com", "acme.com"),
        ("https://www.acme.com", "acme.com"),
        ("https://www.acme.com/about", "acme.com"),
        ("https://acme.com/a/b?c=d", "acme.com"),
        ("acme.com", "acme.com"),
        ("https://sub.acme.co.uk/path", "sub.acme.co.uk"),
    ],
)
def test_bare_domain_strips_scheme_www_and_path(url, expected):
    assert _extract_bare_domain(url) == expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://acme.com", "Acme"),
        ("https://www.linear.app", "Linear"),
        ("https://figma.com/", "Figma"),
        ("https://stripe.io", "Stripe"),
    ],
)
def test_company_name_drops_the_tld_and_capitalises(url, expected):
    assert _extract_company_name(url) == expected


def test_company_name_is_only_a_fallback_for_vanity_domains():
    """Documents a known limitation rather than asserting ideal behaviour.

    The regex cannot know that joinblossomhealth.com is "Blossom Health"; an LLM
    call refines it from page content later. This pins what the fallback returns
    so a change to that path is a deliberate decision, not an accident.
    """
    assert _extract_company_name("https://joinblossomhealth.com") == "Joinblossomhealth"


def test_domain_parsing_does_not_crash_on_junk_input():
    """The API accepts any string as a URL, so this must degrade, not raise."""
    for junk in ["not-a-url-at-all", "", "https://", "://///"]:
        _extract_bare_domain(junk)
        _extract_company_name(junk)
