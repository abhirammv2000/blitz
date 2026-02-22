"""LangGraph StateGraph wiring — 6 agent nodes with interrupt() gates.

Exports:
  build_builder() — returns the uncompiled StateGraph builder
  build_graph()   — async; compiles the graph with AsyncSqliteSaver checkpointer

Each agent node:
1. Sets current_step in state to its index
2. Calls interrupt() to pause and surface a HITL payload to the frontend
3. Returns a stub approval (auto-approve for now — real HITL wired in Phase 2)

Why AsyncSqliteSaver (not SqliteSaver):
- graph.astream() inside async FastAPI endpoints requires an async checkpointer
- Sync SqliteSaver raises NotImplementedError in async context
- AsyncSqliteSaver + aiosqlite is the correct pair for async LangGraph

Why SQLite (not MemorySaver):
- State must survive process restarts for the demo
- interrupt() requires a checkpointer at compile time
"""

from contextlib import asynccontextmanager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.agent_0_research.node import agent_0_research_node
from state import BlitzState

# ---------------------------------------------------------------------------
# Agent node functions — stubs with interrupt() gates (agent_0 is real)
# ---------------------------------------------------------------------------


def agent_1_profile_node(state: BlitzState) -> dict:
    """Marketing Profile: Extracts brand DNA, positioning, USPs, and marketing gaps."""
    interrupt({
        "step": 1,
        "agent": "agent_1_profile",
        "output": None,
        "action": "approve | edit | reject | override",
    })
    return {"current_step": 1, "approved": True}


def agent_2_audience_node(state: BlitzState) -> dict:
    """Audience Identifier: Generates synthetic audience segments with psychographics."""
    interrupt({
        "step": 2,
        "agent": "agent_2_audience",
        "output": None,
        "action": "approve | edit | reject | override",
    })
    return {"current_step": 2, "approved": True}


def agent_3_content_node(state: BlitzState) -> dict:
    """Content Strategist: Creates social posts, email campaigns, blog outlines, and calendar."""
    interrupt({
        "step": 3,
        "agent": "agent_3_content",
        "output": None,
        "action": "approve | edit | reject | override",
    })
    return {"current_step": 3, "approved": True}


def agent_4_sales_node(state: BlitzState) -> dict:
    """Sales Agent: Builds email sequences, LinkedIn templates, and pipeline stages."""
    interrupt({
        "step": 4,
        "agent": "agent_4_sales",
        "output": None,
        "action": "approve | edit | reject | override",
    })
    return {"current_step": 4, "approved": True}


def agent_5_ads_node(state: BlitzState) -> dict:
    """Ad Creative: Generates ad copy, visual concepts, and A/B variants."""
    interrupt({
        "step": 5,
        "agent": "agent_5_ads",
        "output": None,
        "action": "approve | edit | reject | override",
    })
    return {"current_step": 5, "approved": True}


# ---------------------------------------------------------------------------
# Graph builder (uncompiled — needs checkpointer attached at startup)
# ---------------------------------------------------------------------------

builder = StateGraph(BlitzState)

builder.add_node("agent_0_research", agent_0_research_node)
builder.add_node("agent_1_profile", agent_1_profile_node)
builder.add_node("agent_2_audience", agent_2_audience_node)
builder.add_node("agent_3_content", agent_3_content_node)
builder.add_node("agent_4_sales", agent_4_sales_node)
builder.add_node("agent_5_ads", agent_5_ads_node)

builder.add_edge(START, "agent_0_research")
builder.add_edge("agent_0_research", "agent_1_profile")
builder.add_edge("agent_1_profile", "agent_2_audience")
builder.add_edge("agent_2_audience", "agent_3_content")
builder.add_edge("agent_3_content", "agent_4_sales")
builder.add_edge("agent_4_sales", "agent_5_ads")
builder.add_edge("agent_5_ads", END)


@asynccontextmanager
async def build_graph():
    """Async context manager: open AsyncSqliteSaver and yield a compiled graph.

    Usage in FastAPI lifespan:
        async with build_graph() as graph:
            ...  # graph is live here

    The context manager keeps the AsyncSqliteSaver connection open for the
    entire scope, which is required for interrupt() / resume to work across
    multiple HTTP requests.
    """
    async with AsyncSqliteSaver.from_conn_string("blitz.db") as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        yield graph
