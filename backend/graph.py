"""LangGraph StateGraph wiring — 6 agent nodes with interrupt() gates.

Exports:
  build_builder() — returns the uncompiled StateGraph builder
  build_graph()   — async; compiles the graph with AsyncSqliteSaver checkpointer

Agent implementation status:
- agent_0_research: real async implementation (Phase 2)
- agent_1_profile: real async implementation (Phase 3)
- agent_2_audience: real async implementation (Phase 3)
- agent_3_content: real async implementation (Phase 4)
- agent_4_sales: real async implementation (Phase 4)
- agent_5_ads: real async implementation with user-triggered DALL-E 3 image gen (Phase 4)

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

from agents.agent_0_research.node import agent_0_research_node
from agents.agent_1_profile.node import agent_1_profile_node
from agents.agent_2_audience.node import agent_2_audience_node
from agents.agent_3_content.node import agent_3_content_node
from agents.agent_4_sales.node import agent_4_sales_node
from agents.agent_5_ads.node import agent_5_ads_node
from state import BlitzState

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
