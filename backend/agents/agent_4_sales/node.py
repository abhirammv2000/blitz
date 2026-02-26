"""LangGraph node function for Agent 4 (Sales Enablement).

Reads profile and audience segments from ChromaDB, generates sales outreach
materials via GPT-4o, and stores the result for downstream agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import litellm

from agents.agent_4_sales.prompts import SALES_SYNTHESIS_PROMPT
from agents.agent_4_sales.schemas import SalesOutput
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_sales(run_id: str, feedback: str | None = None) -> SalesOutput:
    """Run the sales synthesis LLM call for a given run_id.

    Args:
        run_id: Pipeline run identifier — used to fetch profile and audience.
        feedback: Optional feedback to guide refinement.

    Returns:
        SalesOutput with email sequences, LinkedIn templates, lead scoring, and pipeline stages.
    """
    research_raw = get_agent_output(run_id, "research_decision")
    if research_raw is None:
        logger.warning("Agent 4: no research found in ChromaDB for run_id=%s", run_id)
        research_data = "{}"
    else:
        research_data = research_raw

    profile_raw = get_agent_output(run_id, "profile")
    if profile_raw is None:
        logger.warning("Agent 4: no profile found in ChromaDB for run_id=%s", run_id)
        profile_data = "{}"
    else:
        profile_data = profile_raw

    audience_raw = get_agent_output(run_id, "audience")
    if audience_raw is None:
        logger.warning("Agent 4: no audience found in ChromaDB for run_id=%s", run_id)
        audience_data = "{}"
    else:
        audience_data = audience_raw

    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised sales materials."
        if feedback
        else ""
    )

    prompt = SALES_SYNTHESIS_PROMPT.format(
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
        ),
        timeout=30.0,
    )

    content = response.choices[0].message.content or "{}"
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return SalesOutput(**data)


async def agent_4_sales_node(state: BlitzState) -> dict:
    """Sales Agent node: generates consultative outreach and pipeline assets.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step and sales_output.
    """
    run_id: str = state.get("run_id", "")

    output = await run_sales(run_id)

    store_agent_output(run_id, "sales", json.dumps(output.model_dump()))

    return {
        "current_step": 4,
        "sales_output": output.model_dump(),
    }
