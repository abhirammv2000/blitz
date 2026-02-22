"""BlitzState TypedDict — single source of truth for the Blitz pipeline state.

Every LangGraph node reads from and writes to this TypedDict. Using TypedDict
(not Pydantic BaseModel) is intentional — LangGraph's state management is built
around TypedDict semantics for partial updates and checkpointing.

total=False means all keys are optional by default, which matches LangGraph's
pattern of each node only populating the keys it produces.
"""

from typing import Optional

from typing_extensions import TypedDict

from agents.agent_0_research.schemas import ResearchOutput
from agents.agent_1_profile.schemas import MarketingProfile
from agents.agent_2_audience.schemas import AudienceOutput
from agents.agent_3_content.schemas import ContentOutput
from agents.agent_4_sales.schemas import SalesOutput
from agents.agent_5_ads.schemas import AdsOutput


class BlitzState(TypedDict, total=False):
    """Pipeline state passed between all LangGraph nodes.

    Fields:
        run_id: Unique identifier for this pipeline run (UUID4). Used to scope
            ChromaDB storage and SQLite checkpoint data.
        company_url: The target company URL entered by the user — the pipeline's
            only required input.
        current_step: Zero-based index of the current active agent (0–5).
        research_output: Output from Agent 0 — company intelligence and AEO scores.
        profile_output: Output from Agent 1 — brand DNA and positioning.
        audience_output: Output from Agent 2 — synthetic audience segments.
        content_output: Output from Agent 3 — social, email, blog, and calendar assets.
        sales_output: Output from Agent 4 — outreach sequences and pipeline stages.
        ads_output: Output from Agent 5 — ad copy, visuals, and A/B variants.
        human_feedback: Free-text feedback from the user at a HITL review checkpoint.
            None means no feedback submitted; empty string means approved with no notes.
        approved: Whether the current HITL checkpoint was approved. False = revise.
    """

    run_id: str
    company_url: str
    current_step: int
    research_output: Optional[ResearchOutput]
    profile_output: Optional[MarketingProfile]
    audience_output: Optional[AudienceOutput]
    content_output: Optional[ContentOutput]
    sales_output: Optional[SalesOutput]
    ads_output: Optional[AdsOutput]
    human_feedback: Optional[str]
    approved: bool
