"""Semantic checks on AST (types, scopes, await DAG).

Deep checks still also run in the legacy Python path during emit. This module
owns checks that are ready to run on the structured AST first.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .ast_nodes import (
    ArrayDecl,
    AssignStmt,
    AugAssignStmt,
    AwaitExpr,
    BinaryOp,
    Block,
    Call,
    Cast,
    ClassDef,
    Expr,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    Identifier,
    IfStmt,
    ImportStmt,
    InterpolatedString,
    Literal,
    Module,
    RepeatStmt,
    ReturnStmt,
    SharedDecl,
    TasksBlock,
    UnaryOp,
    WhileStmt,
)


def analyze(module: Module, *, source_path: Path | None = None) -> Module:
    """Validate module; raise TranspileError on known AST-checkable faults."""
    _reject_let(module)
    _check_return_types(module.body)
    declared: set[str] = set()
    constants: set[str] = set()
    types: dict[str, str] = {}
    fixed: set[str] = set()
    _seed_imports(module, source_path, declared, constants, types, fixed)
    _check_bindings(
        module.body,
        types=types,
        declared=declared,
        constants=constants,
        fixed=fixed,
    )
    _check_await_cycles(module.body)
    return module


def _transpile_error(message: str, line: int = 1, column: int = 1, code_line: str = "") -> None:
    from .transpiler import TranspileError

    raise TranspileError(message, line, column, code_line)


def _pys_import_line(stmt: ImportStmt) -> str:
    if stmt.kind == "module":
        return f"import {stmt.module}"
    if stmt.kind == "as":
        return f"import {stmt.module} as {stmt.alias}"
    if stmt.kind == "all_from":
        return f"import all from {stmt.module}"
    if stmt.kind == "name_from":
        return f"import {stmt.name} from {stmt.module}"
    return ""


def _seed_imports(
    module: Module,
    source_path: Path | None,
    declared: set[str],
    constants: set[str],
    types: dict[str, str],
    fixed: set[str],
) -> None:
    """Pull imported names (and const/fix) into scope when source_path is known."""
    if source_path is None:
        return
    from .transpiler import Parser

    resolver = Parser(module.source, source_path=source_path, enforce_formatting=False)
    for stmt in module.body:
        if not isinstance(stmt, ImportStmt):
            continue
        line = _pys_import_line(stmt)
        if not line:
            continue
        try:
            resolver._translate_import_statement(line, stmt.span.line if stmt.span else 1, line)
        except Exception:
            # Legacy emit still reports import errors.
            continue
    declared |= set(resolver.imported_names)
    constants |= set(resolver.constants)
    fixed |= set(resolver.fixed_vars)
    for name, t in resolver.variable_types.items():
        if name in resolver.imported_names:
            types[name] = t


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


def _is_compile_time_const_expr(expr: Expr | None) -> bool:
    if expr is None:
        return False
    if isinstance(expr, Literal):
        return expr.kind in {"int", "float", "string", "char", "bool", "null"}
    if isinstance(expr, UnaryOp) and expr.op in {"+", "-"}:
        return _is_compile_time_const_expr(expr.operand)
    if isinstance(expr, BinaryOp) and expr.op in {"+", "-", "*", "/", "%"}:
        return _is_compile_time_const_expr(expr.left) and _is_compile_time_const_expr(expr.right)
    if isinstance(expr, Cast):
        return _is_compile_time_const_expr(expr.expr)
    return False


def _check_bindings(
    body: list[Any],
    *,
    types: dict[str, str] | None = None,
    declared: set[str] | None = None,
    constants: set[str] | None = None,
    fixed: set[str] | None = None,
    loop_counters: set[str] | None = None,
) -> None:
    types = types if types is not None else {}
    declared = declared if declared is not None else set()
    constants = constants if constants is not None else set()
    fixed = fixed if fixed is not None else set()
    loop_counters = loop_counters if loop_counters is not None else set()

    for stmt in body:
        if isinstance(stmt, AssignStmt):
            line = stmt.span.line if stmt.span else 1
            col = stmt.span.column if stmt.span else 1
            if stmt.declare_type or stmt.is_const or stmt.is_fix:
                if stmt.is_const:
                    if not _is_compile_time_const_expr(stmt.value):
                        _transpile_error(
                            f"Const '{stmt.name}' must be initialized with a compile-time constant expression.",
                            line,
                            col,
                            f"const … {stmt.name}",
                        )
                    constants.add(stmt.name)
                if stmt.is_fix:
                    fixed.add(stmt.name)
                if stmt.declare_type == "var":
                    types[stmt.name] = _infer_type(stmt.value) or "int"
                elif stmt.declare_type:
                    types[stmt.name] = stmt.declare_type
                declared.add(stmt.name)
            else:
                if "." not in stmt.name and stmt.name in loop_counters:
                    _transpile_error(
                        f"Loop counter '{stmt.name}' is immutable and cannot be modified inside the loop.",
                        line,
                        col,
                        f"{stmt.name} = ...",
                    )
                if "." not in stmt.name and stmt.name not in declared:
                    _transpile_error(
                        f"Undeclared variable '{stmt.name}'. Variables must be declared with a type before assignment.",
                        line,
                        col,
                        f"{stmt.name} = ...",
                    )
                if stmt.name in constants:
                    _transpile_error(
                        f"Cannot assign to const '{stmt.name}'. Constants are fixed at compile time.",
                        line,
                        col,
                        f"{stmt.name} = ...",
                    )
                if stmt.name in fixed:
                    _transpile_error(
                        f"Cannot assign to fix '{stmt.name}'. Fixed variables are immutable after assignment.",
                        line,
                        col,
                        f"{stmt.name} = ...",
                    )
                if "." not in stmt.name and stmt.name in types:
                    inferred = _infer_type(stmt.value)
                    declared_t = types[stmt.name]
                    if inferred and inferred != declared_t:
                        if not (declared_t in {"int", "float"} and inferred in {"int", "float"}):
                            _transpile_error(
                                f"Type mismatch: cannot assign {inferred} to '{stmt.name}' of type {declared_t}.",
                                line,
                                col,
                                f"{stmt.name} = ...",
                            )
        elif isinstance(stmt, AugAssignStmt):
            line = stmt.span.line if stmt.span else 1
            col = stmt.span.column if stmt.span else 1
            if stmt.name in loop_counters:
                _transpile_error(
                    f"Loop counter '{stmt.name}' is immutable and cannot be modified inside the loop.",
                    line,
                    col,
                    f"{stmt.name}{stmt.op}",
                )
            if stmt.name in constants:
                _transpile_error(
                    f"Cannot modify const '{stmt.name}'. Constants are fixed at compile time.",
                    line,
                    col,
                    f"{stmt.name}{stmt.op}",
                )
            if stmt.name in fixed:
                _transpile_error(
                    f"Cannot modify fix '{stmt.name}'. Fixed variables are immutable after assignment.",
                    line,
                    col,
                    f"{stmt.name}{stmt.op}",
                )
            if "." not in stmt.name and stmt.name not in declared:
                _transpile_error(
                    f"Undeclared variable '{stmt.name}'. Variables must be declared with a type before assignment.",
                    line,
                    col,
                    f"{stmt.name}{stmt.op}",
                )
        elif isinstance(stmt, ArrayDecl):
            declared.add(stmt.name)
            if stmt.elem_type:
                types[stmt.name] = f"{stmt.elem_type}[]"
        elif isinstance(stmt, SharedDecl):
            declared.add(stmt.name)
            if stmt.declare_type:
                types[stmt.name] = stmt.declare_type
        elif isinstance(stmt, ImportStmt):
            if stmt.kind == "as" and stmt.alias:
                declared.add(stmt.alias)
            elif stmt.kind == "name_from" and stmt.name:
                declared.add(stmt.name)
        elif isinstance(stmt, FunctionDef):
            declared.add(stmt.name)
            local_decl = set(declared) | set(stmt.params)
            local_types = dict(types)
            for p in stmt.params:
                local_types.setdefault(p, "int")
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=local_types,
                    declared=local_decl,
                    constants=set(constants),
                    fixed=set(fixed),
                    loop_counters=set(),
                )
        elif isinstance(stmt, ClassDef):
            declared.add(stmt.name)
            for m in stmt.methods:
                local_decl = set(declared) | set(m.params) | {"self"}
                if m.body:
                    _check_bindings(
                        m.body.statements,
                        types=dict(types),
                        declared=local_decl,
                        constants=set(constants),
                        fixed=set(fixed),
                        loop_counters=set(),
                    )
        elif isinstance(stmt, TasksBlock):
            for t in stmt.tasks:
                local_decl = set(declared) | set(t.params)
                if t.body:
                    _check_bindings(
                        t.body.statements,
                        types=dict(types),
                        declared=local_decl,
                        constants=set(constants),
                        fixed=set(fixed),
                        loop_counters=set(),
                    )
        elif isinstance(stmt, IfStmt):
            if stmt.then_body:
                _check_bindings(
                    stmt.then_body.statements,
                    types=types,
                    declared=declared,
                    constants=constants,
                    fixed=fixed,
                    loop_counters=loop_counters,
                )
            if stmt.else_body:
                _check_bindings(
                    stmt.else_body.statements,
                    types=types,
                    declared=declared,
                    constants=constants,
                    fixed=fixed,
                    loop_counters=loop_counters,
                )
        elif isinstance(stmt, Block):
            _check_bindings(
                stmt.statements,
                types=types,
                declared=declared,
                constants=constants,
                fixed=fixed,
                loop_counters=loop_counters,
            )
        elif isinstance(stmt, ForRangeStmt):
            declared.add(stmt.var)
            nested = set(loop_counters) | {stmt.var}
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=types,
                    declared=declared,
                    constants=constants,
                    fixed=fixed,
                    loop_counters=nested,
                )
        elif isinstance(stmt, ForEachStmt):
            declared.add(stmt.var)
            # foreach vars are writable in PYS? Legacy only marks C-style for counters.
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=types,
                    declared=declared,
                    constants=constants,
                    fixed=fixed,
                    loop_counters=loop_counters,
                )
        elif isinstance(stmt, (WhileStmt, RepeatStmt)):
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=types,
                    declared=declared,
                    constants=constants,
                    fixed=fixed,
                    loop_counters=loop_counters,
                )


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
