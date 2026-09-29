"""Ratings, ad picks, experiment assignment and results, against a throwaway SQLite file."""

from __future__ import annotations

import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

import app.main as main_mod
from app.config import settings
from app.db import feedback as fb
from app.experiments import ADS_CRITIC

pytestmark = pytest.mark.usefixtures("isolated_chroma")

RUN = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "feedback.db"
    monkeypatch.setattr(fb, "_db_path", lambda: path)
    fb.init_feedback_tables()
    return path


@pytest.fixture
def client(db):
    with TestClient(main_mod.app) as c:
        yield c


# -- storage ---------------------------------------------------------------


def test_voting_again_changes_the_vote_instead_of_adding_one(db):
    fb.save_rating(RUN, "agent_5_ads", 1)
    fb.save_rating(RUN, "agent_5_ads", -1)

    row = fb.get_feedback_summary()["by_agent"][0]
    assert (row["up"], row["down"], row["total"]) == (0, 1, 1)


def test_summary_has_a_rate_and_an_interval_per_agent(db):
    for i in range(10):
        fb.save_rating(f"run-{i:04d}-xxxx", "agent_2_audience", 1 if i < 8 else -1)

    row = fb.get_feedback_summary()["by_agent"][0]
    assert row["up_rate"] == pytest.approx(0.8)
    assert row["ci_low"] == pytest.approx(0.4902, abs=1e-3)
    assert row["ci_high"] == pytest.approx(0.9433, abs=1e-3)


def test_an_empty_database_gives_an_empty_summary(db):
    assert fb.get_feedback_summary() == {"by_agent": [], "ad_picks": []}


def test_a_rating_other_than_up_or_down_is_refused_by_the_table(db):
    with pytest.raises(sqlite3.IntegrityError):
        fb.save_rating(RUN, "agent_5_ads", 0)


def test_ad_picks_are_counted_and_can_be_changed(db):
    fb.save_pick(RUN, "Google Ads", "A")
    fb.save_pick(RUN, "Google Ads", "B")
    fb.save_pick("22222222-2222-2222-2222-222222222222", "Google Ads", "B")

    assert fb.get_feedback_summary()["ad_picks"] == [{"chosen": "B", "count": 2}]


def test_the_first_assignment_for_a_run_sticks(db):
    fb.record_assignment(RUN, ADS_CRITIC, "critic_on")
    fb.record_assignment(RUN, ADS_CRITIC, "critic_off")

    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT variant FROM experiment_assignments").fetchall()
    assert rows == [("critic_on",)]


# -- experiment results ----------------------------------------------------


