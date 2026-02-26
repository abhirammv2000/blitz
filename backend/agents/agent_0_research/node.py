"""LangGraph node function for Agent 0 (Research).

Runs the research pipeline and stores the output in ChromaDB for downstream agents.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

from agents.agent_0_research.progress import get_queue
from agents.agent_0_research.research import run_research
from agents.agent_0_research.schemas import ResearchOutput
from db import store_agent_output
from state import BlitzState


async def agent_0_research_node(state: BlitzState) -> dict:
    """Research Scout node: gathers company intelligence.

    Args:
        state: BlitzState with company_url and run_id.

    Returns:
        State update dict with current_step and research_output.
    """
    company_url: str = state.get("company_url", "")
    run_id: str = state.get("run_id", "")

    output = await run_research(company_url, run_id)

    store_agent_output(run_id, "research_decision", json.dumps(output.model_dump()))

    return {
        "current_step": 0,
        "research_output": output.model_dump(),
    }
