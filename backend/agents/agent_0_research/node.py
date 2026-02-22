"""LangGraph node function for Agent 0 (Research).

Implements the HITL reject loop pattern:
- Calls run_research() with the company URL from state
- Interrupts with the ResearchOutput for human review
- Handles approve / edit / override / reject decisions
- On reject: loops back with feedback to refine research
- Stores final HITL decision in ChromaDB for downstream agents

Why async: run_research() uses asyncio internally; LangGraph supports async
node functions when using graph.astream() in an async FastAPI context.
"""

from __future__ import annotations

import json

from langgraph.types import interrupt

from agents.agent_0_research.progress import get_queue
from agents.agent_0_research.research import run_research
from agents.agent_0_research.schemas import ResearchOutput
from db import store_agent_output
from state import BlitzState


async def agent_0_research_node(state: BlitzState) -> dict:
    """Research Scout node: gathers company intelligence with HITL review loop.

    HITL loop pattern:
    1. Run research (with optional reject feedback)
    2. Interrupt — surface ResearchOutput to frontend for human review
    3. On resume: check decision action
       - "approve": accept output as-is, break
       - "edit": merge user edits into output, break
       - "override": replace output with user-supplied data, break
       - "reject": set feedback, loop back to step 1

    After loop: stores the final HITL decision in ChromaDB.

    Args:
        state: BlitzState with company_url and run_id.

    Returns:
        State update dict with current_step, research_output, and approved flag.
    """
    company_url: str = state.get("company_url", "")
    run_id: str = state.get("run_id", "")

    feedback: str | None = None
    final_output: ResearchOutput | None = None
    decision: dict = {}

    while True:
        # Run (or re-run with feedback) the research pipeline
        output = await run_research(company_url, run_id, feedback)

        # Interrupt: surface ResearchOutput to frontend for HITL review
        decision = interrupt({
            "step": 0,
            "agent": "agent_0_research",
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
            final_output = ResearchOutput(**{**output.model_dump(), **edits})
            break

        elif action == "override":
            # Replace output entirely with user-supplied data
            final_output = ResearchOutput(**decision["data"])
            break

        elif action == "reject":
            # Loop back with feedback to refine research
            feedback = decision.get("feedback", "")
            continue

        else:
            # Unknown action — treat as approve
            final_output = output
            break

    # Store HITL decision in ChromaDB for downstream agent context
    store_agent_output(run_id, "research_decision", json.dumps(decision))

    return {
        "current_step": 0,
        "research_output": final_output.model_dump(),
        "approved": True,
    }
