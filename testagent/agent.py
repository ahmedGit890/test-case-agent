"""The agent loop: ask the backend what to do, run the tool, feed the result back."""
from . import tools


class Agent:
    def __init__(self, backend, target, max_steps=10):
        self.backend = backend
        self.max_steps = max_steps
        # `target` (the system under test) is bound here, so the model
        # only ever chooses tools; it cannot run arbitrary code.
        self.tools = {
            "parse_requirement": tools.parse_requirement,
            "generate_boundary_cases": tools.generate_boundary_cases,
            "run_cases": lambda cases: tools.run_cases(target, cases),
            "summarize": tools.summarize,
        }
        self.trace = []

    def run(self, requirement):
        history = [{"role": "user", "content": requirement}]
        for _ in range(self.max_steps):
            action = self.backend.next_action(history)
            if "final" in action:
                self.trace.append(("final", action["final"]))
                return action["final"]
            name = action.get("tool")
            if name not in self.tools:
                return f"Stopped: backend asked for unknown tool {name!r}"
            result = self.tools[name](**action["args"])
            self.trace.append((name, result))
            history.append({"role": "tool", "tool": name, "result": result})
        return f"Stopped: exceeded {self.max_steps} steps"
