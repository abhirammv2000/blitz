"""Stores one row per LLM call in SQLite, and the queries that read them back.

We keep raw calls rather than per-run totals so a new question is just a new
query. Nothing in here raises: if telemetry breaks it should cost us a row,
not a pipeline run.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

_DB_PATH = settings.sqlite_file


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_telemetry_table() -> None:
    """Create the llm_calls table if it isn't there yet."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                run_id TEXT,
                agent TEXT,
                model_group TEXT,
                model TEXT,
                provider TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                error_type TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_calls_run ON llm_calls(run_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_calls_ts ON llm_calls(ts)")
        conn.commit()
    finally:
        conn.close()


def record_call(
    *,
    run_id: str | None,
    agent: str | None,
    model_group: str | None,
    model: str | None,
    provider: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: float = 0.0,
    latency_ms: int = 0,
    status: str = "success",
    error_type: str | None = None,
) -> None:
    """Save one LLM call."""
    try:
        conn = _get_conn()
        try:
            conn.execute(
                """
                INSERT INTO llm_calls (
                    ts, run_id, agent, model_group, model, provider,
                    prompt_tokens, completion_tokens, total_tokens,
                    cost_usd, latency_ms, status, error_type
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    run_id, agent, model_group, model, provider,
                    prompt_tokens, completion_tokens, prompt_tokens + completion_tokens,
                    cost_usd, latency_ms, status, error_type,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not write telemetry row: %s", exc)


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    try:
        conn = _get_conn()
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telemetry query failed: %s", exc)
        return []


def get_summary() -> dict:
    """Totals across every call we've recorded."""
    rows = _rows("""
        SELECT
            COUNT(*)                             AS calls,
            COUNT(DISTINCT run_id)               AS runs,
            COALESCE(SUM(cost_usd), 0)           AS total_cost_usd,
            COALESCE(SUM(total_tokens), 0)       AS total_tokens,
            COALESCE(AVG(latency_ms), 0)         AS avg_latency_ms,
            COALESCE(SUM(status = 'success'), 0) AS successes,
            COALESCE(SUM(status = 'failure'), 0) AS failures
        FROM llm_calls
    """)
    summary = rows[0] if rows else {}

    # Averages are done here rather than in SQL so an empty table gives 0
    # instead of a division error.
    runs = summary.get("runs") or 0
    summary["avg_cost_per_run_usd"] = (summary.get("total_cost_usd", 0) / runs) if runs else 0.0
    summary["avg_tokens_per_run"] = (summary.get("total_tokens", 0) / runs) if runs else 0
    calls = summary.get("calls") or 0
    summary["success_rate"] = (summary.get("successes", 0) / calls) if calls else 0.0

    summary["by_provider"] = _rows("""
        SELECT provider,
               COUNT(*) AS calls,
               COALESCE(SUM(cost_usd), 0) AS cost_usd,
               COALESCE(SUM(total_tokens), 0) AS tokens
        FROM llm_calls GROUP BY provider ORDER BY cost_usd DESC
    """)
    summary["by_model_group"] = _rows("""
        SELECT model_group,
               COUNT(*) AS calls,
               COALESCE(SUM(cost_usd), 0) AS cost_usd
        FROM llm_calls GROUP BY model_group ORDER BY cost_usd DESC
    """)
    return summary


def get_agent_costs() -> list[dict]:
    """Spend and latency per agent, most expensive first."""
    return _rows("""
        SELECT agent,
               COUNT(*)                       AS calls,
               COALESCE(SUM(cost_usd), 0)     AS cost_usd,
               COALESCE(SUM(total_tokens), 0) AS tokens,
               COALESCE(AVG(latency_ms), 0)   AS avg_latency_ms,
               COALESCE(MAX(latency_ms), 0)   AS max_latency_ms
        FROM llm_calls
        WHERE agent IS NOT NULL
        GROUP BY agent
        ORDER BY cost_usd DESC
    """)


def get_runs(limit: int = 50) -> list[dict]:
    """One row per pipeline run, newest first."""
    return _rows("""
        SELECT run_id,
               MIN(ts)                              AS started_at,
               COUNT(*)                             AS calls,
               COALESCE(SUM(cost_usd), 0)           AS cost_usd,
               COALESCE(SUM(total_tokens), 0)       AS tokens,
               COALESCE(SUM(latency_ms), 0)         AS total_latency_ms,
               COALESCE(SUM(status = 'failure'), 0) AS failures
        FROM llm_calls
        WHERE run_id IS NOT NULL
        GROUP BY run_id
        ORDER BY started_at DESC
        LIMIT ?
    """, (limit,))


def get_run_detail(run_id: str) -> dict:
    """Every call in one run, plus a per-agent breakdown."""
    return {
        "run_id": run_id,
        "calls": _rows("SELECT * FROM llm_calls WHERE run_id = ? ORDER BY ts", (run_id,)),
        "by_agent": _rows("""
            SELECT agent,
                   COUNT(*)                       AS calls,
                   COALESCE(SUM(cost_usd), 0)     AS cost_usd,
                   COALESCE(SUM(total_tokens), 0) AS tokens,
                   COALESCE(SUM(latency_ms), 0)   AS latency_ms
            FROM llm_calls WHERE run_id = ? GROUP BY agent ORDER BY cost_usd DESC
        """, (run_id,)),
    }
