"""Pydantic output schema for Agent 3 (Content Strategy)."""

from pydantic import BaseModel


class ContentOutput(BaseModel):
    """Structured output from the Content Strategy agent.

    Produces platform-specific content assets and a 30-day content calendar.
    Each item in social_posts, email_campaigns, and blog_outlines is a dict
    with segment-targeted content ready for human review or export.
    """

    social_posts: list[dict]  # [{segment, platform, copy, hashtags, cta}]
    email_campaigns: list[dict]  # [{segment, subject, preview_text, body, cta}]
    blog_outlines: list[dict]  # [{title, target_keyword, sections, audience_segment}]
    content_calendar: list[dict]  # [{date, channel, content_type, content_ref, segment}]
