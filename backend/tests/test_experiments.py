"""Assignment and statistics for the live experiments. Pure logic, no database."""

from __future__ import annotations

import math
import uuid

import pytest

from app.experiments import (
    MIN_RATED_PER_VARIANT,
    assign,
    two_proportion_p_value,
    verdict,
    wilson_interval,
)

VARIANTS = ("critic_on", "critic_off")


def test_assignment_is_stable_for_the_same_run():
    run_id = str(uuid.uuid4())
    assert assign("ads_critic", run_id, VARIANTS) == assign("ads_critic", run_id, VARIANTS)


def test_assignment_splits_roughly_evenly():
    ids = [str(uuid.uuid4()) for _ in range(4000)]
    on = sum(assign("ads_critic", i, VARIANTS) == "critic_on" for i in ids)
    assert 0.45 < on / len(ids) < 0.55


def test_different_experiments_do_not_assign_in_lockstep():
    ids = [str(uuid.uuid4()) for _ in range(500)]
    same = sum(assign("ads_critic", i, VARIANTS) == assign("other", i, VARIANTS) for i in ids)
    assert 0.35 < same / len(ids) < 0.65


def test_assign_needs_variants():
    with pytest.raises(ValueError):
        assign("ads_critic", "run", ())


def test_wilson_interval_for_eight_of_ten():
    low, high = wilson_interval(8, 10)
    assert low == pytest.approx(0.4902, abs=1e-3)
    assert high == pytest.approx(0.9433, abs=1e-3)


def test_wilson_interval_with_no_data_and_at_the_edges():
    assert wilson_interval(0, 0) == (0.0, 0.0)
    low, high = wilson_interval(0, 20)
    assert low == 0.0 and 0 < high < 0.2
    low, high = wilson_interval(20, 20)
    assert high == 1.0 and 0.8 < low < 1.0


def test_p_value_for_a_z_of_two():
    # 30/50 against 20/50: pooled rate 0.5, standard error 0.1, z = 2.
    assert two_proportion_p_value(30, 50, 20, 50) == pytest.approx(math.erfc(2 / math.sqrt(2)))
    assert two_proportion_p_value(30, 50, 20, 50) == pytest.approx(0.0455, abs=1e-4)


def test_p_value_is_symmetric_and_one_for_equal_rates():
    assert two_proportion_p_value(20, 50, 30, 50) == pytest.approx(two_proportion_p_value(30, 50, 20, 50))
    assert two_proportion_p_value(25, 50, 25, 50) == pytest.approx(1.0)


def test_p_value_is_none_when_it_cannot_be_computed():
    assert two_proportion_p_value(0, 0, 5, 10) is None
    assert two_proportion_p_value(10, 10, 10, 10) is None
    assert two_proportion_p_value(0, 10, 0, 10) is None


def _v(name, up, rated):
    return {"variant": name, "up": up, "rated": rated}


def test_verdict_holds_back_until_there_are_enough_ratings():
    text = verdict([_v("critic_on", 9, 10), _v("critic_off", 2, 10)])
    assert "Not enough ratings" in text
    assert str(MIN_RATED_PER_VARIANT) in text


def test_verdict_reports_a_real_difference_and_a_null_one():
    assert "unlikely to be chance" in verdict([_v("critic_on", 40, 50), _v("critic_off", 20, 50)])
    assert "No clear difference" in verdict([_v("critic_on", 26, 50), _v("critic_off", 24, 50)])


def test_verdict_with_one_variant():
    assert "Only one variant" in verdict([_v("critic_on", 5, 5)])
