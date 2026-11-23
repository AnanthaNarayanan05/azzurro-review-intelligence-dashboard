"""Small, dependency-free statistics helpers (means, proportions, 95% intervals).

Normal-approximation intervals are used. They are reasonable once each group has about 30 or more
observations, which is also the minimum sample the trend and comparison code insists on.
"""

import math

Z_95 = 1.96


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def sample_variance(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    centre = sum(values) / len(values)
    return sum((v - centre) ** 2 for v in values) / (len(values) - 1)


def mean_interval(values: list[float]) -> tuple[float, float] | None:
    """95% interval for a mean, or None when it cannot be estimated (fewer than 2 values)."""
    variance = sample_variance(values)
    if variance is None:
        return None
    centre = sum(values) / len(values)
    margin = Z_95 * math.sqrt(variance / len(values))
    return centre - margin, centre + margin


def difference_of_means(recent: list[float], previous: list[float]) -> dict | None:
    """Welch-style difference (recent - previous) with a 95% interval."""
    var_recent, var_previous = sample_variance(recent), sample_variance(previous)
    if var_recent is None or var_previous is None:
        return None
    diff = sum(recent) / len(recent) - sum(previous) / len(previous)
    margin = Z_95 * math.sqrt(var_recent / len(recent) + var_previous / len(previous))
    return {"difference": diff, "ci_low": diff - margin, "ci_high": diff + margin}


def difference_of_proportions(
    recent_hits: int, recent_n: int, previous_hits: int, previous_n: int
) -> dict | None:
    """Difference (recent - previous) of two proportions with a 95% interval."""
    if recent_n == 0 or previous_n == 0:
        return None
    p_recent, p_previous = recent_hits / recent_n, previous_hits / previous_n
    diff = p_recent - p_previous
    margin = Z_95 * math.sqrt(
        p_recent * (1 - p_recent) / recent_n + p_previous * (1 - p_previous) / previous_n
    )
    return {"difference": diff, "ci_low": diff - margin, "ci_high": diff + margin}


def excludes_zero(interval: dict) -> bool:
    return interval["ci_low"] > 0 or interval["ci_high"] < 0


def round_or_none(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)
