"""LangGraph node function for Agent 2 (Audience Intelligence).

Reads Agent 1's marketing profile from ChromaDB, generates audience segments
via GPT-4o, and stores the result for downstream agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import litellm

from agents.agent_2_audience.prompts import AUDIENCE_SYNTHESIS_PROMPT
from agents.agent_2_audience.schemas import AudienceOutput, AudienceSegment
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_audience(run_id: str, feedback: str | None = None) -> AudienceOutput:
    """Run the audience synthesis LLM call for a given run_id.

    Args:
        run_id: Pipeline run identifier — used to fetch the profile from ChromaDB.
        feedback: Optional feedback to guide refinement.

    Returns:
        AudienceOutput with 3-5 AudienceSegment instances.
    """
    research_raw = get_agent_output(run_id, "research_decision")
    profile_raw = get_agent_output(run_id, "profile")

    if profile_raw is None:
        logger.warning("Agent 2: no profile found in ChromaDB for run_id=%s", run_id)
    if research_raw is None:
        logger.warning("Agent 2: no research found in ChromaDB for run_id=%s", run_id)

    profile_data = profile_raw or "{}"
    research_data = research_raw or "{}"

    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised audience segments."
        if feedback
        else ""
    )

    prompt = AUDIENCE_SYNTHESIS_PROMPT.format(
        profile_data=profile_data,
        research_data=research_data,
        feedback=feedback_instruction,
    )

    response = await asyncio.wait_for(
        litellm.acompletion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            temperature=0.4,
        ),
        timeout=30.0,
    )

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return AudienceOutput(**data)


async def agent_2_audience_node(state: BlitzState) -> dict:
    """Audience Identifier node: generates synthetic audience segments.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step and audience_output.
    """
    run_id: str = state.get("run_id", "")

    output = await run_audience(run_id)

    store_agent_output(run_id, "audience", json.dumps(output.model_dump()))

    return {
        "current_step": 2,
        "audience_output": output.model_dump(),
    }
