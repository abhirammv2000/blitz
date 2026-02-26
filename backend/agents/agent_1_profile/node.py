"""LangGraph node function for Agent 1 (Marketing Profile).

Reads research dossier from ChromaDB, synthesizes a marketing profile via GPT-4o,
and stores the result for downstream agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import litellm

from agents.agent_1_profile.prompts import PROFILE_SYNTHESIS_PROMPT
from agents.agent_1_profile.schemas import MarketingProfile
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_profile(run_id: str, feedback: str | None = None) -> MarketingProfile:
    """Run the profile synthesis LLM call for a given run_id.

    Args:
        run_id: Pipeline run identifier — used to fetch research from ChromaDB.
        feedback: Optional feedback to guide refinement.

    Returns:
        MarketingProfile with brand_dna, positioning_statement, usps, marketing_gaps.
    """
    research_raw = get_agent_output(run_id, "research_decision")
    if research_raw is None:
        logger.warning("Agent 1: no research_decision found in ChromaDB for run_id=%s", run_id)
        research_data = "{}"
    else:
        research_data = research_raw

    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised profile."
        if feedback
        else ""
    )

    prompt = PROFILE_SYNTHESIS_PROMPT.format(
        research_data=research_data,
        feedback=feedback_instruction,
    )

    response = await asyncio.wait_for(
        litellm.acompletion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            temperature=0.3,
        ),
        timeout=30.0,
    )

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return MarketingProfile(**data)


async def agent_1_profile_node(state: BlitzState) -> dict:
    """Marketing Profile Creator node: synthesizes brand DNA and positioning.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step and profile_output.
    """
    run_id: str = state.get("run_id", "")

    output = await run_profile(run_id)

    store_agent_output(run_id, "profile", json.dumps(output.model_dump()))

    return {
        "current_step": 1,
        "profile_output": output.model_dump(),
    }
