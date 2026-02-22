"""Pydantic output schema for Agent 4 (Sales Enablement)."""

from pydantic import BaseModel


class SalesOutput(BaseModel):
    """Structured output from the Sales Enablement agent.

    Produces multi-touch outreach sequences, LinkedIn templates, lead scoring
    criteria, and pipeline stage definitions — all segment-targeted.
    """

    email_sequences: list[dict]  # [{segment, step, subject, body, delay_days}]
    linkedin_templates: list[dict]  # [{segment, connection_request, follow_up_1, follow_up_2}]
    lead_scoring: dict  # {criteria: [{signal, points}], tiers: [{name, score_range, action}]}
    pipeline_stages: list[dict]  # [{stage, definition, entry_criteria, exit_criteria, actions}]
