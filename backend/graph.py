"""LangGraph StateGraph wiring — 6 agent nodes in a straight-through pipeline.

Exports:
  build_graph() — returns a compiled graph with MemorySaver checkpointer

Agent nodes run sequentially: research → profile → audience → content → sales → ads.
No HITL interrupts — each node runs to completion and passes data via ChromaDB.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.agent_0_research.node import agent_0_research_node
from agents.agent_1_profile.node import agent_1_profile_node
from agents.agent_2_audience.node import agent_2_audience_node
from agents.agent_3_content.node import agent_3_content_node
from agents.agent_4_sales.node import agent_4_sales_node
from agents.agent_5_ads.node import agent_5_ads_node
from state import BlitzState

# ---------------------------------------------------------------------------
# Graph builder
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


def build_graph():
    """Compile the graph with a MemorySaver checkpointer and return it.

    MemorySaver is used instead of AsyncSqliteSaver since we no longer need
    persistent checkpoints for HITL resume. This avoids SQLite file locking
    issues on Windows/OneDrive.
    """
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
