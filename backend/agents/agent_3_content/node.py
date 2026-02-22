"""LangGraph node function for Agent 3 (Content Strategy).

Implements the HITL reject loop pattern:
- Reads Agent 1's profile AND Agent 2's audience segments from ChromaDB
- Calls run_content() to generate platform-optimized content assets
- Interrupts with the ContentOutput for human review
- Handles approve / edit / override / reject decisions
- On reject: loops back with feedback to refine content
- Stores final HITL decision in ChromaDB for downstream agents

Why async: litellm.acompletion() is awaited; LangGraph supports async
node functions when using graph.astream() in an async FastAPI context.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import litellm
from langgraph.types import interrupt

from agents.agent_3_content.prompts import CONTENT_SYNTHESIS_PROMPT
from agents.agent_3_content.schemas import ContentOutput
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_content(run_id: str, feedback: str | None = None) -> ContentOutput:
    """Run the content synthesis LLM call for a given run_id.

    Reads Agent 1's marketing profile AND Agent 2's audience segments from
    ChromaDB (cross-agent context), then calls GPT-4o to generate platform-
    optimized content assets matching the brand voice.

    Args:
        run_id: Pipeline run identifier — used to fetch profile and audience.
        feedback: Optional reject feedback from HITL loop to guide refinement.

    Returns:
        ContentOutput with social posts, email campaigns, blog outlines,
        and a 30-day content calendar.
    """
    # Read Agent 1's profile from ChromaDB — cross-agent context
    profile_raw = get_agent_output(run_id, "profile")
    if profile_raw is None:
        logger.warning("Agent 3: no profile found in ChromaDB for run_id=%s", run_id)
        profile_data = "{}"
    else:
        profile_data = profile_raw

    # Read Agent 2's audience segments from ChromaDB — cross-agent context
    audience_raw = get_agent_output(run_id, "audience")
    if audience_raw is None:
        logger.warning("Agent 3: no audience found in ChromaDB for run_id=%s", run_id)
        audience_data = "{}"
    else:
        audience_data = audience_raw

    # Build feedback instruction
    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised content."
        if feedback
        else ""
    )

    prompt = CONTENT_SYNTHESIS_PROMPT.format(
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

    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return ContentOutput(**data)


async def agent_3_content_node(state: BlitzState) -> dict:
    """Content Strategist node: generates platform-optimized content assets.

    HITL loop pattern:
    1. Run content synthesis (with optional reject feedback)
    2. Interrupt — surface ContentOutput to frontend for human review
    3. On resume: check decision action
       - "approve": accept output as-is, break
       - "edit": merge user edits into output, break
       - "override": replace output with user-supplied data, break
       - "reject": set feedback, loop back to step 1

    After loop: stores the final output and HITL decision in ChromaDB.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step, content_output, and approved flag.
    """
    run_id: str = state.get("run_id", "")

    feedback: str | None = None
    final_output: ContentOutput | None = None
    decision: dict = {}

    while True:
        # Run (or re-run with feedback) the content synthesis
        output = await run_content(run_id, feedback)

        # Interrupt: surface ContentOutput to frontend for HITL review
        decision = interrupt({
            "step": 3,
            "agent": "agent_3_content",
            "output": output.model_dump(),
            "action": "approve | edit | reject | override",
        })

        action = decision.get("action", "approve")

        if action == "approve":
            final_output = output
            break

        elif action == "edit":
            # Merge user edits into the output
            edits = decision.get("data", {})
            final_output = ContentOutput(**{**output.model_dump(), **edits})
            break

        elif action == "override":
            # Replace output entirely with user-supplied data
            final_output = ContentOutput(**decision["data"])
            break

        elif action == "reject":
            # Loop back with feedback to refine content
            feedback = decision.get("feedback", "")
            continue

        else:
            # Unknown action — treat as approve
            final_output = output
            break

    # Store content output and HITL decision in ChromaDB for downstream agents
    store_agent_output(run_id, "content", json.dumps(final_output.model_dump()))
    store_agent_output(run_id, "content_decision", json.dumps(decision))

    return {
        "current_step": 3,
        "content_output": final_output.model_dump(),
        "approved": True,
    }
