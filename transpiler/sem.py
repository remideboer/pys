"""Semantic checks on AST (types, scopes, await DAG).

Deep checks still also run in the legacy Python path during emit. This module
owns checks that are ready to run on the structured AST first.
"""
from __future__ import annotations

from typing import Any

from .ast_nodes import (
    AssignStmt,
    AwaitExpr,
    BinaryOp,
    Block,
    Call,
    ClassDef,
    Expr,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    Identifier,
    IfStmt,
    InterpolatedString,
    Literal,
    Module,
    RepeatStmt,
    ReturnStmt,
    TasksBlock,
    UnaryOp,
    WhileStmt,
)


def analyze(module: Module) -> Module:
    """Validate module; raise TranspileError on known AST-checkable faults."""
    _reject_let(module)
    _check_return_types(module.body)
    _check_simple_assignments(module.body)
    _check_await_cycles(module.body)
    return module


def _transpile_error(message: str, line: int = 1, column: int = 1, code_line: str = "") -> None:
    from .transpiler import TranspileError

    raise TranspileError(message, line, column, code_line)


def _reject_let(module: Module) -> None:
    for line_no, raw in enumerate(module.source.splitlines(), start=1):
        stripped = raw.lstrip()
        if stripped.startswith("let ") or stripped == "let":
            col = raw.find("let") + 1
            _transpile_error(
                "Use `var` instead of `let` for type-inferred variables.",
                line_no,
                col,
                raw.rstrip(),
            )


def _check_return_types(body: list[Any]) -> None:
    for node in body:
        if isinstance(node, FunctionDef):
            _check_fn_returns(node.return_type, node.body, node.span.line if node.span else 1)
            if node.body:
                _check_return_types(node.body.statements)
        elif isinstance(node, ClassDef):
            for m in node.methods:
                if m.is_constructor:
                    if m.body:
                        _check_return_types(m.body.statements)
                    continue
                _check_fn_returns(m.return_type, m.body, m.span.line if m.span else 1)
                if m.body:
                    _check_return_types(m.body.statements)
        elif isinstance(node, TasksBlock):
            for t in node.tasks:
                if t.body:
                    _check_return_types(t.body.statements)
        elif isinstance(node, IfStmt):
            if node.then_body:
                _check_return_types(node.then_body.statements)
            if node.else_body:
                _check_return_types(node.else_body.statements)
        elif isinstance(node, Block):
            _check_return_types(node.statements)
        elif isinstance(node, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
            if node.body:
                _check_return_types(node.body.statements)


def _check_fn_returns(return_type: str, body: Block | None, line: int) -> None:
    if not body:
        return

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ReturnStmt) and stmt.value is not None and not return_type:
                _transpile_error(
                    "Functions that return a value must declare a return type in the signature "
                    "(e.g. `global function AppStore openStore()` or `public int capacity()`).",
                    stmt.span.line if stmt.span else line,
                    stmt.span.column if stmt.span else 1,
                    "return",
                )
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(stmt.body.statements)

    walk(body.statements)


def _infer_type(expr: Expr | None) -> str | None:
    if expr is None:
        return None
    if isinstance(expr, Literal):
        if expr.kind in {"string", "char", "int", "float", "bool", "null"}:
            return expr.kind
        return None
    if isinstance(expr, InterpolatedString):
        return "string"
    if isinstance(expr, BinaryOp) and expr.op == "+":
        left = _infer_type(expr.left)
        right = _infer_type(expr.right)
        if left == "string" or right == "string":
            return "string"
        if left == right:
            return left
        return None
    if isinstance(expr, UnaryOp):
        return _infer_type(expr.operand)
    return None


