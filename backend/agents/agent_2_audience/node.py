"""LangGraph node function for Agent 2 (Audience Intelligence).

Implements the HITL reject loop pattern:
- Reads Agent 1's marketing profile from ChromaDB (cross-agent context)
- Calls run_audience() to generate 3-5 audience segments
- Interrupts with the AudienceOutput for human review
- Handles approve / edit / override / reject decisions
- On reject: loops back with feedback to refine segments
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

from agents.agent_2_audience.prompts import AUDIENCE_SYNTHESIS_PROMPT
from agents.agent_2_audience.schemas import AudienceOutput, AudienceSegment
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_audience(run_id: str, feedback: str | None = None) -> AudienceOutput:
    """Run the audience synthesis LLM call for a given run_id.

    Reads Agent 1's marketing profile from ChromaDB (cross-agent context),
    then calls GPT-4o to generate 3-5 audience segments with citation-style reasoning.

    Args:
        run_id: Pipeline run identifier — used to fetch the profile from ChromaDB.
        feedback: Optional reject feedback from HITL loop to guide refinement.

    Returns:
        AudienceOutput with 3-5 AudienceSegment instances.
    """
    # Read both Agent 0's research and Agent 1's profile from ChromaDB
    research_raw = get_agent_output(run_id, "research_decision")
    profile_raw = get_agent_output(run_id, "profile")

    if profile_raw is None:
        logger.warning("Agent 2: no profile found in ChromaDB for run_id=%s", run_id)
    if research_raw is None:
        logger.warning("Agent 2: no research_decision found in ChromaDB for run_id=%s", run_id)

    profile_data = profile_raw or "{}"
    research_data = research_raw or "{}"

    # Build feedback instruction
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

    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return AudienceOutput(**data)


async def agent_2_audience_node(state: BlitzState) -> dict:
    """Audience Identifier node: generates synthetic audience segments.

    HITL loop pattern:
    1. Run audience synthesis (with optional reject feedback)
    2. Interrupt — surface AudienceOutput to frontend for human review
    3. On resume: check decision action
       - "approve": accept output as-is, break
       - "edit": merge user edits into output, break
       - "override": replace output with user-supplied data, break
       - "reject": set feedback, loop back to step 1

    After loop: stores the final output and HITL decision in ChromaDB.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step, audience_output, and approved flag.
    """
    run_id: str = state.get("run_id", "")

    feedback: str | None = None
    final_output: AudienceOutput | None = None
    decision: dict = {}

    while True:
        # Run (or re-run with feedback) the audience synthesis
        output = await run_audience(run_id, feedback)

        # Interrupt: surface AudienceOutput to frontend for HITL review
        decision = interrupt({
            "step": 2,
            "agent": "agent_2_audience",
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
            final_output = AudienceOutput(**{**output.model_dump(), **edits})
            break

        elif action == "override":
            # Replace output entirely with user-supplied data
            final_output = AudienceOutput(**decision["data"])
            break

        elif action == "reject":
            # Loop back with feedback to refine segments
            feedback = decision.get("feedback", "")
            continue

        else:
            # Unknown action — treat as approve
            final_output = output
            break

    # Store audience output and HITL decision in ChromaDB for downstream agents
    store_agent_output(run_id, "audience", json.dumps(final_output.model_dump()))
    store_agent_output(run_id, "audience_decision", json.dumps(decision))

    return {
        "current_step": 2,
        "audience_output": final_output.model_dump(),
        "approved": True,
    }
