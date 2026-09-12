"""A hard ceiling on how many pipeline runs can start in a day.

The access key (see app.main.require_access_key) stops anonymous drive-by
use; this is the backstop for the case where the key itself leaks or gets
shared past who it was meant for. One row per UTC day, incremented
atomically so two requests racing to start a run can't both slip through
one slot under the cap.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.config import settings

_DB_PATH = settings.sqlite_file


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_usage_table() -> None:
    """Create the daily_runs table if it doesn't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_runs (
                day TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def check_and_increment_daily_cap(cap: int) -> bool:
    """Count today's run against `cap`. Returns whether it's allowed.

    cap <= 0 means no cap - the common case locally, where this isn't
    configured at all. Allowed calls are counted; a call that gets refused
    is not, so a request right at the cap doesn't burn a slot for nothing.
    """
    if cap <= 0:
        return True

    today = _today()
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT count FROM daily_runs WHERE day = ?", (today,)).fetchone()
        current = row["count"] if row else 0
        if current >= cap:
            conn.commit()
            return False
        if row:
            conn.execute("UPDATE daily_runs SET count = count + 1 WHERE day = ?", (today,))
        else:
            conn.execute("INSERT INTO daily_runs (day, count) VALUES (?, 1)", (today,))
        conn.commit()
        return True
    finally:
        conn.close()


def runs_today() -> int:
    """How many runs have started today. Used by /health-adjacent reporting only."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT count FROM daily_runs WHERE day = ?", (_today(),)).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()
