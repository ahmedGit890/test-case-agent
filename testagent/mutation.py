"""Mutation testing for small Python validator functions.

Idea: a good test suite should fail when the code under test is wrong. We
create many slightly wrong copies of the function ("mutants", for example
`>=` changed to `>`), run the tests against each one, and count how many
mutants the tests catch. That share is the mutation score.

Scope and limits (be honest about these when you describe this work):
  * works on one self-contained function that takes a single number
  * first-order mutants only (one change at a time)
  * "equivalent" mutants (changes that do not alter behaviour) are found by
    comparing outputs over a sample domain, so the result depends on that domain
"""
import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from typing import Callable

# Each comparison operator can be swapped for these neighbours.
COMPARE_MUTATIONS = {
    ast.Lt: [ast.LtE, ast.Gt],
    ast.LtE: [ast.Lt, ast.GtE],
    ast.Gt: [ast.GtE, ast.Lt],
    ast.GtE: [ast.Gt, ast.LtE],
    ast.Eq: [ast.NotEq],
    ast.NotEq: [ast.Eq],
    ast.In: [ast.NotIn],
    ast.NotIn: [ast.In],
}
# Arithmetic: each operator is swapped for one neighbour.
ARITHMETIC_MUTATIONS = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.FloorDiv: ast.Mult,
}
SYMBOL = {
    ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
    ast.In: "in", ast.NotIn: "not in",
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "//",
}


class _Mutator(ast.NodeTransformer):
    """Walks the code and applies exactly one mutation: the `target`-th site.

    Run it with target=-1 first to count how many mutation sites exist.
    """

    def __init__(self, target):
        self.target = target
        self.count = -1
        self.description = None

    def _hit(self, description):
        self.count += 1
        if self.count == self.target:
            self.description = description
            return True
        return False

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            for new_op in COMPARE_MUTATIONS.get(type(op), []):
                # In a chain like `a <= x <= b` both operators share a line, so the
                # column of the right-hand operand tells the two mutants apart.
                where = f"line {node.lineno}, col {node.comparators[i].col_offset}"
                if self._hit(f"{where}: {SYMBOL[type(op)]} -> {SYMBOL[new_op]}"):
                    node.ops[i] = new_op()
        return node

    def visit_Expr(self, node):
        # A bare constant statement is a docstring: documentation, not behaviour.
        if isinstance(node.value, ast.Constant):
            return node
        return self.generic_visit(node)

    def visit_Constant(self, node):
        where = f"line {node.lineno}, col {node.col_offset}"
        if isinstance(node.value, bool):
            return node
        if isinstance(node.value, int):
            for delta in (1, -1):
                if self._hit(f"{where}: {node.value} -> {node.value + delta}"):
                    return ast.copy_location(ast.Constant(node.value + delta), node)
        elif isinstance(node.value, str):
            changed = node.value + "x"
            if self._hit(f"{where}: {node.value!r} -> {changed!r}"):
                return ast.copy_location(ast.Constant(changed), node)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        new_op = ARITHMETIC_MUTATIONS.get(type(node.op))
        if new_op:
            where = f"line {node.lineno}, col {node.col_offset}"
            if self._hit(f"{where}: {SYMBOL[type(node.op)]} -> {SYMBOL[new_op]}"):
                node.op = new_op()
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        old, new = (ast.And, ast.Or) if isinstance(node.op, ast.And) else (ast.Or, ast.And)
        if self._hit(f"line {node.lineno}: {old.__name__.lower()} -> {new.__name__.lower()}"):
            node.op = new()
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not) and self._hit(f"line {node.lineno}: removed 'not'"):
            return node.operand
        return node


@dataclass
class Mutant:
    description: str
    func: Callable


def _source_of(func):
    return textwrap.dedent(inspect.getsource(func))


def _build(tree, original):
    """Compile a (mutated) syntax tree back into a callable."""
    ast.fix_missing_locations(tree)
    namespace = dict(original.__globals__)  # copy: never touch the real module
    exec(compile(tree, "<mutant>", "exec"), namespace)
    return namespace[original.__name__]


def generate_mutants(func):
    source = _source_of(func)
    counter = _Mutator(-1)
    counter.visit(ast.parse(source))
    mutants = []
    for target in range(counter.count + 1):
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                node.decorator_list = []
        mutator = _Mutator(target)
        mutator.visit(tree)
        mutants.append(Mutant(mutator.description, _build(tree, func)))
    return mutants


def _behaviour(fn, domain):
    out = []
    for x in domain:
        try:
            out.append(("ok", bool(fn(x))))
        except Exception as exc:  # a crash is also behaviour
            out.append(("error", type(exc).__name__))
    return out


def _fails(fn, case):
    """True if the test case fails against `fn` (a crash counts as failing)."""
    try:
        return bool(fn(case["input"])) != case["expected"]
    except Exception:
        return True


@dataclass
class MutationReport:
    total: int
    equivalent: int
    killed: int
    original_passes: bool
    survivors: list = field(default_factory=list)

    @property
    def score(self):
        testable = self.total - self.equivalent
        return self.killed / testable if testable else 1.0


def mutation_report(func, cases, domain=range(-50, 151)):
    """Run `cases` (as produced by tools.generate_boundary_cases) against mutants of `func`."""
    original_behaviour = _behaviour(func, domain)
    report = MutationReport(
        total=0, equivalent=0, killed=0,
        original_passes=not any(_fails(func, c) for c in cases),
    )
    for mutant in generate_mutants(func):
        report.total += 1
        if _behaviour(mutant.func, domain) == original_behaviour:
            report.equivalent += 1
        elif any(_fails(mutant.func, c) for c in cases):
            report.killed += 1
        else:
            report.survivors.append(mutant.description)
    return report
