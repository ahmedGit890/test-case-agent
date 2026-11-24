# Test Case Agent

![tests](https://github.com/ahmedGit890/test-case-agent/actions/workflows/tests.yml/badge.svg)

A small tool-using agent that turns a plain-English requirement into
boundary-value test cases, runs them against a system under test, and reports
failures. A mutation-testing module then measures how good those tests are.

```
"age must be between 18 and 60 inclusive"
  -> parse_requirement -> generate_boundary_cases -> run_cases -> summarize
```

The standard library is the only dependency. No API key is needed.

## Run

```
python -m unittest discover -s tests -t .
python demo.py             # agent against a validator with a planted bug
python mutation_demo.py    # compare test-selection strategies by mutation score
```

Demo output against an implementation with a planted off-by-one bug:

```
5/6 passed
  FAIL age=18: expected True, got False
```

## Requirement types

| Sentence | Cases generated |
|---|---|
| `age must be between 18 and 60 inclusive` | values just below, on and just above each bound |
| `name length must be between 3 and 20 inclusive` | strings whose length is just below, on and just above each bound |
| `status must be one of NEW, ACTIVE, CLOSED` | every allowed value, plus values that must be rejected |

Without the word "inclusive", bounds are treated as exclusive.

## Design

- `testagent/agent.py`: the loop. Ask the backend for an action, execute the
  tool, feed the result back, stop on a final answer or a step limit.
  The model can only pick from a fixed tool registry, never run arbitrary code.
- `testagent/tools.py`: requirement parsing, boundary value analysis,
  test execution (crashes count as failures), result summary.
- `testagent/backend.py`: the decision-maker. `MockBackend` is a deterministic
  planner so runs are repeatable and unit-testable. Any LLM can be plugged in
  by implementing `next_action(history)`.
- `testagent/baselines.py`: other ways to pick tests (equivalence partitioning,
  uniform random, random near the boundaries) used as comparison baselines.
- `testagent/mutation.py`: mutation testing, described below.
- Safety behaviours covered by tests: unparseable requirements, unknown
  tools, runaway loops.

## Measuring the tests: mutation testing

How good are the generated tests? `testagent/mutation.py` makes small wrong
copies ("mutants") of the function under test and counts how many the tests
catch. That share is the mutation score. Mutation operators:

- comparison swaps (`<`, `<=`, `>`, `>=`, `==`, `!=`) and `in` / `not in`
- integer constants changed by +1 and -1; string constants extended
- arithmetic swaps (`+` and `-`, `*` and `//`), `and` / `or`, removed `not`

Changes that cannot alter behaviour ("equivalent mutants") are found by
comparing outputs over a sample domain and are left out of the score.
Docstrings are not mutated.

```
python mutation_demo.py
```

Results (300 trials for the random strategies, same number of tests as the
boundary-value set):

| Validator | Mutants | Boundary-value | Equivalence partitioning | Random, uniform | Random, near boundary |
|---|---|---|---|---|---|
| age 18..60 | 8 | **100%** (6 tests) | 25% (3 tests) | 28% | 52% |
| name length 3..20 | 8 | **100%** (6 tests) | 25% (3 tests) | 31% | 52% |
| status in {NEW, ACTIVE, CLOSED} | 4 | **100%** (5 tests) | 50% (2 tests) | n/a | n/a |

Reading the result: boundary-value tests catch every mutant here, because each
mutant changes behaviour exactly at a bound or at one allowed value. Equivalence
partitioning picks one value per class, so it misses off-by-one mutants. Random
near the boundaries does better than uniform random but never reached 100% in
any trial with six tests.

**Caveats:**
- These are three tiny validators with 4 to 8 mutants each, so the scores are
  coarse (a single mutant moves a score by 12 to 25 points).
- Most mutants are off-by-one changes, which boundary-value tests are designed
  to catch. A mutant set with more varied faults could narrow the gap.
- Equivalent-mutant detection depends on the sample domain chosen.
- Mutation works on one self-contained single-argument function and
  first-order (one change at a time) mutants only.

## Limitations

- Only the three requirement sentences above are parsed (no regex, required
  fields, or multi-field rules).
- Enumeration cases do not test case sensitivity, because the requirement
  does not say whether it matters.
- The mock backend follows a fixed plan. It is not a language model.

## Roadmap (my next steps)

- [ ] Add a real LLM backend (tool-calling API) and compare it with the mock
- [ ] Multi-field rules and pairwise combinations
- [ ] Generate Robot Framework test cases from the produced cases
- [ ] Second-order mutants and a larger, more varied mutant set
- [x] Measure how many planted bugs the generated tests catch (mutation score)
- [x] More rule types: string length and allowed values
- [x] Baselines: equivalence partitioning and random-near-boundary tests
