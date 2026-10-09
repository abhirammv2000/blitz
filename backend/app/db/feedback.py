"""User feedback and experiment assignments, in the same SQLite file as telemetry.

Three small tables:

- ratings: a thumbs up or down on one agent's output for a run. One row per
  (run, agent), so clicking again changes the vote instead of adding one.
- ad_picks: which ad variant a person preferred, one row per (run, ad group).
- experiment_assignments: which variant of an experiment a run was given.

Reads that feed the dashboard join these with llm_calls, so an experiment shows
cost next to the quality signal.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.experiments import verdict, wilson_interval

# The metric an experiment is judged on: thumbs on this agent's output.
ADS_AGENT = "agent_5_ads"


def _db_path() -> Path:
    return settings.sqlite_file


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def init_feedback_tables() -> None:
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                run_id TEXT NOT NULL,
                agent  TEXT NOT NULL,
                value  INTEGER NOT NULL CHECK (value IN (-1, 1)),
                ts     TEXT NOT NULL,
                PRIMARY KEY (run_id, agent)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ad_picks (
                run_id      TEXT NOT NULL,
                ad_copy_ref TEXT NOT NULL,
                chosen      TEXT NOT NULL,
                ts          TEXT NOT NULL,
                PRIMARY KEY (run_id, ad_copy_ref)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_assignments (
                run_id     TEXT NOT NULL,
                experiment TEXT NOT NULL,
                variant    TEXT NOT NULL,
                ts         TEXT NOT NULL,
                PRIMARY KEY (run_id, experiment)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_rating(run_id: str, agent: str, value: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO ratings (run_id, agent, value, ts) VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, agent) DO UPDATE SET value = excluded.value, ts = excluded.ts
            """,
            (run_id, agent, value, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def save_pick(run_id: str, ad_copy_ref: str, chosen: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO ad_picks (run_id, ad_copy_ref, chosen, ts) VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, ad_copy_ref) DO UPDATE SET chosen = excluded.chosen, ts = excluded.ts
            """,
            (run_id, ad_copy_ref, chosen, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def record_assignment(run_id: str, experiment: str, variant: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO experiment_assignments (run_id, experiment, variant, ts) VALUES (?, ?, ?, ?)",
            (run_id, experiment, variant, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_feedback_summary() -> dict:
    """Thumbs per agent (with a 95% interval on the up-rate) and ad variant picks."""
    by_agent = []
    for row in _rows("""
        SELECT agent,
               SUM(value = 1)  AS up,
               SUM(value = -1) AS down,
               COUNT(*)        AS total
        FROM ratings GROUP BY agent ORDER BY agent
    """):
        low, high = wilson_interval(row["up"], row["total"])
        by_agent.append({
            **row,
            "up_rate": row["up"] / row["total"],
            "ci_low": low,
            "ci_high": high,
        })
    picks = _rows("""
        SELECT chosen, COUNT(*) AS count FROM ad_picks GROUP BY chosen ORDER BY count DESC
    """)
    return {"by_agent": by_agent, "ad_picks": picks}


def get_experiment_results(experiment: str) -> dict:
    """Per-variant rating rate, cost and latency for one experiment, plus a verdict."""
    rated = _rows(
        """
        SELECT a.variant                                   AS variant,
               COUNT(*)                                    AS runs,
               COUNT(r.value)                              AS rated,
               COALESCE(SUM(r.value = 1), 0)               AS up
        FROM experiment_assignments a
        LEFT JOIN ratings r ON r.run_id = a.run_id AND r.agent = ?
        WHERE a.experiment = ?
        GROUP BY a.variant
        ORDER BY a.variant
        """,
        (ADS_AGENT, experiment),
    )
    try:
        cost_rows = _rows(
            """
            SELECT a.variant                       AS variant,
                   AVG(t.cost)                     AS avg_cost_usd,
                   AVG(t.latency)                  AS avg_latency_ms
            FROM experiment_assignments a
            JOIN (SELECT run_id, SUM(cost_usd) AS cost, SUM(latency_ms) AS latency
                  FROM llm_calls WHERE run_id IS NOT NULL GROUP BY run_id) t
              ON t.run_id = a.run_id
            WHERE a.experiment = ?
            GROUP BY a.variant
            """,
            (experiment,),
        )
    except sqlite3.OperationalError:
        # No llm_calls table yet, so no cost numbers. The ratings still count.
        cost_rows = []
    per_run = {row["variant"]: row for row in cost_rows}

    variants = []
    for row in rated:
        low, high = wilson_interval(row["up"], row["rated"])
        cost = per_run.get(row["variant"], {})
        variants.append({
            **row,
            "up_rate": (row["up"] / row["rated"]) if row["rated"] else None,
            "ci_low": low,
            "ci_high": high,
            "avg_cost_usd": cost.get("avg_cost_usd"),
            "avg_latency_ms": cost.get("avg_latency_ms"),
        })
    return {
        "experiment": experiment,
        "metric": "thumbs-up rate on the ads step",
        "variants": variants,
        "verdict": verdict(variants),
    }
