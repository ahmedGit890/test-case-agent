"""Run the agent against a correct and a buggy implementation."""
from testagent.agent import Agent
from testagent.backend import MockBackend
from testagent.sut import validate_age_buggy, validate_age_correct

REQUIREMENT = "age must be between 18 and 60 inclusive"

for label, target in [("correct", validate_age_correct), ("buggy", validate_age_buggy)]:
    agent = Agent(MockBackend(), target)
    print(f"--- {label} implementation ---")
    print(agent.run(REQUIREMENT))
    print("tool calls:", " -> ".join(name for name, _ in agent.trace))
    print()
