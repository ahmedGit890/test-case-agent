import random
import unittest

from testagent.baselines import partition_cases
from testagent.mutation import _fails, generate_mutants, mutation_report
from testagent.sut import (validate_age_buggy, validate_age_correct,
                           validate_name_length_correct, validate_status_correct)
from testagent.tools import generate_boundary_cases, is_valid, parse_requirement

RULE = parse_requirement("age must be between 18 and 60 inclusive")
BVA = generate_boundary_cases(RULE)


def make_cases(values):
    return [{"name": f"age={v}", "input": v, "expected": is_valid(RULE, v)} for v in values]


class MutantGenerationTests(unittest.TestCase):
    def test_generates_expected_number_of_mutants(self):
        # 2 comparison operators x 2 swaps + 2 constants x 2 changes = 8
        self.assertEqual(len(generate_mutants(validate_age_correct)), 8)

    def test_mutant_descriptions_are_unique(self):
        descriptions = [m.description for m in generate_mutants(validate_age_correct)]
        self.assertEqual(len(descriptions), len(set(descriptions)))

    def test_original_function_is_unchanged_by_mutation(self):
        generate_mutants(validate_age_correct)
        self.assertTrue(validate_age_correct(18))
        self.assertTrue(validate_age_correct(60))
        self.assertFalse(validate_age_correct(17))

    def test_mutants_really_differ_from_original(self):
        mutants = generate_mutants(validate_age_correct)
        differing = [
            m for m in mutants
            if any(m.func(x) != validate_age_correct(x) for x in range(-50, 151))
        ]
        self.assertEqual(len(differing), len(mutants))

    def test_boolean_and_not_operators_are_mutated(self):
        def check(x):
            return not (x > 0 and x < 10)

        descriptions = [m.description for m in generate_mutants(check)]
        self.assertTrue(any("and -> or" in d for d in descriptions))
        self.assertTrue(any("removed 'not'" in d for d in descriptions))


class OperatorTests(unittest.TestCase):
    def descriptions(self, func):
        return [m.description for m in generate_mutants(func)]

    def test_arithmetic_operators_are_mutated(self):
        def f(x):
            return x + 1 > 5

        d = self.descriptions(f)
        self.assertTrue(any("+ -> -" in s for s in d))
        # 2 comparison swaps + 1 arithmetic swap + 2 changes for each of 2 constants
        self.assertEqual(len(d), 7)

    def test_multiplication_and_floor_division_swap(self):
        def f(x):
            return x * 2 // 3 > 0

        d = self.descriptions(f)
        self.assertTrue(any("* -> //" in s for s in d))
        self.assertTrue(any("// -> *" in s for s in d))

    def test_membership_is_flipped(self):
        d = self.descriptions(validate_status_correct)
        self.assertTrue(any("in -> not in" in s for s in d))

    def test_string_constants_are_changed(self):
        d = self.descriptions(validate_status_correct)
        self.assertTrue(any("'NEW' -> 'NEWx'" in s for s in d))
        # 1 membership flip + 3 string constants
        self.assertEqual(len(d), 4)

    def test_docstrings_are_not_mutated(self):
        def with_doc(x):
            """Not code."""
            return x > 5

        def without_doc(x):
            return x > 5

        self.assertEqual(len(generate_mutants(with_doc)), len(generate_mutants(without_doc)))

    def test_string_mutants_get_their_own_behaviour(self):
        mutants = {m.description: m.func for m in generate_mutants(validate_status_correct)}
        changed = next(f for d, f in mutants.items() if "'ACTIVE' -> 'ACTIVEx'" in d)
        self.assertFalse(changed("ACTIVE"))
        self.assertTrue(changed("NEW"))


class RuleKindScoringTests(unittest.TestCase):
    def test_length_boundary_tests_kill_every_mutant(self):
        rule = parse_requirement("name length must be between 3 and 20 inclusive")
        report = mutation_report(validate_name_length_correct, generate_boundary_cases(rule),
                                 domain=["a" * n for n in range(0, 41)])
        self.assertEqual(report.total, 8)
        self.assertEqual(report.score, 1.0)

    def test_enum_boundary_tests_kill_every_mutant(self):
        rule = parse_requirement("status must be one of NEW, ACTIVE, CLOSED")
        report = mutation_report(validate_status_correct, generate_boundary_cases(rule),
                                 domain=["NEW", "ACTIVE", "CLOSED", "OLD", "", "x"])
        self.assertEqual(report.total, 4)
        self.assertEqual(report.score, 1.0)

    def test_enum_partitioning_misses_the_values_it_did_not_try(self):
        rule = parse_requirement("status must be one of NEW, ACTIVE, CLOSED")
        report = mutation_report(validate_status_correct, partition_cases(rule),
                                 domain=["NEW", "ACTIVE", "CLOSED", "OLD", "", "x"])
        self.assertEqual(report.score, 0.5)
        self.assertEqual(len(report.survivors), 2)

    def test_range_partitioning_is_weaker_than_boundary_values(self):
        rule = parse_requirement("age must be between 18 and 60 inclusive")
        bva = mutation_report(validate_age_correct, generate_boundary_cases(rule)).score
        ep = mutation_report(validate_age_correct, partition_cases(rule)).score
        self.assertLess(ep, bva)


class ScoringTests(unittest.TestCase):
    def test_boundary_tests_kill_every_mutant(self):
        report = mutation_report(validate_age_correct, BVA)
        self.assertTrue(report.original_passes)
        self.assertEqual(report.killed, report.total - report.equivalent)
        self.assertEqual(report.score, 1.0)
        self.assertEqual(report.survivors, [])

    def test_weak_tests_leave_survivors(self):
        report = mutation_report(validate_age_correct, make_cases([30, 40, 50]))
        self.assertLess(report.score, 1.0)
        self.assertTrue(report.survivors)

    def test_no_tests_kill_nothing(self):
        report = mutation_report(validate_age_correct, [])
        self.assertEqual(report.killed, 0)

    def test_equivalent_mutants_are_excluded_from_the_score(self):
        def small(x):
            return x < 1000  # over the default domain (-50..150), 1000 -> 999 changes nothing

        cases = [{"name": "x=5", "input": 5, "expected": True},
                 {"name": "x=2000", "input": 2000, "expected": False}]
        report = mutation_report(small, cases)
        self.assertGreater(report.equivalent, 0)
        self.assertLess(report.equivalent, report.total)

    def test_tests_that_fail_on_the_original_are_flagged(self):
        report = mutation_report(validate_age_buggy, BVA)
        self.assertFalse(report.original_passes)

    def test_a_crash_counts_as_a_failing_test(self):
        def boom(_):
            raise ZeroDivisionError

        self.assertTrue(_fails(boom, {"name": "x", "input": 1, "expected": True}))

    def test_a_wrong_answer_counts_as_a_failing_test(self):
        case = {"name": "x", "input": 1, "expected": True}
        self.assertTrue(_fails(lambda x: False, case))
        self.assertFalse(_fails(lambda x: True, case))

    def test_boundary_tests_beat_random_tests_of_the_same_size(self):
        bva = mutation_report(validate_age_correct, BVA).score
        scores = []
        for seed in range(100):
            rng = random.Random(seed)
            cases = make_cases([rng.randint(-50, 150) for _ in BVA])
            scores.append(mutation_report(validate_age_correct, cases).score)
        self.assertGreater(bva, sum(scores) / len(scores))


if __name__ == "__main__":
    unittest.main()
