"""SQLite storage for voice agent lead capture.

Uses the same blitz.db file as the rest of the backend.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "blitz.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_leads_table() -> None:
    """Create the voice_leads table if it doesn't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS voice_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                company_name TEXT,
                agent_id TEXT,
                conversation_id TEXT UNIQUE,
                caller_name TEXT,
                email TEXT,
                phone TEXT,
                callback_time TEXT,
                raw_transcript TEXT,
                interested INTEGER,
                extracted_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def insert_lead(
    run_id: str,
    company_name: str | None = None,
    agent_id: str | None = None,
    conversation_id: str | None = None,
    caller_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    callback_time: str | None = None,
    raw_transcript: str | None = None,
    interested: bool | None = None,
) -> int:
    """Insert or replace a lead record. Returns the row id."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT OR REPLACE INTO voice_leads
               (run_id, company_name, agent_id, conversation_id,
                caller_name, email, phone, callback_time,
                raw_transcript, interested, extracted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                company_name,
                agent_id,
                conversation_id,
                caller_name,
                email,
                phone,
                callback_time,
                raw_transcript,
                1 if interested else (0 if interested is not None else None),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_leads_for_run(run_id: str) -> list[dict]:
    """Return all leads for a given pipeline run."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM voice_leads WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
