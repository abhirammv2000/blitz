"""Offline eval suite: scores pipeline output against a fixed set of scenarios.

Two things live here. grounding.py checks whether generated copy actually
references the research it was given, instead of being generic boilerplate
that could describe any company in the category. schema_conformance.py checks
that a malformed model response gets rejected instead of silently passed on -
the thing schema validation is supposed to guarantee, now pinned with an
actual scenario set instead of assumed.

Both are code-based checks, not an LLM judge - deterministic, free to run, and
they never disagree with themselves. See backend/run_evals.py to run the full
set and get a report instead of pytest's plain pass/fail.
"""
