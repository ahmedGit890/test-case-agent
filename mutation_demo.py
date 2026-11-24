"""How good are different ways of choosing tests? Score them with mutation testing.

For each validator we compare boundary-value tests (what the agent generates)
with equivalence partitioning and two random baselines. A higher mutation score
means the tests catch more of the deliberately wrong versions of the code.
"""
import random

from testagent.baselines import near_boundary_cases, partition_cases, random_cases
from testagent.mutation import mutation_report
from testagent.sut import (validate_age_correct, validate_name_length_correct,
                           validate_status_correct)
from testagent.tools import generate_boundary_cases, parse_requirement

TRIALS = 300

VALIDATORS = [
    ("age 18..60", "age must be between 18 and 60 inclusive",
     validate_age_correct, range(-50, 151)),
    ("name length 3..20", "name length must be between 3 and 20 inclusive",
     validate_name_length_correct, ["a" * n for n in range(0, 41)]),
    ("status in {NEW, ACTIVE, CLOSED}", "status must be one of NEW, ACTIVE, CLOSED",
     validate_status_correct, ["NEW", "ACTIVE", "CLOSED", "OLD", "", "x"]),
]


def averaged(make_cases, func, domain):
    scores = [mutation_report(func, make_cases(random.Random(seed)), domain).score
              for seed in range(TRIALS)]
    perfect = sum(s == 1.0 for s in scores) / TRIALS
    return sum(scores) / TRIALS, perfect


def main():
    for label, requirement, func, domain in VALIDATORS:
        rule = parse_requirement(requirement)
        bva = generate_boundary_cases(rule)
        ep = partition_cases(rule)
        base = mutation_report(func, bva, domain)
        print(f"\n{label}: {base.total} mutants, {base.equivalent} equivalent (ignored)")
        print(f"  boundary-value ({len(bva)} tests):     {base.score:4.0%}  survivors: {base.survivors or 'none'}")
        ep_report = mutation_report(func, ep, domain)
        print(f"  equivalence partitioning ({len(ep)}):    {ep_report.score:4.0%}  survivors: {len(ep_report.survivors)}")
        if rule.get("kind") == "enum":
            continue  # random baselines need a numeric size to vary
        n = len(bva)
        mean, perfect = averaged(lambda r: random_cases(rule, n, r), func, domain)
        print(f"  random, uniform ({n}):             {mean:4.0%} mean, 100% in {perfect:.0%} of trials")
        mean, perfect = averaged(lambda r: near_boundary_cases(rule, n, r), func, domain)
        print(f"  random, near boundary ({n}):       {mean:4.0%} mean, 100% in {perfect:.0%} of trials")


if __name__ == "__main__":
    main()
