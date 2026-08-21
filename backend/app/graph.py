"""
LangGraph Pipeline Configuration

This file wires together our 6 AI agents into a single, automated pipeline.
It exports a `build_graph()` function that gives us the ready-to-run graph.

How it works:
- The agents run one after another in a straight line: 
  Research -> Profile -> Audience -> Content -> Sales -> Ads
- There's no human intervention needed in the middle.
- They share data with each other using ChromaDB behind the scenes.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.agent_0_research.node import agent_0_research_node
from app.agents.agent_1_profile.node import agent_1_profile_node
from app.agents.agent_2_audience.node import agent_2_audience_node
from app.agents.agent_3_content.node import agent_3_content_node
from app.agents.agent_4_sales.node import agent_4_sales_node
from app.agents.agent_5_ads.critic import critic_ads_node
from app.agents.agent_5_ads.node import agent_5_ads_node
from app.state import BlitzState
from app.telemetry import agent_context

# ---------------------------------------------------------------------------
# Graph Builder Setup
# ---------------------------------------------------------------------------

# We use a StateGraph to pass around our BlitzState object between agents.
builder = StateGraph(BlitzState)

def instrumented(name: str, node):
    """Label every LLM call this node makes so telemetry knows who made it.

    Doing it here means the agents don't need to know telemetry exists, and a
    new node can't be added without being measured.
    """

    async def wrapper(state: BlitzState) -> dict:
        with agent_context(state.get("run_id"), name):
            return await node(state)

    wrapper.__name__ = f"instrumented_{name}"
    return wrapper


# 1. First, we add all our agent functions as "nodes" in the graph.
builder.add_node("agent_0_research", instrumented("agent_0_research", agent_0_research_node))
builder.add_node("agent_1_profile", instrumented("agent_1_profile", agent_1_profile_node))
builder.add_node("agent_2_audience", instrumented("agent_2_audience", agent_2_audience_node))
builder.add_node("agent_3_content", instrumented("agent_3_content", agent_3_content_node))
builder.add_node("agent_4_sales", instrumented("agent_4_sales", agent_4_sales_node))
builder.add_node("agent_5_ads", instrumented("agent_5_ads", agent_5_ads_node))
builder.add_node("critic_ads", instrumented("critic_ads", critic_ads_node))

# 2. Next, we define the flow by drawing "edges" (connections) between the nodes.
builder.add_edge(START, "agent_0_research")
builder.add_edge("agent_0_research", "agent_1_profile")
builder.add_edge("agent_1_profile", "agent_2_audience")
builder.add_edge("agent_2_audience", "agent_3_content")
builder.add_edge("agent_3_content", "agent_4_sales")
builder.add_edge("agent_4_sales", "agent_5_ads")
builder.add_edge("agent_5_ads", "critic_ads")

def route_after_critic(state: BlitzState):
    if state.get("ads_approved"):
        return END
    return "agent_5_ads"

builder.add_conditional_edges("critic_ads", route_after_critic, {"agent_5_ads": "agent_5_ads", END: END})


def build_graph():
    """
    Compile the graph into a runnable application.
    
    We use MemorySaver here to keep track of the pipeline's progress in memory. 
    We previously used a SQLite database for this, but since we no longer need 
    to pause and resume the pipeline (it just runs straight through), MemorySaver 
    is much faster and avoids pesky file-locking issues, especially on Windows!
    """
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
