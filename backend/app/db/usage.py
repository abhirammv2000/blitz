"""Hard ceilings on spend: pipeline runs per day, ad images per run.

The access key (see app.main.require_access_key) stops anonymous drive-by
use; these are the backstop for the case where the key itself leaks or gets
shared past who it was meant for. One row per key (UTC day, or run_id),
persisted here rather than in memory so the cap actually holds once the API
runs as more than one replica. The daily cap is a single atomic
check-and-increment; the per-run image cap checks and increments as two
separate steps so a failed generation doesn't consume the cap - see each
function's docstring.
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


def init_image_counts_table() -> None:
    """Create the image_counts table if it doesn't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS image_counts (
                run_id TEXT PRIMARY KEY,
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


def image_count(run_id: str) -> int:
    """How many images have been generated for this run so far.

    Was a module-level `dict[str, int]` in app.main - fine for one process,
    but silently stopped enforcing the per-run cap the moment the API ran
    as more than one replica, since each process had its own empty dict.
    """
    conn = _get_conn()
    try:
        row = conn.execute("SELECT count FROM image_counts WHERE run_id = ?", (run_id,)).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()


def increment_image_count(run_id: str) -> None:
    """Record one successful image generation for this run.

    Only called after `generate_ad_image` returns a real image - a failed
    generation must not consume part of the cap (see
    test_a_failed_generation_does_not_consume_cap), so unlike
    check_and_increment_daily_cap this isn't a single atomic
    check-and-increment: the caller checks `image_count` first, generates,
    and only then calls this. That leaves a narrow window where two
    concurrent requests for the same run_id could both read the same count
    and both generate - acceptable here since this endpoint is a manual,
    one-click-at-a-time UI action, not the daily cap's "stop anonymous
    drive-by use" backstop.
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT count FROM image_counts WHERE run_id = ?", (run_id,)).fetchone()
        if row:
            conn.execute("UPDATE image_counts SET count = count + 1 WHERE run_id = ?", (run_id,))
        else:
            conn.execute("INSERT INTO image_counts (run_id, count) VALUES (?, 1)", (run_id,))
        conn.commit()
    finally:
        conn.close()
