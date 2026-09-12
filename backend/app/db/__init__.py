"""Persistence.

`chroma` holds the cross-agent pipeline outputs; `leads` holds voice-agent
lead capture in SQLite; `usage` holds the daily pipeline-run cap. The names
used most often are re-exported here so callers can write
`from app.db import get_agent_context`.
"""

from app.db.chroma import (
    get_agent_context,
    get_agent_output,
    get_collection,
    get_run_context,
    reset_client,
    store_agent_output,
)
from app.db.leads import get_leads_for_run, init_leads_table, insert_lead
from app.db.usage import check_and_increment_daily_cap, init_usage_table, runs_today

__all__ = [
    "get_agent_context",
    "get_agent_output",
    "get_collection",
    "get_run_context",
    "reset_client",
    "store_agent_output",
    "get_leads_for_run",
    "init_leads_table",
    "insert_lead",
    "check_and_increment_daily_cap",
    "init_usage_table",
    "runs_today",
]
