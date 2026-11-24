"""Other ways to choose tests, used as fair baselines for boundary-value testing.

  partition_cases      equivalence partitioning: one representative per class
  random_cases         uniform random values around the valid range
  near_boundary_cases  random values within +-3 of a bound (a stronger random baseline)

All return the same case dicts as tools.generate_boundary_cases, so any of them
can be scored with mutation.mutation_report.
"""
from .tools import INVALID_VALUE, case_for, is_valid


def _is_enum(rule):
    return rule.get("kind") == "enum"


def partition_cases(rule):
    """Equivalence partitioning: one test from each class (below, inside, above)."""
    if _is_enum(rule):
        valid, field = rule["values"][0], rule["field"]
        return [
            {"name": f"{field}={valid}", "input": valid, "expected": True},
            {"name": f"{field}={INVALID_VALUE!r}", "input": INVALID_VALUE,
             "expected": is_valid(rule, INVALID_VALUE)},
        ]
    lo, hi = rule["lo"], rule["hi"]
    below = lo - 10
    if rule.get("kind") == "length":
        below = 0 if lo > 0 else None  # no shorter-than-minimum class when the minimum is 0
    sizes = [below, (lo + hi) // 2, hi + 10]
    unique = dict.fromkeys(s for s in sizes if s is not None)
    return [case_for(rule, s) for s in unique]


def random_cases(rule, n, rng):
    """`n` uniform random values from well below the range to well above it."""
    if _is_enum(rule):
        raise ValueError("random sizes do not apply to an allowed-values rule")
    low, high = rule["lo"] - 40, rule["hi"] + 40
    if rule.get("kind") == "length":
        low = 0
    return [case_for(rule, rng.randint(low, high)) for _ in range(n)]


def near_boundary_cases(rule, n, rng):
    """`n` random values within +-3 of the lower or upper bound."""
    if _is_enum(rule):
        raise ValueError("boundaries do not apply to an allowed-values rule")
    sizes = []
    for _ in range(n):
        size = rng.choice((rule["lo"], rule["hi"])) + rng.randint(-3, 3)
        if rule.get("kind") == "length":
            size = max(0, size)
        sizes.append(size)
    return [case_for(rule, s) for s in sizes]