def _check_simple_assignments(body: list[Any], types: dict[str, str] | None = None) -> None:
    types = types if types is not None else {}
    for stmt in body:
        if isinstance(stmt, AssignStmt):
            if stmt.declare_type:
                if stmt.declare_type == "var":
                    types[stmt.name] = _infer_type(stmt.value) or "int"
                else:
                    types[stmt.name] = stmt.declare_type
            elif "." not in stmt.name and stmt.name in types:
                inferred = _infer_type(stmt.value)
                declared = types[stmt.name]
                if inferred and inferred != declared:
                    if not (declared in {"int", "float"} and inferred in {"int", "float"}):
                        line = stmt.span.line if stmt.span else 1
                        col = stmt.span.column if stmt.span else 1
                        _transpile_error(
                            f"Type mismatch: cannot assign {inferred} to '{stmt.name}' of type {declared}.",
                            line,
                            col,
                            f"{stmt.name} = ...",
                        )
        elif isinstance(stmt, FunctionDef):
            if stmt.body:
                _check_simple_assignments(stmt.body.statements, dict(types))
        elif isinstance(stmt, ClassDef):
            for m in stmt.methods:
                if m.body:
                    _check_simple_assignments(m.body.statements, dict(types))
        elif isinstance(stmt, TasksBlock):
            for t in stmt.tasks:
                if t.body:
                    _check_simple_assignments(t.body.statements, dict(types))
        elif isinstance(stmt, IfStmt):
            if stmt.then_body:
                _check_simple_assignments(stmt.then_body.statements, types)
            if stmt.else_body:
                _check_simple_assignments(stmt.else_body.statements, types)
        elif isinstance(stmt, Block):
            _check_simple_assignments(stmt.statements, types)
        elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
            if stmt.body:
                _check_simple_assignments(stmt.body.statements, types)


def _await_targets(expr: Expr | None) -> list[str]:
    if expr is None:
        return []
    if isinstance(expr, AwaitExpr):
        t = expr.target
        if isinstance(t, Call) and isinstance(t.callee, Identifier):
            return [t.callee.name]
        if isinstance(t, Identifier):
            return [t.name]
        return []
    found: list[str] = []
    for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index"):
        child = getattr(expr, attr, None)
        if isinstance(child, Expr):
            found.extend(_await_targets(child))
    args = getattr(expr, "args", None)
    if isinstance(args, list):
        for a in args:
            if isinstance(a, Expr):
                found.extend(_await_targets(a))
    return found


def _stmt_await_targets(stmt: Any) -> list[str]:
    names: list[str] = []
    if isinstance(stmt, AssignStmt):
        names.extend(_await_targets(stmt.value))
    elif isinstance(stmt, ReturnStmt):
        names.extend(_await_targets(stmt.value))
    else:
        for attr in ("expr", "value", "cond"):
            child = getattr(stmt, attr, None)
            if isinstance(child, Expr):
                names.extend(_await_targets(child))
    return names


def _awaits_in_block(body: Block | None) -> list[str]:
    if not body:
        return []
    names: list[str] = []

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            names.extend(_stmt_await_targets(stmt))
            if isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(stmt.body.statements)

    walk(body.statements)
    return names


def _check_await_cycles(body: list[Any]) -> None:
    for stmt in body:
        if isinstance(stmt, TasksBlock):
            _check_one_tasks_group(stmt)
        elif isinstance(stmt, FunctionDef) and stmt.body:
            _check_await_cycles(stmt.body.statements)
        elif isinstance(stmt, ClassDef):
            for m in stmt.methods:
                if m.body:
                    _check_await_cycles(m.body.statements)
        elif isinstance(stmt, IfStmt):
            if stmt.then_body:
                _check_await_cycles(stmt.then_body.statements)
            if stmt.else_body:
                _check_await_cycles(stmt.else_body.statements)
        elif isinstance(stmt, Block):
            _check_await_cycles(stmt.statements)
        elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
            if stmt.body:
                _check_await_cycles(stmt.body.statements)


def _check_one_tasks_group(group: TasksBlock) -> None:
    nodes = {t.name for t in group.tasks}
    graph: dict[str, set[str]] = {t.name: set() for t in group.tasks}
    for task in group.tasks:
        for target in _awaits_in_block(task.body):
            if target not in nodes:
                line = group.span.line if group.span else 1
                _transpile_error(
                    f"Unknown task '{target}' in await "
                    f"(from task '{task.name}'). "
                    f"Declare it in this `tasks` group.",
                    line,
                    1,
                    "}",
                )
            graph[task.name].add(target)
    cycle = _find_await_cycle(graph)
    if not cycle:
        return
    path = " → ".join(cycle)
    line = group.span.line if group.span else 1
    _transpile_error(
        f"Await cycle in tasks group (would deadlock): {path}. "
        f"Await dependencies must form a DAG — a task must not wait "
        f"(directly or indirectly) on itself. Prefer a consumer that "
        f"awaits producers, not mutual awaits.",
        line,
        1,
        "}",
    )


def _find_await_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        visiting.add(node)
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            if nxt in visiting:
                i = stack.index(nxt)
                return stack[i:] + [nxt]
            if nxt not in visited:
                found = dfs(nxt)
                if found:
                    return found
        visiting.discard(node)
        stack.pop()
        visited.add(node)
        return None

    for start in sorted(graph):
        if start not in visited:
            found = dfs(start)
            if found:
                return found
    return None