def _seed(db, *, with_costs: bool):
    """Two runs per variant. critic_on: one up one down. critic_off: both up."""
    plan = [
        ("run-on-1-xxxx", "critic_on", 1, 0.30, 40000),
        ("run-on-2-xxxx", "critic_on", -1, 0.34, 44000),
        ("run-off-1-xxx", "critic_off", 1, 0.20, 30000),
        ("run-off-2-xxx", "critic_off", 1, 0.22, 32000),
    ]
    for run_id, variant, vote, _cost, _latency in plan:
        fb.record_assignment(run_id, ADS_CRITIC, variant)
        fb.save_rating(run_id, "agent_5_ads", vote)
    if not with_costs:
        return
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE llm_calls (run_id TEXT, cost_usd REAL, latency_ms INTEGER)")
    for run_id, _variant, _vote, cost, latency in plan:
        # Two calls per run, to check the join sums per run before averaging.
        conn.execute("INSERT INTO llm_calls VALUES (?, ?, ?)", (run_id, cost / 2, latency // 2))
        conn.execute("INSERT INTO llm_calls VALUES (?, ?, ?)", (run_id, cost / 2, latency // 2))
    conn.commit()
    conn.close()


def test_results_count_runs_ratings_and_cost_per_variant(db):
    _seed(db, with_costs=True)

    res = fb.get_experiment_results(ADS_CRITIC)
    by = {v["variant"]: v for v in res["variants"]}

    assert (by["critic_on"]["runs"], by["critic_on"]["rated"], by["critic_on"]["up"]) == (2, 2, 1)
    assert (by["critic_off"]["runs"], by["critic_off"]["rated"], by["critic_off"]["up"]) == (2, 2, 2)
    assert by["critic_on"]["up_rate"] == pytest.approx(0.5)
    assert by["critic_on"]["avg_cost_usd"] == pytest.approx(0.32)
    assert by["critic_off"]["avg_cost_usd"] == pytest.approx(0.21)
    assert by["critic_on"]["avg_latency_ms"] == pytest.approx(42000)
    assert "Not enough ratings" in res["verdict"]


def test_a_run_nobody_rated_counts_as_a_run_but_not_a_rating(db):
    fb.record_assignment("run-a-xxxxxx", ADS_CRITIC, "critic_on")
    fb.record_assignment("run-b-xxxxxx", ADS_CRITIC, "critic_on")
    fb.save_rating("run-a-xxxxxx", "agent_5_ads", 1)
    # A thumb on a different step must not count toward the ads metric.
    fb.save_rating("run-b-xxxxxx", "agent_2_audience", 1)

    v = fb.get_experiment_results(ADS_CRITIC)["variants"][0]
    assert (v["runs"], v["rated"], v["up"]) == (2, 1, 1)


def test_results_still_work_when_there_is_no_cost_table(db):
    _seed(db, with_costs=False)

    v = fb.get_experiment_results(ADS_CRITIC)["variants"][0]
    assert v["avg_cost_usd"] is None
    assert v["rated"] == 2


def test_a_variant_with_no_ratings_has_no_rate(db):
    fb.record_assignment(RUN, ADS_CRITIC, "critic_on")

    v = fb.get_experiment_results(ADS_CRITIC)["variants"][0]
    assert v["up_rate"] is None


# -- endpoints -------------------------------------------------------------


def test_a_rating_posted_to_the_api_shows_up_in_the_summary(client):
    r = client.post("/feedback/rating", json={"run_id": RUN, "agent": "agent_5_ads", "value": 1})
    assert r.status_code == 200

    summary = client.get("/feedback/summary").json()
    assert summary["by_agent"][0]["agent"] == "agent_5_ads"
    assert summary["by_agent"][0]["up"] == 1


@pytest.mark.parametrize("body", [
    {"run_id": RUN, "agent": "not_an_agent", "value": 1},
    {"run_id": RUN, "agent": "agent_5_ads", "value": 0},
    {"run_id": RUN, "agent": "agent_5_ads", "value": 5},
    {"run_id": "x", "agent": "agent_5_ads", "value": 1},
    {"run_id": RUN, "agent": "agent_5_ads"},
])
def test_bad_ratings_are_rejected(client, body):
    assert client.post("/feedback/rating", json=body).status_code == 422


def test_ad_pick_endpoint_validates_and_stores(client):
    ok = client.post("/feedback/ad-pick", json={"run_id": RUN, "ad_copy_ref": "Meta", "chosen": "B"})
    assert ok.status_code == 200
    assert client.get("/feedback/summary").json()["ad_picks"] == [{"chosen": "B", "count": 1}]

    too_long = client.post("/feedback/ad-pick", json={"run_id": RUN, "ad_copy_ref": "x" * 500, "chosen": "B"})
    assert too_long.status_code == 422


def test_unknown_experiment_is_a_404(client):
    assert client.get("/experiments/nope").status_code == 404
    assert client.get(f"/experiments/{ADS_CRITIC}").status_code == 200


def test_feedback_routes_need_the_access_key_once_one_is_set(client, monkeypatch):
    monkeypatch.setattr(settings, "access_key", "secret123")
    assert client.get("/feedback/summary").status_code == 401
    assert client.post("/feedback/rating", json={"run_id": RUN, "agent": "agent_5_ads", "value": 1}).status_code == 401
    assert client.get(f"/experiments/{ADS_CRITIC}").status_code == 401


# -- pipeline start --------------------------------------------------------


class _CapturingGraph:
    def __init__(self):
        self.initial_state = None

    async def astream(self, initial_state, *_args, **_kwargs):
        self.initial_state = initial_state
        return
        yield  # makes this an async generator


def _start(client, monkeypatch):
    graph = _CapturingGraph()
    monkeypatch.setattr(main_mod, "graph", graph)
    client.post("/pipeline/start", json={"url": "https://acme.com"})
    return graph.initial_state


def test_experiments_off_means_every_run_keeps_the_critic_and_nothing_is_recorded(client, monkeypatch, db):
    monkeypatch.setattr(settings, "experiments_enabled", False)

    state = _start(client, monkeypatch)

    assert state["ads_critic_enabled"] is True
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM experiment_assignments").fetchone()[0] == 0


def test_experiments_on_records_the_assignment_and_passes_it_to_the_graph(client, monkeypatch, db):
    monkeypatch.setattr(settings, "experiments_enabled", True)

    seen = set()
    for _ in range(30):
        state = _start(client, monkeypatch)
        run_id = state["run_id"]
        variant = sqlite3.connect(db).execute(
            "SELECT variant FROM experiment_assignments WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        assert state["ads_critic_enabled"] == (variant == "critic_on")
        seen.add(variant)

    # 30 fair coin flips landing all one way has odds of about 1 in 500 million.
    assert seen == {"critic_on", "critic_off"}


def test_a_failed_assignment_write_falls_back_to_the_normal_run(client, monkeypatch, db):
    monkeypatch.setattr(settings, "experiments_enabled", True)

    def broken(*_a, **_k):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(fb, "record_assignment", broken)

    assert _start(client, monkeypatch)["ads_critic_enabled"] is True
    assert uuid.UUID(_start(client, monkeypatch)["run_id"])
