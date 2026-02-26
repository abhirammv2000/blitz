"""LangGraph node function for Agent 3 (Content Strategy).

Reads profile and audience segments from ChromaDB, generates content assets
via GPT-4o, and stores the result for downstream agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import litellm

from agents.agent_3_content.prompts import CONTENT_SYNTHESIS_PROMPT
from agents.agent_3_content.schemas import ContentOutput
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_content(run_id: str, feedback: str | None = None) -> ContentOutput:
    """Run the content synthesis LLM call for a given run_id.

    Args:
        run_id: Pipeline run identifier — used to fetch profile and audience.
        feedback: Optional feedback to guide refinement.

    Returns:
        ContentOutput with social posts, email campaigns, blog outlines,
        and a 30-day content calendar.
    """
    research_raw = get_agent_output(run_id, "research_decision")
    if research_raw is None:
        logger.warning("Agent 3: no research found in ChromaDB for run_id=%s", run_id)
        research_data = "{}"
    else:
        research_data = research_raw

    profile_raw = get_agent_output(run_id, "profile")
    if profile_raw is None:
        logger.warning("Agent 3: no profile found in ChromaDB for run_id=%s", run_id)
        profile_data = "{}"
    else:
        profile_data = profile_raw

    audience_raw = get_agent_output(run_id, "audience")
    if audience_raw is None:
        logger.warning("Agent 3: no audience found in ChromaDB for run_id=%s", run_id)
        audience_data = "{}"
    else:
        audience_data = audience_raw

    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised content."
        if feedback
        else ""
    )

    prompt = CONTENT_SYNTHESIS_PROMPT.format(
        research_data=research_data,
        profile_data=profile_data,
        audience_data=audience_data,
        feedback=feedback_instruction,
    )

    response = await asyncio.wait_for(
        litellm.acompletion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            temperature=0.4,
            max_tokens=8000,
        ),
        timeout=60.0,
    )

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return ContentOutput(**data)


async def agent_3_content_node(state: BlitzState) -> dict:
    """Content Strategist node: generates platform-optimized content assets.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step and content_output.
    """
    run_id: str = state.get("run_id", "")

    output = await run_content(run_id)

    store_agent_output(run_id, "content", json.dumps(output.model_dump()))

    return {
        "current_step": 3,
        "content_output": output.model_dump(),
    }
