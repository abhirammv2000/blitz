"""Pydantic output schema for Agent 4 (Sales Enablement).

Nested models follow the BrandDNA/MarketingGap pattern from agent_1_profile —
no loose dict types, enabling reliable frontend rendering and type-safe access.
"""

from pydantic import BaseModel


class EmailStep(BaseModel):
    """A single step in a multi-touch email outreach sequence."""

    step: int  # 1=Insight, 2=Value, 3=Ask
    subject: str
    body: str
    delay_days: int  # Days since previous step (0 for step 1)


class EmailSequence(BaseModel):
    """A 3-email consultative outreach sequence for a specific audience segment."""

    segment: str
    emails: list[EmailStep]  # Exactly 3: Insight -> Value -> Ask


class LinkedInTemplate(BaseModel):
    """LinkedIn DM templates for a specific audience segment."""

    segment: str
    connection_request: str  # Short, casual — under 300 chars
    follow_up_1: str         # Provides value, references connection
    follow_up_2: str         # Soft ask or resource share


class LeadScoringTier(BaseModel):
    """A Hot/Warm/Cold lead scoring tier with behavioral signals and recommended action."""

    tier: str        # "Hot" | "Warm" | "Cold"
    description: str
    signals: list[str]
    action: str


class PipelineStage(BaseModel):
    """A stage in the sales pipeline with entry/exit criteria and recommended actions."""

    stage: str           # prospect | contacted | engaged | converted
    definition: str
    entry_criteria: str
    exit_criteria: str
    actions: list[str]


class SalesOutput(BaseModel):
    """Structured output from the Sales Enablement agent.

    Produces multi-touch outreach sequences, LinkedIn templates, lead scoring
    criteria, and pipeline stage definitions — all segment-targeted and
    typed with nested Pydantic models for reliable frontend rendering.
    """

    email_sequences: list[EmailSequence]
    linkedin_templates: list[LinkedInTemplate]
    lead_scoring: list[LeadScoringTier]    # Hot, Warm, Cold tiers
    pipeline_stages: list[PipelineStage]   # prospect -> contacted -> engaged -> converted
