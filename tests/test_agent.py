import unittest

from testagent import tools
from testagent.agent import Agent
from testagent.backend import MockBackend
from testagent.sut import validate_age_buggy, validate_age_correct

REQ = "age must be between 18 and 60 inclusive"


class ToolTests(unittest.TestCase):
    def test_parse_inclusive(self):
        self.assertEqual(
            tools.parse_requirement(REQ),
            {"field": "age", "lo": 18, "hi": 60, "inclusive": True},
        )

    def test_parse_exclusive_by_default(self):
        rule = tools.parse_requirement("score must be between 0 and 10")
        self.assertFalse(rule["inclusive"])

    def test_parse_errors(self):
        self.assertIn("error", tools.parse_requirement("be nice to users"))
        self.assertIn("error", tools.parse_requirement("x must be between 9 and 3"))

    def test_boundary_cases_inclusive(self):
        rule = tools.parse_requirement(REQ)
        expected = {c["input"]: c["expected"] for c in tools.generate_boundary_cases(rule)}
        self.assertEqual(
            expected,
            {17: False, 18: True, 19: True, 59: True, 60: True, 61: False},
        )

    def test_boundary_cases_exclusive(self):
        rule = tools.parse_requirement("score must be between 0 and 10")
        expected = {c["input"]: c["expected"] for c in tools.generate_boundary_cases(rule)}
        self.assertFalse(expected[0])
        self.assertTrue(expected[1])
        self.assertFalse(expected[10])

    def test_crash_counts_as_failure(self):
        def boom(_):
            raise ValueError("bad")

        res = tools.run_cases(boom, [{"name": "x", "input": 1, "expected": True}])
        self.assertFalse(res[0]["passed"])
        self.assertIn("ValueError", res[0]["error"])


class AgentTests(unittest.TestCase):
    def test_correct_implementation_passes(self):
        out = Agent(MockBackend(), validate_age_correct).run(REQ)
        self.assertEqual(out, "6/6 passed")

    def test_buggy_implementation_is_caught(self):
        out = Agent(MockBackend(), validate_age_buggy).run(REQ)
        self.assertIn("5/6 passed", out)
        self.assertIn("FAIL age=18: expected True, got False", out)

    def test_unparseable_requirement_stops_cleanly(self):
        out = Agent(MockBackend(), validate_age_correct).run("be nice")
        self.assertTrue(out.startswith("Stopped:"))

    def test_step_limit(self):
        class Looping:
            def next_action(self, history):
                return {"tool": "parse_requirement", "args": {"text": REQ}}

        out = Agent(Looping(), validate_age_correct, max_steps=3).run(REQ)
        self.assertIn("exceeded 3 steps", out)

    def test_unknown_tool_rejected(self):
        class Rogue:
            def next_action(self, history):
                return {"tool": "delete_everything", "args": {}}

        out = Agent(Rogue(), validate_age_correct).run(REQ)
        self.assertIn("unknown tool", out)


if __name__ == "__main__":
    unittest.main()
