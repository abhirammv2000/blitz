"""Assigning runs to experiment variants, and the small amount of statistics
needed to read the results.

Assignment is a hash of the experiment name and run id, so a run always gets the
same variant and nothing has to be stored to make that true. The stats are
standard library only: a Wilson interval for a rate, and a pooled two-proportion
z-test for the difference between two rates.
"""

from __future__ import annotations

import hashlib
import math

ADS_CRITIC = "ads_critic"
ADS_CRITIC_VARIANTS = ("critic_on", "critic_off")

# Below this many rated runs in either variant, the numbers are shown but no
# verdict is given. A z-test on a handful of thumbs isn't worth trusting.
MIN_RATED_PER_VARIANT = 20


def assign(experiment: str, run_id: str, variants: tuple[str, ...]) -> str:
    """Pick a variant for this run. Same inputs always give the same answer."""
    if not variants:
        raise ValueError("variants must not be empty")
    digest = hashlib.sha256(f"{experiment}:{run_id}".encode()).digest()
    return variants[int.from_bytes(digest[:8], "big") % len(variants)]


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. (0, 0) when there is no data."""
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_p_value(k1: int, n1: int, k2: int, n2: int) -> float | None:
    """Two-sided p-value for whether two rates differ (pooled z-test).

    None when it can't be computed: an empty group, or both groups at 0% or 100%
    so there is no variance to test against.
    """
    if n1 <= 0 or n2 <= 0:
        return None
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (k1 / n1 - k2 / n2) / se
    return math.erfc(abs(z) / math.sqrt(2))


def verdict(variants: list[dict]) -> str:
    """One plain sentence about what the results say so far."""
    if len(variants) < 2:
        return "Only one variant has runs so far."
    thin = [v["variant"] for v in variants if v["rated"] < MIN_RATED_PER_VARIANT]
    if thin:
        return (
            f"Not enough ratings yet. Need at least {MIN_RATED_PER_VARIANT} rated runs "
            f"per variant, still short: {', '.join(thin)}."
        )
    a, b = variants[0], variants[1]
    p = two_proportion_p_value(a["up"], a["rated"], b["up"], b["rated"])
    if p is None:
        return "The two variants have identical results, so there is nothing to compare."
    if p < 0.05:
        return f"The difference is unlikely to be chance (p={p:.3f})."
    return f"No clear difference yet (p={p:.3f})."
