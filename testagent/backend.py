"""The 'brain' of the agent.

A backend looks at the conversation history and returns the next action:
    {"tool": "<name>", "args": {...}}   call a tool
    {"final": "<text>"}                 stop and answer

MockBackend is a deterministic planner so the project runs offline and is
testable. To use a real LLM, implement the same `next_action(history)` method
(send the history and tool descriptions to the model, parse its tool call).
"""


class Backend:
    def next_action(self, history):
        raise NotImplementedError


class MockBackend(Backend):
    """Plans: parse -> generate -> run -> summarize -> final, reacting to errors."""

    def next_action(self, history):
        last = history[-1]
        if last["role"] == "user":
            return {"tool": "parse_requirement", "args": {"text": last["content"]}}

        tool, result = last["tool"], last["result"]
        if isinstance(result, dict) and "error" in result:
            return {"final": f"Stopped: {result['error']}"}
        if tool == "parse_requirement":
            return {"tool": "generate_boundary_cases", "args": {"rule": result}}
        if tool == "generate_boundary_cases":
            return {"tool": "run_cases", "args": {"cases": result}}
        if tool == "run_cases":
            return {"tool": "summarize", "args": {"results": result}}
        if tool == "summarize":
            return {"final": result["text"]}
        return {"final": f"Stopped: unknown tool {tool!r}"}
