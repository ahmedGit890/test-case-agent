"""Tools the agent can call. Each takes and returns plain JSON-like data.

Supported requirement sentences (case-insensitive):
  range   "age must be between 18 and 60 inclusive"
  length  "name length must be between 3 and 20 inclusive"
  enum    "status must be one of NEW, ACTIVE, CLOSED"
Without the word "inclusive", range and length bounds are treated as exclusive.
"""
import re

RULE = re.compile(  # range rule (kept under its original name)
    r"(?P<field>\w+)\s+must\s+be\s+between\s+(?P<lo>-?\d+)\s+and\s+(?P<hi>-?\d+)"
    r"(?P<incl>\s+inclusive)?",
    re.IGNORECASE,
)
LENGTH = re.compile(
    r"(?P<field>\w+)\s+length\s+must\s+be\s+between\s+(?P<lo>\d+)\s+and\s+(?P<hi>\d+)"
    r"(?P<incl>\s+inclusive)?",
    re.IGNORECASE,
)
ENUM = re.compile(r"(?P<field>\w+)\s+must\s+be\s+one\s+of\s+(?P<values>[^.\n]+)", re.IGNORECASE)

INVALID_VALUE = "__invalid__"  # a value no enum rule should accept


def _bounds_rule(m, kind):
    lo, hi = int(m["lo"]), int(m["hi"])
    if lo > hi:
        return {"error": f"lower bound {lo} is greater than upper bound {hi}"}
    rule = {"field": m["field"], "lo": lo, "hi": hi, "inclusive": bool(m["incl"])}
    if kind != "range":
        rule["kind"] = kind  # plain range rules carry no "kind" key
    return rule


def parse_requirement(text):
    """Turn a requirement sentence into a rule dict, or {"error": ...}."""
    # Order matters: "name length must be between ..." also looks like a range rule.
    m = LENGTH.search(text)
    if m:
        return _bounds_rule(m, "length")
    m = ENUM.search(text)
    if m:
        pieces = re.split(r",|\bor\b", m["values"])
        values = [p.strip().strip("'\"") for p in pieces]
        values = [v for v in values if v]
        if len(values) < 2:
            return {"error": f"need at least two allowed values in: {text!r}"}
        return {"kind": "enum", "field": m["field"], "values": values}
    m = RULE.search(text)
    if m:
        return _bounds_rule(m, "range")
    return {"error": f"could not parse a rule from: {text!r}"}


def is_valid(rule, value):
    """The requirement itself: is `value` allowed by the parsed rule?"""
    kind = rule.get("kind", "range")
    if kind == "enum":
        return value in rule["values"]
    number = len(value) if kind == "length" else value
    if rule["inclusive"]:
        return rule["lo"] <= number <= rule["hi"]
    return rule["lo"] < number < rule["hi"]


def case_for(rule, size):
    """Build one test case. `size` is the number itself (range) or the string length."""
    if rule.get("kind") == "length":
        value, label = "a" * size, f"{rule['field']} length={size}"
    else:
        value, label = size, f"{rule['field']}={size}"
    return {"name": label, "input": value, "expected": is_valid(rule, value)}


def generate_boundary_cases(rule):
    """Boundary value analysis: just below, on and just above each bound.

    For an "allowed values" rule: every allowed value, plus values that must be rejected.
    """
    kind = rule.get("kind", "range")
    if kind == "enum":
        cases = [{"name": f"{rule['field']}={v}", "input": v, "expected": True}
                 for v in rule["values"]]
        for bad in (INVALID_VALUE, ""):
            cases.append({"name": f"{rule['field']}={bad!r}", "input": bad,
                          "expected": is_valid(rule, bad)})
        return cases
    lo, hi = rule["lo"], rule["hi"]
    sizes = {lo - 1, lo, lo + 1, hi - 1, hi, hi + 1}
    if kind == "length":
        sizes = {s for s in sizes if s >= 0}  # a string cannot have negative length
    return [case_for(rule, s) for s in sorted(sizes)]


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
