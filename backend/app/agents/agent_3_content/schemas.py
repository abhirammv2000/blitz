"""Pydantic output schema for Agent 3 (Content Strategy).

Nested models follow the BrandDNA/MarketingGap pattern from agent_1_profile —
no loose dict types, enabling reliable frontend rendering and type-safe access.
"""

from pydantic import BaseModel


class SocialPost(BaseModel):
    """A single platform-optimized social post for a named audience segment."""

    segment: str
    platform: str  # "LinkedIn" | "Twitter" | "Instagram"
    post_copy: str
    hashtags: list[str]
    cta: str


class EmailCampaign(BaseModel):
    """A marketing email campaign targeted at a specific audience segment."""

    segment: str
    subject: str
    preview_text: str
    body: str  # Max 200 words, draft quality
    cta: str


class BlogOutline(BaseModel):
    """A blog post outline optimized for a keyword and audience segment."""

    title: str
    target_keyword: str
    sections: list[str]  # Max 5 section headings
    audience_segment: str


class CalendarEntry(BaseModel):
    """A single entry in the 30-day content calendar with relative timing."""

    timing: str  # e.g. "Week 1 - Monday"
    channel: str
    content_type: str
    content_ref: str  # References a title/subject/copy from above outputs
    segment: str


class ContentOutput(BaseModel):
    """Structured output from the Content Strategy agent.

    Produces platform-specific content assets and a 30-day content calendar.
    All items are nested Pydantic models — no loose dicts — for reliable
    frontend rendering and downstream agent consumption.
    """

    social_posts: list[SocialPost]
    email_campaigns: list[EmailCampaign]
    blog_outlines: list[BlogOutline]
    content_calendar: list[CalendarEntry]
