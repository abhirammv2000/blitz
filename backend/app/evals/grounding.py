"""Checks whether generated copy actually references the research it was
given, rather than being generic boilerplate that could describe any company
in the category.

Two separate, narrower checks rather than one fuzzy "grounded" score - a
single blurry number hides which kind of grounding is missing:

- named_entity_rate: does the copy mention the company or a real competitor?
- source_number_rate: does it reuse a number that actually appears in the
  research, rather than a plausible-looking invented one?

Reusing a specific number is a much stronger signal than "the copy contains
some number" - a hallucinated stat would pass that weaker check too.
"""

from __future__ import annotations

import re

# Numbers are pulled from these fields specifically, not the whole research
# dict. aeo_score and aeo_details carry structural numbers (scores, ranks)
# that a marketer would never cite verbatim - counting those as "sources"
# would make the check too easy to pass.
_NUMBER_SOURCE_FIELDS = ("summary", "executive_summary", "site_content")

_NUMBER_RE = re.compile(r"\d[\d,.]*%?")


def extract_entities(research: dict) -> set[str]:
    """Company name and competitor names from a ResearchOutput-shaped dict."""
    entities: set[str] = set()
    name = research.get("company_name")
    if name:
        entities.add(name.lower())
    for c in research.get("competitors") or []:
        cname = c.get("name") if isinstance(c, dict) else None
        if cname:
            entities.add(cname.lower())
    return entities


def extract_source_numbers(research: dict) -> set[str]:
    """Numeric tokens that actually appear in the research's narrative text."""
    numbers: set[str] = set()
    for field in _NUMBER_SOURCE_FIELDS:
        text = research.get(field)
        if isinstance(text, str):
            numbers.update(_NUMBER_RE.findall(text))
    for item in research.get("press_coverage") or []:
        snippet = item.get("snippet") if isinstance(item, dict) else None
        if isinstance(snippet, str):
            numbers.update(_NUMBER_RE.findall(snippet))
    return numbers


def mentions_named_entity(text: str, entities: set[str]) -> bool:
    lowered = text.lower()
    return any(e in lowered for e in entities)


def mentions_source_number(text: str, source_numbers: set[str]) -> bool:
    return any(n in text for n in source_numbers)


def score_grounding(items: list[str], research: dict) -> dict:
    """Rate a batch of generated text against one research dossier.

    `items` is generated copy - ad bodies, email subjects, whatever unit is
    being scored, combined into one string per item by the caller. Returns
    rates rather than a single pass/fail: evals are a distribution, and a
    flat 0%/100% score hides whether ten items or one thousand produced it.
    """
    if not items:
        return {"count": 0, "named_entity_rate": 0.0, "source_number_rate": 0.0}

    entities = extract_entities(research)
    numbers = extract_source_numbers(research)
    named = sum(1 for t in items if mentions_named_entity(t, entities))
    numbered = sum(1 for t in items if mentions_source_number(t, numbers))

    return {
        "count": len(items),
        "named_entity_rate": named / len(items),
        "source_number_rate": numbered / len(items),
    }
