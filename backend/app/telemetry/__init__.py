"""AI telemetry: per-call usage, cost, latency, and reliability.

Answers the questions you cannot run an agent system in production without:
what does a run cost, which agent dominates that cost, how often does the
primary model fail over, and is any of it getting worse.
"""

from app.telemetry.context import agent_context, current_agent, current_run_id
from app.telemetry.logger import install_telemetry
from app.telemetry.store import (
    get_agent_costs,
    get_run_detail,
    get_runs,
    get_summary,
    init_telemetry_table,
    record_call,
)

__all__ = [
    "agent_context",
    "current_agent",
    "current_run_id",
    "install_telemetry",
    "init_telemetry_table",
    "record_call",
    "get_summary",
    "get_agent_costs",
    "get_runs",
    "get_run_detail",
]
