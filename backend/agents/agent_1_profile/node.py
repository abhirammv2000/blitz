"""LangGraph node function for Agent 1 (Marketing Profile).

Implements the HITL reject loop pattern:
- Reads research dossier from ChromaDB (cross-agent context from Agent 0)
- Calls run_profile() with research data + optional feedback
- Interrupts with the MarketingProfile for human review
- Handles approve / edit / override / reject decisions
- On reject: loops back with feedback to refine the profile
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

from agents.agent_1_profile.prompts import PROFILE_SYNTHESIS_PROMPT
from agents.agent_1_profile.schemas import MarketingProfile
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_profile(run_id: str, feedback: str | None = None) -> MarketingProfile:
    """Run the profile synthesis LLM call for a given run_id.

    Reads the research dossier from ChromaDB (stored by Agent 0 as
    "research_decision"), then calls GPT-4o to synthesize a MarketingProfile.

    Args:
        run_id: Pipeline run identifier — used to fetch research from ChromaDB.
        feedback: Optional reject feedback from HITL loop to guide refinement.

    Returns:
        MarketingProfile with brand_dna, positioning_statement, usps, marketing_gaps.
    """
    # Read research dossier from ChromaDB (cross-agent context)
    research_raw = get_agent_output(run_id, "research_decision")
    if research_raw is None:
        logger.warning("Agent 1: no research_decision found in ChromaDB for run_id=%s", run_id)
        research_data = "{}"
    else:
        research_data = research_raw

    # Build feedback instruction
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

    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return MarketingProfile(**data)


async def agent_1_profile_node(state: BlitzState) -> dict:
    """Marketing Profile Creator node: synthesizes brand DNA and positioning.

    HITL loop pattern:
    1. Run profile synthesis (with optional reject feedback)
    2. Interrupt — surface MarketingProfile to frontend for human review
    3. On resume: check decision action
       - "approve": accept output as-is, break
       - "edit": merge user edits into output, break
       - "override": replace output with user-supplied data, break
       - "reject": set feedback, loop back to step 1

    After loop: stores the final output and HITL decision in ChromaDB.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step, profile_output, and approved flag.
    """
    run_id: str = state.get("run_id", "")

    feedback: str | None = None
    final_output: MarketingProfile | None = None
    decision: dict = {}

    while True:
        # Run (or re-run with feedback) the profile synthesis
        output = await run_profile(run_id, feedback)

        # Interrupt: surface MarketingProfile to frontend for HITL review
        interrupt_value = {
            "step": 1,
            "agent": "agent_1_profile",
            "output": output.model_dump(),
            "action": "approve | edit | reject | override",
        }
        decision = interrupt(interrupt_value)

        action = decision.get("action", "approve")

        if action == "approve":
            final_output = output
            break

        elif action == "edit":
            # Merge user edits into the output
            edits = decision.get("data", {})
            final_output = MarketingProfile(**{**output.model_dump(), **edits})
            break

        elif action == "override":
            # Replace output entirely with user-supplied data
            final_output = MarketingProfile(**decision["data"])
            break

        elif action == "reject":
            # Loop back with feedback to refine profile
            feedback = decision.get("feedback", "")
            continue

        else:
            # Unknown action — treat as approve
            final_output = output
            break

    # Store profile output and HITL decision in ChromaDB for downstream agents
    store_agent_output(run_id, "profile", json.dumps(final_output.model_dump()))
    store_agent_output(run_id, "profile_decision", json.dumps(decision))

    return {
        "current_step": 1,
        "profile_output": final_output.model_dump(),
        "approved": True,
    }
