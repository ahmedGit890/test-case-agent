import random
import unittest

from testagent.baselines import near_boundary_cases, partition_cases, random_cases
from testagent.tools import parse_requirement

RANGE = parse_requirement("age must be between 18 and 60 inclusive")
LENGTH = parse_requirement("name length must be between 3 and 20 inclusive")
ENUM = parse_requirement("status must be one of NEW, ACTIVE, CLOSED")


class PartitionTests(unittest.TestCase):
    def test_range_has_one_case_per_class(self):
        cases = partition_cases(RANGE)
        self.assertEqual([c["expected"] for c in cases], [False, True, False])
        self.assertEqual([c["input"] for c in cases], [8, 39, 70])

    def test_length_has_one_case_per_class(self):
        cases = partition_cases(LENGTH)
        self.assertEqual([len(c["input"]) for c in cases], [0, 11, 30])
        self.assertEqual([c["expected"] for c in cases], [False, True, False])

    def test_length_with_minimum_zero_has_no_too_short_class(self):
        rule = parse_requirement("code length must be between 0 and 5 inclusive")
        self.assertEqual(len(partition_cases(rule)), 2)

    def test_enum_has_one_valid_and_one_invalid_case(self):
        cases = partition_cases(ENUM)
        self.assertEqual([c["expected"] for c in cases], [True, False])


class RandomTests(unittest.TestCase):
    def test_same_seed_gives_same_cases(self):
        a = random_cases(RANGE, 10, random.Random(1))
        b = random_cases(RANGE, 10, random.Random(1))
        self.assertEqual(a, b)

    def test_different_seed_gives_different_cases(self):
        a = random_cases(RANGE, 10, random.Random(1))
        b = random_cases(RANGE, 10, random.Random(2))
        self.assertNotEqual(a, b)

    def test_requested_number_of_cases(self):
        self.assertEqual(len(random_cases(RANGE, 7, random.Random(0))), 7)
        self.assertEqual(len(near_boundary_cases(LENGTH, 7, random.Random(0))), 7)

    def test_expected_values_follow_the_requirement(self):
        for case in random_cases(RANGE, 50, random.Random(3)):
            self.assertEqual(case["expected"], 18 <= case["input"] <= 60)

    def test_near_boundary_values_stay_within_three_of_a_bound(self):
        for case in near_boundary_cases(RANGE, 200, random.Random(4)):
            v = case["input"]
            self.assertTrue(min(abs(v - 18), abs(v - 60)) <= 3)

    def test_length_cases_are_never_negative(self):
        for case in random_cases(LENGTH, 200, random.Random(5)):
            self.assertGreaterEqual(len(case["input"]), 0)
        for case in near_boundary_cases(LENGTH, 200, random.Random(5)):
            self.assertGreaterEqual(len(case["input"]), 0)

    def test_enum_rules_are_rejected_by_random_baselines(self):
        with self.assertRaises(ValueError):
            random_cases(ENUM, 5, random.Random(0))
        with self.assertRaises(ValueError):
            near_boundary_cases(ENUM, 5, random.Random(0))


if __name__ == "__main__":
    unittest.main()
