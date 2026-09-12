"""Tests for the daily pipeline-run cap.

The thing that matters here is the race: two requests arriving at once for
the last slot under the cap must not both get through.
"""

from __future__ import annotations

import asyncio

import pytest

from app.db.usage import check_and_increment_daily_cap, init_usage_table, runs_today


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Use a throwaway database file so we don't touch the real blitz.db."""
    import app.db.usage as usage

    monkeypatch.setattr(usage, "_DB_PATH", tmp_path / "usage-test.db")
    init_usage_table()


def test_cap_of_zero_means_unlimited():
    for _ in range(50):
        assert check_and_increment_daily_cap(0) is True
    # Nothing was counted, since an unlimited cap never touches the table.
    assert runs_today() == 0


def test_calls_under_the_cap_are_allowed():
    assert check_and_increment_daily_cap(3) is True
    assert check_and_increment_daily_cap(3) is True
    assert check_and_increment_daily_cap(3) is True
    assert runs_today() == 3


def test_a_call_at_the_cap_is_refused_and_not_counted():
    check_and_increment_daily_cap(2)
    check_and_increment_daily_cap(2)

    assert check_and_increment_daily_cap(2) is False
    assert runs_today() == 2, "a refused call should not consume a slot"


def test_refused_calls_stay_refused_until_the_next_day():
    check_and_increment_daily_cap(1)

    assert check_and_increment_daily_cap(1) is False
    assert check_and_increment_daily_cap(1) is False


async def test_concurrent_requests_for_the_last_slot_dont_both_win():
    """The whole point of the atomic upsert: two requests racing for slot 3
    of a cap of 3 must not both succeed."""
    check_and_increment_daily_cap(3)
    check_and_increment_daily_cap(3)

    results = await asyncio.gather(
        asyncio.to_thread(check_and_increment_daily_cap, 3),
        asyncio.to_thread(check_and_increment_daily_cap, 3),
    )

    assert sorted(results) == [False, True]
    assert runs_today() == 3
