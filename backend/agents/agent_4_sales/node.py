"""LangGraph node function for Agent 4 (Sales Enablement).

Implements the HITL reject loop pattern:
- Reads Agent 1's profile AND Agent 2's audience segments from ChromaDB
- Calls run_sales() to generate consultative outreach sequences and pipeline assets
- Interrupts with the SalesOutput for human review
- Handles approve / edit / override / reject decisions
- On reject: loops back with feedback to refine sales materials
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

from agents.agent_4_sales.prompts import SALES_SYNTHESIS_PROMPT
from agents.agent_4_sales.schemas import SalesOutput
from db import get_agent_output, store_agent_output
from state import BlitzState

logger = logging.getLogger(__name__)


async def run_sales(run_id: str, feedback: str | None = None) -> SalesOutput:
    """Run the sales synthesis LLM call for a given run_id.

    Reads Agent 1's marketing profile AND Agent 2's audience segments from
    ChromaDB (cross-agent context), then calls GPT-4o to generate consultative
    outreach sequences, LinkedIn templates, lead scoring tiers, and pipeline stages.

    Args:
        run_id: Pipeline run identifier — used to fetch profile and audience.
        feedback: Optional reject feedback from HITL loop to guide refinement.

    Returns:
        SalesOutput with email sequences, LinkedIn templates, lead scoring, and pipeline stages.
    """
    # Read Agent 1's profile from ChromaDB — cross-agent context
    profile_raw = get_agent_output(run_id, "profile")
    if profile_raw is None:
        logger.warning("Agent 4: no profile found in ChromaDB for run_id=%s", run_id)
        profile_data = "{}"
    else:
        profile_data = profile_raw

    # Read Agent 2's audience segments from ChromaDB — cross-agent context
    audience_raw = get_agent_output(run_id, "audience")
    if audience_raw is None:
        logger.warning("Agent 4: no audience found in ChromaDB for run_id=%s", run_id)
        audience_data = "{}"
    else:
        audience_data = audience_raw

    # Build feedback instruction
    feedback_instruction = (
        f"User feedback from prior attempt: {feedback}\nIncorporate this feedback into your revised sales materials."
        if feedback
        else ""
    )

    prompt = SALES_SYNTHESIS_PROMPT.format(
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

    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("```").strip()

    data = json.loads(content)
    return SalesOutput(**data)


async def agent_4_sales_node(state: BlitzState) -> dict:
    """Sales Agent node: generates consultative outreach and pipeline assets.

    HITL loop pattern:
    1. Run sales synthesis (with optional reject feedback)
    2. Interrupt — surface SalesOutput to frontend for human review
    3. On resume: check decision action
       - "approve": accept output as-is, break
       - "edit": merge user edits into output, break
       - "override": replace output with user-supplied data, break
       - "reject": set feedback, loop back to step 1

    After loop: stores the final output and HITL decision in ChromaDB.

    Args:
        state: BlitzState with run_id.

    Returns:
        State update dict with current_step, sales_output, and approved flag.
    """
    run_id: str = state.get("run_id", "")

    feedback: str | None = None
    final_output: SalesOutput | None = None
    decision: dict = {}

    while True:
        # Run (or re-run with feedback) the sales synthesis
        output = await run_sales(run_id, feedback)

        # Interrupt: surface SalesOutput to frontend for HITL review
        decision = interrupt({
            "step": 4,
            "agent": "agent_4_sales",
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
            final_output = SalesOutput(**{**output.model_dump(), **edits})
            break

        elif action == "override":
            # Replace output entirely with user-supplied data
            final_output = SalesOutput(**decision["data"])
            break

        elif action == "reject":
            # Loop back with feedback to refine sales materials
            feedback = decision.get("feedback", "")
            continue

        else:
            # Unknown action — treat as approve
            final_output = output
            break

    # Store sales output and HITL decision in ChromaDB for downstream agents
    store_agent_output(run_id, "sales", json.dumps(final_output.model_dump()))
    store_agent_output(run_id, "sales_decision", json.dumps(decision))

    return {
        "current_step": 4,
        "sales_output": final_output.model_dump(),
        "approved": True,
    }
