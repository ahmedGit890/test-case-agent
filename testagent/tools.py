"""Tools the agent can call. Each takes and returns plain JSON-like data."""
import re

RULE = re.compile(
    r"(?P<field>\w+)\s+must\s+be\s+between\s+(?P<lo>-?\d+)\s+and\s+(?P<hi>-?\d+)"
    r"(?P<incl>\s+inclusive)?",
    re.IGNORECASE,
)


def parse_requirement(text):
    """Extract a numeric range rule from a requirement sentence."""
    m = RULE.search(text)
    if not m:
        return {"error": f"could not parse a range rule from: {text!r}"}
    lo, hi = int(m["lo"]), int(m["hi"])
    if lo > hi:
        return {"error": f"lower bound {lo} is greater than upper bound {hi}"}
    return {
        "field": m["field"],
        "lo": lo,
        "hi": hi,
        # Without the word "inclusive" we treat the bounds as exclusive.
        "inclusive": bool(m["incl"]),
    }


def generate_boundary_cases(rule):
    """Boundary value analysis: values just below, on and just above each bound."""
    lo, hi, inc = rule["lo"], rule["hi"], rule["inclusive"]

    def valid(v):
        return lo <= v <= hi if inc else lo < v < hi

    values = sorted({lo - 1, lo, lo + 1, hi - 1, hi, hi + 1})
    return [
        {"name": f"{rule['field']}={v}", "input": v, "expected": valid(v)}
        for v in values
    ]


def run_cases(target, cases):
    """Run each case against the callable under test and record the outcome."""
    results = []
    for case in cases:
        try:
            actual = bool(target(case["input"]))
            error = None
        except Exception as exc:  # a crash is a failed test, not an agent crash
            actual, error = None, repr(exc)
        results.append({**case, "actual": actual, "error": error,
                        "passed": error is None and actual == case["expected"]})
    return results


def summarize(results):
    failed = [r for r in results if not r["passed"]]
    lines = [f"{len(results) - len(failed)}/{len(results)} passed"]
    for r in failed:
        got = r["error"] or r["actual"]
        lines.append(f"  FAIL {r['name']}: expected {r['expected']}, got {got}")
    return {"passed": not failed, "text": "\n".join(lines)}
