import unittest

from testagent import tools
from testagent.agent import Agent
from testagent.backend import MockBackend
from testagent.sut import (validate_name_length_buggy, validate_name_length_correct,
                           validate_status_buggy, validate_status_correct)

LENGTH_REQ = "name length must be between 3 and 20 inclusive"
ENUM_REQ = "status must be one of NEW, ACTIVE, CLOSED"


class ParsingTests(unittest.TestCase):
    def test_length_rule(self):
        self.assertEqual(
            tools.parse_requirement(LENGTH_REQ),
            {"field": "name", "lo": 3, "hi": 20, "inclusive": True, "kind": "length"},
        )

    def test_length_rule_is_not_mistaken_for_a_range_rule(self):
        rule = tools.parse_requirement(LENGTH_REQ)
        self.assertEqual(rule["field"], "name")  # not "length"

    def test_enum_rule(self):
        self.assertEqual(
            tools.parse_requirement(ENUM_REQ),
            {"kind": "enum", "field": "status", "values": ["NEW", "ACTIVE", "CLOSED"]},
        )

    def test_enum_rule_with_or_and_quotes(self):
        rule = tools.parse_requirement("colour must be one of 'red', 'green' or 'blue'")
        self.assertEqual(rule["values"], ["red", "green", "blue"])

    def test_enum_needs_two_values(self):
        self.assertIn("error", tools.parse_requirement("status must be one of ACTIVE"))

    def test_length_lower_bound_above_upper_bound_is_an_error(self):
        self.assertIn("error", tools.parse_requirement("name length must be between 9 and 3"))

    def test_range_rule_keeps_its_original_shape(self):
        rule = tools.parse_requirement("age must be between 18 and 60 inclusive")
        self.assertNotIn("kind", rule)


class CaseGenerationTests(unittest.TestCase):
    def test_length_boundary_cases(self):
        cases = tools.generate_boundary_cases(tools.parse_requirement(LENGTH_REQ))
        got = {len(c["input"]): c["expected"] for c in cases}
        self.assertEqual(got, {2: False, 3: True, 4: True, 19: True, 20: True, 21: False})

    def test_length_cases_never_use_negative_lengths(self):
        rule = tools.parse_requirement("code length must be between 0 and 5 inclusive")
        cases = tools.generate_boundary_cases(rule)
        self.assertTrue(all(len(c["input"]) >= 0 for c in cases))
        self.assertEqual(sorted(len(c["input"]) for c in cases), [0, 1, 4, 5, 6])

    def test_exclusive_length_bounds(self):
        rule = tools.parse_requirement("code length must be between 3 and 6")
        cases = {len(c["input"]): c["expected"] for c in tools.generate_boundary_cases(rule)}
        self.assertFalse(cases[3])
        self.assertTrue(cases[4])
        self.assertFalse(cases[6])

    def test_enum_cases_cover_every_value_and_reject_others(self):
        cases = tools.generate_boundary_cases(tools.parse_requirement(ENUM_REQ))
        accepted = [c["input"] for c in cases if c["expected"]]
        rejected = [c["input"] for c in cases if not c["expected"]]
        self.assertEqual(accepted, ["NEW", "ACTIVE", "CLOSED"])
        self.assertIn(tools.INVALID_VALUE, rejected)
        self.assertIn("", rejected)


class AgentOnNewRulesTests(unittest.TestCase):
    def test_correct_length_validator_passes(self):
        out = Agent(MockBackend(), validate_name_length_correct).run(LENGTH_REQ)
        self.assertEqual(out, "6/6 passed")

    def test_buggy_length_validator_is_caught(self):
        out = Agent(MockBackend(), validate_name_length_buggy).run(LENGTH_REQ)
        self.assertIn("5/6 passed", out)
        self.assertIn("FAIL name length=3", out)

    def test_correct_enum_validator_passes(self):
        out = Agent(MockBackend(), validate_status_correct).run(ENUM_REQ)
        self.assertEqual(out, "5/5 passed")

    def test_buggy_enum_validator_is_caught(self):
        out = Agent(MockBackend(), validate_status_buggy).run(ENUM_REQ)
        self.assertIn("4/5 passed", out)
        self.assertIn("FAIL status=CLOSED", out)


if __name__ == "__main__":
    unittest.main()
