# Test Case Agent

A small tool-using agent that turns a plain-English requirement into
boundary-value test cases, runs them against a system under test, and reports
failures.

```
"age must be between 18 and 60 inclusive"
  -> parse_requirement -> generate_boundary_cases -> run_cases -> summarize
```

The standard library is the only dependency. No API key is needed.

## Run

```
python -m unittest discover -s tests -t .
python demo.py
```

Demo output against an implementation with a planted off-by-one bug:

```
5/6 passed
  FAIL age=18: expected True, got False
```

## Design

- `testagent/agent.py`: the loop. Ask the backend for an action, execute the
  tool, feed the result back, stop on a final answer or a step limit.
  The model can only pick from a fixed tool registry, never run arbitrary code.
- `testagent/tools.py`: requirement parsing, boundary value analysis,
  test execution (crashes count as failures), result summary.
- `testagent/backend.py`: the decision-maker. `MockBackend` is a deterministic
  planner so runs are repeatable and unit-testable. Any LLM can be plugged in
  by implementing `next_action(history)`.
- Safety behaviours covered by tests: unparseable requirements, unknown
  tools, runaway loops.

## Limitations

- Only numeric "between X and Y" rules are parsed.
- The mock backend follows a fixed plan. It is not a language model.

## Roadmap (my next steps)

- [ ] Add a real LLM backend (tool-calling API) and compare it with the mock
- [ ] Support more rule types: string length, regex, enums, required fields
- [ ] Equivalence partitioning and pairwise combinations for multi-field rules
- [ ] Generate Robot Framework test cases from the produced cases
- [ ] Measure: how many planted bugs does the agent catch, and which does it miss?
