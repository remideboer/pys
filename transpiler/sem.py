"""Semantic checks on AST (types, scopes, await DAG, library boundary)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .ast_nodes import (
    ArrayDecl,
    ArrayLiteral,
    AssignStmt,
    AugAssignStmt,
    AwaitExpr,
    BinaryOp,
    Block,
    Call,
    Cast,
    ClassDef,
    Expr,
    ExprStmt,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    Identifier,
    IfStmt,
    ImportStmt,
    InterfaceDef,
    InterpolatedString,
    Literal,
    Member,
    Module,
    PrintStmt,
    RepeatStmt,
    ReturnStmt,
    SharedDecl,
    TasksBlock,
    UnaryOp,
    WhileStmt,
)

_TYPED_INTERP = re.compile(r"#([sficbo])\{([^}]+)\}")
_PRIMITIVES = frozenset({"int", "float", "char", "string", "bool"})
_SPEC_TYPES: dict[str, set[str]] = {
    "s": {"string"},
    "i": {"int"},
    "f": {"float"},
    "c": {"char"},
    "b": {"bool"},
    "o": set(),
}


def _is_simple_name(name: str) -> bool:
    """True for bare identifiers; false for member/index lvalues."""
    return "." not in name and "[" not in name


def analyze(module: Module, *, source_path: Path | None = None) -> Module:
    """Validate module; raise TranspileError on known AST-checkable faults."""
    _reject_let(module)
    _check_return_types(module.body)
    declared: set[str] = set()
    constants: set[str] = set()
    types: dict[str, str] = {}
    fixed: set[str] = set()
    import_resolver = _seed_imports(module, source_path, declared, constants, types, fixed)
    class_parents = _class_parents_map(module.body)
    class_names = set(class_parents) | {
        s.name for s in module.body if isinstance(s, ClassDef)
    }
    interfaces = {s.name for s in module.body if isinstance(s, InterfaceDef)}
    class_implements = _class_implements_map(module.body, interfaces)
    if import_resolver is not None:
        _check_library_types(
            module.body,
            import_resolver,
            types=types,
            class_names=class_names,
            interfaces=interfaces,
        )
    _check_bindings(
        module.body,
        types=types,
        declared=declared,
        constants=constants,
        fixed=fixed,
        class_parents=class_parents,
        class_names=class_names,
        class_implements=class_implements,
        interfaces=interfaces,
    )
    _check_oop(module.body, types=types)
    _check_interfaces(module.body)
    _check_shared_capture(module.body)
    _check_arrays(module.body)
    _check_class_member_modifiers(module.body)
    _check_await_placement(module.body)
    if import_resolver is not None:
        _check_seen_name_calls(module.body, import_resolver)
    _check_await_cycles(module.body)
    return module


def _transpile_error(
    message: str,
    line: int = 1,
    column: int = 1,
    code_line: str = "",
    *,
    code: str | None = None,
    suggested_fix: str | None = None,
    tips: list[str] | None = None,
) -> None:
    from .transpiler import TranspileError

    raise TranspileError(
        message,
        line,
        column,
        code_line,
        code=code,
        suggested_fix=suggested_fix,
        tips=tips,
    )


def _pys_import_line(stmt: ImportStmt) -> str:
    if stmt.kind == "module":
        return f"import {stmt.module}"
    if stmt.kind == "as":
        return f"import {stmt.module} as {stmt.alias}"
    if stmt.kind == "all_from":
        return f"import all from {stmt.module}"
    if stmt.kind == "name_from":
        names = stmt.names or ([stmt.name] if stmt.name else [])
        return f"import {', '.join(names)} from {stmt.module}"
    return ""


def _seed_imports(
    module: Module,
    source_path: Path | None,
    declared: set[str],
    constants: set[str],
    types: dict[str, str],
    fixed: set[str],
) -> Any | None:
    """Pull imported names (and const/fix) into scope when source_path is known."""
    if source_path is None:
        return None
    from .transpiler import TranspileError

    if source_path is None:
        return None
    from . import imports as imports_mod

    resolver = imports_mod.make_resolver(module.source, source_path)
    for stmt in module.body:
        if not isinstance(stmt, ImportStmt):
            continue
        line = _pys_import_line(stmt)
        if not line:
            continue
        try:
            imports_mod.translate_import(resolver, line, stmt.span.line if stmt.span else 1)
        except TranspileError:
            raise
        except Exception:
            continue
    declared |= set(resolver.imported_names)
    constants |= set(resolver.constants)
    fixed |= set(resolver.fixed_vars)
    for name, t in resolver.variable_types.items():
        if name in resolver.imported_names:
            types[name] = t
    return resolver


def _call_receiver_method(expr: Expr | None) -> tuple[str, str | None] | None:
    if not isinstance(expr, Call):
        return None
    callee = expr.callee
    if isinstance(callee, Identifier):
        return callee.name, None
    if isinstance(callee, Member):
        method = callee.name
        obj = callee.object
        parts: list[str] = []
        while isinstance(obj, Member):
            parts.append(obj.name)
            obj = obj.object
        if isinstance(obj, Identifier):
            parts.append(obj.name)
            parts.reverse()
            if len(parts) == 1:
                return parts[0], method
            return ".".join(parts + [method]), None
    return None


def _base_type_name(type_name: str) -> str:
    name = (type_name or "").strip()
    if "<" in name:
        name = name.split("<", 1)[0]
    if name.endswith("[]"):
        name = name[:-2]
    return name


def _known_library_type(type_name: str, resolver: Any) -> bool:
    from .pytypes import _find_class_in_package

    base = _base_type_name(type_name)
    primitives = {"int", "float", "char", "string", "bool", "list", "dict", "tuple", "set", "var"}
    if not base or base in primitives:
        return True
    if base in resolver.class_parents or base in resolver.interfaces or base in resolver.exports:
        return True
    if base in getattr(resolver, "type_modules", {}):
        return True
    site_paths = resolver._deps_paths()
    for mod in sorted(set(resolver.imported_modules.values())):
        cls = _find_class_in_package(mod, base, site_paths)
        if isinstance(cls, type):
            resolver.type_modules[base] = cls.__module__
            return True
    return False


def _check_library_types(
    body: list[Any],
    resolver: Any,
    *,
    types: dict[str, str],
    class_names: set[str],
    interfaces: set[str],
) -> None:
    """Reject unknown library types and require types on inferred library returns."""
    from .pytypes import _usage_tips_for, infer_call_return_info

    site_paths = resolver._deps_paths()
    local_types = dict(types)

    for stmt in body:
        if not isinstance(stmt, AssignStmt):
            continue
        line = stmt.span.line if stmt.span else 1
        col = stmt.span.column if stmt.span else 1

        if stmt.declare_type and stmt.declare_type != "var":
            base = _base_type_name(stmt.declare_type)
            if (
                base not in class_names
                and base not in interfaces
                and not _known_library_type(stmt.declare_type, resolver)
            ):
                _transpile_error(
                    f"Unknown type '{base}'. Declare a class/interface, or import a library "
                    f"that defines it (via pys.deps).",
                    line,
                    col,
                    f"{stmt.declare_type} {stmt.name}",
                    code="pys.unknown-type",
                )
            local_types[stmt.name] = stmt.declare_type

        call = _call_receiver_method(stmt.value)
        if call is None:
            continue
        recv, method = call
        info = infer_call_return_info(
            recv,
            method,
            variable_types=local_types,
            imported_modules=resolver.imported_modules,
            site_paths=site_paths,
            type_modules=resolver.type_modules,
        )
        if info is None:
            continue
        if stmt.declare_type:
            local_types[stmt.name] = stmt.declare_type
            continue
        # Untyped assignment from a library call with a known return shape.
        if info.from_external and info.pys_type:
            tips = _usage_tips_for(info.pys_type, info.element_type, stmt.name)
            rhs = f"{recv}.{method}()" if method else f"{recv}()"
            suggested = f"{info.pys_type} {stmt.name} = {rhs}"
            msg = (
                f"Missing type for '{stmt.name}'. Library call returns `{info.pys_type}` "
                f"(weak/untyped boundary)."
            )
            _transpile_error(
                msg,
                line,
                col,
                f"{stmt.name} = ...",
                code="pys.missing-type",
                suggested_fix=suggested,
                tips=tips,
            )


def _class_parents_map(body: list[Any]) -> dict[str, str | None]:
    interfaces = {s.name for s in body if isinstance(s, InterfaceDef)}
    parents: dict[str, str | None] = {}
    for stmt in body:
        if not isinstance(stmt, ClassDef):
            continue
        parent: str | None = None
        for b in stmt.bases:
            if b not in interfaces:
                parent = b
                break
        parents[stmt.name] = parent
    return parents


def _class_implements_map(body: list[Any], interfaces: set[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for stmt in body:
        if not isinstance(stmt, ClassDef):
            continue
        out[stmt.name] = [b for b in stmt.bases if b in interfaces]
    return out


def _is_assignable_type(
    actual: str,
    declared: str,
    class_parents: dict[str, str | None],
    *,
    class_implements: dict[str, list[str]] | None = None,
    interfaces: set[str] | None = None,
) -> bool:
    if actual == declared:
        return True
    if actual == "null":
        return True
    a_base = _base_type_name(actual)
    d_base = _base_type_name(declared)
    if a_base == d_base:
        return True
    if d_base in _PRIMITIVES or a_base in _PRIMITIVES:
        return d_base in {"int", "float"} and a_base in {"int", "float"}
    current: str | None = a_base
    seen: set[str] = set()
    implements = class_implements or {}
    iface_set = interfaces or set()
    while current:
        if current == d_base:
            return True
        if d_base in iface_set and d_base in implements.get(current, []):
            return True
        if current in seen:
            break
        seen.add(current)
        parent = class_parents.get(current)
        current = _base_type_name(parent) if parent else None
    return False


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


def _infer_type(expr: Expr | None, class_names: set[str] | None = None) -> str | None:
    if expr is None:
        return None
    if isinstance(expr, Literal):
        if expr.kind in {"string", "char", "int", "float", "bool", "null"}:
            return expr.kind
        return None
    if isinstance(expr, InterpolatedString):
        return "string"
    if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
        if class_names and expr.callee.name in class_names:
            return expr.callee.name
        return None
    if isinstance(expr, BinaryOp) and expr.op == "+":
        left = _infer_type(expr.left, class_names)
        right = _infer_type(expr.right, class_names)
        if left == "string" or right == "string":
            return "string"
        if left == right:
            return left
        return None
    if isinstance(expr, UnaryOp):
        return _infer_type(expr.operand, class_names)
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


def _base_type_name(type_name: str) -> str:
    t = type_name.strip()
    if "<" in t:
        return t.split("<", 1)[0].strip()
    return t


def _split_angled_commas(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(depth - 1, 0)
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _extract_type_args(type_name: str) -> list[str]:
    t = type_name.strip()
    lt = t.find("<")
    if lt < 0 or not t.endswith(">"):
        return []
    return _split_angled_commas(t[lt + 1 : -1])


def _lookup_name_type(expr: str, types: dict[str, str]) -> str | None:
    expr = expr.strip()
    if not expr:
        return None
    if re.fullmatch(r"[A-Za-z_]\w*", expr):
        return types.get(expr)
    indexed = re.fullmatch(r"(?P<recv>[A-Za-z_]\w*)\[(?P<idx>[^\]]+)\]", expr)
    if not indexed:
        return None
    recv_t = types.get(indexed.group("recv"))
    if not recv_t:
        return None
    if recv_t.endswith("[]"):
        return recv_t[:-2]
    args = _extract_type_args(recv_t)
    idx = indexed.group("idx").strip()
    if args and re.fullmatch(r"\d+", idx):
        i = int(idx)
        if 0 <= i < len(args):
            return args[i]
    return None


def _check_typed_interpolation(
    expr: Expr | None,
    types: dict[str, str],
    *,
    line: int,
    column: int,
    code_line: str = "",
) -> None:
    if expr is None:
        return
    if isinstance(expr, InterpolatedString):
        for m in _TYPED_INTERP.finditer(expr.raw):
            spec = m.group(1)
            inner = m.group(2).strip()
            var_type = _lookup_name_type(inner, types)
            if var_type is None:
                continue
            check_type = _base_type_name(var_type)
            if spec == "o":
                if check_type in _PRIMITIVES:
                    _transpile_error(
                        f"Typed interpolation #o{{}} requires an object type, but '{inner}' is {check_type}.",
                        line,
                        column,
                        code_line or expr.raw,
                    )
            elif check_type not in _SPEC_TYPES[spec]:
                spec_label = {"s": "string", "i": "int", "f": "float", "c": "char", "b": "bool"}[spec]
                _transpile_error(
                    f"Typed interpolation #{spec}{{}} requires {spec_label}, but '{inner}' is {check_type}.",
                    line,
                    column,
                    code_line or expr.raw,
                )
    for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index"):
        child = getattr(expr, attr, None)
        if isinstance(child, Expr):
            _check_typed_interpolation(child, types, line=line, column=column, code_line=code_line)
    args = getattr(expr, "args", None)
    if isinstance(args, list):
        for a in args:
            if isinstance(a, Expr):
                _check_typed_interpolation(a, types, line=line, column=column, code_line=code_line)


def _check_bindings(
    body: list[Any],
    *,
    types: dict[str, str] | None = None,
    declared: set[str] | None = None,
    constants: set[str] | None = None,
    fixed: set[str] | None = None,
    loop_counters: set[str] | None = None,
    class_parents: dict[str, str | None] | None = None,
    class_names: set[str] | None = None,
    class_implements: dict[str, list[str]] | None = None,
    interfaces: set[str] | None = None,
) -> None:
    types = types if types is not None else {}
    declared = declared if declared is not None else set()
    constants = constants if constants is not None else set()
    fixed = fixed if fixed is not None else set()
    loop_counters = loop_counters if loop_counters is not None else set()
    class_parents = class_parents if class_parents is not None else {}
    class_names = class_names if class_names is not None else set()
    class_implements = class_implements if class_implements is not None else {}
    interfaces = interfaces if interfaces is not None else set()

    for stmt in body:
        if isinstance(stmt, AssignStmt):
            line = stmt.span.line if stmt.span else 1
            col = stmt.span.column if stmt.span else 1
            _check_typed_interpolation(stmt.value, types, line=line, column=col)
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
                    types[stmt.name] = _infer_type(stmt.value, class_names) or "int"
                elif stmt.declare_type:
                    types[stmt.name] = stmt.declare_type
                    inferred = _infer_type(stmt.value, class_names)
                    if inferred and not _is_assignable_type(
                        inferred,
                        stmt.declare_type,
                        class_parents,
                        class_implements=class_implements,
                        interfaces=interfaces,
                    ):
                        _transpile_error(
                            f"Type mismatch: cannot assign {inferred} to '{stmt.name}' of type {stmt.declare_type}.",
                            line,
                            col,
                            f"{stmt.declare_type} {stmt.name} = ...",
                        )
                declared.add(stmt.name)
            else:
                if _is_simple_name(stmt.name) and stmt.name in loop_counters:
                    _transpile_error(
                        f"Loop counter '{stmt.name}' is immutable and cannot be modified inside the loop.",
                        line,
                        col,
                        f"{stmt.name} = ...",
                    )
                if _is_simple_name(stmt.name) and stmt.name not in declared:
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
                if _is_simple_name(stmt.name) and stmt.name in types:
                    inferred = _infer_type(stmt.value, class_names)
                    declared_t = types[stmt.name]
                    if inferred and not _is_assignable_type(
                        inferred,
                        declared_t,
                        class_parents,
                        class_implements=class_implements,
                        interfaces=interfaces,
                    ):
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
            if _is_simple_name(stmt.name) and stmt.name not in declared:
                _transpile_error(
                    f"Undeclared variable '{stmt.name}'. Variables must be declared with a type before assignment.",
                    line,
                    col,
                    f"{stmt.name}{stmt.op}",
                )
        elif isinstance(stmt, PrintStmt):
            line = stmt.span.line if stmt.span else 1
            col = stmt.span.column if stmt.span else 1
            _check_typed_interpolation(stmt.value, types, line=line, column=col)
        elif isinstance(stmt, ReturnStmt):
            line = stmt.span.line if stmt.span else 1
            col = stmt.span.column if stmt.span else 1
            _check_typed_interpolation(stmt.value, types, line=line, column=col)
        elif isinstance(stmt, ExprStmt):
            line = stmt.span.line if stmt.span else 1
            col = stmt.span.column if stmt.span else 1
            _check_typed_interpolation(stmt.expr, types, line=line, column=col)
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
            elif stmt.kind == "name_from":
                for n in stmt.names or ([stmt.name] if stmt.name else []):
                    declared.add(n)
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
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
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
                        class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
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
                        class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
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
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
                )
            if stmt.else_body:
                _check_bindings(
                    stmt.else_body.statements,
                    types=types,
                    declared=declared,
                    constants=constants,
                    fixed=fixed,
                    loop_counters=loop_counters,
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
                )
        elif isinstance(stmt, Block):
            _check_bindings(
                stmt.statements,
                types=types,
                declared=declared,
                constants=constants,
                fixed=fixed,
                loop_counters=loop_counters,
                class_parents=class_parents,
            class_names=class_names,
            class_implements=class_implements,
            interfaces=interfaces,
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
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
                )
        elif isinstance(stmt, ForEachStmt):
            declared.add(stmt.var)
            if stmt.var_type:
                types[stmt.var] = stmt.var_type
            # foreach vars are writable in PYS? Legacy only marks C-style for counters.
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=types,
                    declared=declared,
                    constants=constants,
                    fixed=fixed,
                    loop_counters=loop_counters,
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
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
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
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


def _check_oop(body: list[Any], *, types: dict[str, str]) -> None:
    sealed: set[str] = set()
    class_names: set[str] = set()
    interfaces: set[str] = set()
    class_members: dict[str, dict[str, str]] = {}
    class_parents: dict[str, str | None] = {}
    class_implements: dict[str, list[str]] = {}

    for stmt in body:
        if isinstance(stmt, InterfaceDef):
            interfaces.add(stmt.name)
            class_members[stmt.name] = {m: "public" for m in stmt.methods}
        elif isinstance(stmt, ClassDef):
            class_names.add(stmt.name)
            if stmt.sealed:
                sealed.add(stmt.name)
            members: dict[str, str] = {}
            for f in stmt.fields:
                members[f.name] = f.access or "public"
            for m in stmt.methods:
                if not m.is_constructor:
                    members[m.name] = m.access or "public"
            class_members[stmt.name] = members

    for stmt in body:
        if not isinstance(stmt, ClassDef):
            continue
        parent: str | None = None
        impls: list[str] = []
        for b in stmt.bases:
            if b in interfaces:
                impls.append(b)
            elif parent is None:
                parent = b
        class_parents[stmt.name] = parent
        class_implements[stmt.name] = impls
        for b in stmt.bases:
            if b in sealed:
                line = stmt.span.line if stmt.span else 1
                _transpile_error(
                    f"Class {stmt.name} cannot inherit from sealed class {b}.",
                    line,
                    1,
                    f"class {stmt.name}",
                )

    def is_subtype(child: str | None, parent: str) -> bool:
        current = child
        seen: set[str] = set()
        while current:
            if current == parent:
                return True
            if current in seen:
                break
            seen.add(current)
            current = class_parents.get(current)
        return False

    def lookup_member(type_name: str, member: str) -> tuple[str | None, str | None]:
        current: str | None = type_name
        seen: set[str] = set()
        while current:
            members = class_members.get(current, {})
            if member in members:
                return current, members[member]
            for iface in class_implements.get(current, []):
                iface_members = class_members.get(iface, {})
                if member in iface_members:
                    return iface, iface_members[member]
            if current in seen:
                break
            seen.add(current)
            current = class_parents.get(current)
        if type_name in interfaces:
            members = class_members.get(type_name, {})
            if member in members:
                return type_name, members[member]
        return None, None

    def receiver_type(recv: str, local_types: dict[str, str], current_class: str | None) -> str | None:
        if recv in {"this", "self"}:
            return current_class
        return local_types.get(recv)

    def check_member(
        recv: str,
        member: str,
        local_types: dict[str, str],
        current_class: str | None,
        line: int,
        column: int,
        code: str = "",
    ) -> None:
        recv_t = receiver_type(recv, local_types, current_class)
        if not recv_t:
            return
        defining_cls, access = lookup_member(recv_t, member)
        if defining_cls is None or access is None:
            known = recv_t in class_members or recv_t in interfaces or recv_t in class_parents
            if known:
                _transpile_error(
                    f"'{member}' is not a member of declared type {recv_t}.",
                    line,
                    column,
                    code or f"{recv}.{member}",
                )
            return
        allowed = False
        if access == "public":
            allowed = True
        elif access == "module":
            allowed = True
        elif access == "private":
            allowed = current_class == defining_cls
        elif access == "protected":
            allowed = current_class is not None and is_subtype(current_class, defining_cls)
        if allowed:
            return
        _transpile_error(
            f"Access denied: '{member}' is {access} in class {defining_cls}.",
            line,
            column,
            code or f"{recv}.{member}",
        )

    def walk_expr(expr: Expr | None, local_types: dict[str, str], current_class: str | None) -> None:
        if expr is None:
            return
        if isinstance(expr, Member) and isinstance(expr.object, Identifier):
            line = expr.span.line if expr.span else 1
            col = expr.span.column if expr.span else 1
            check_member(expr.object.name, expr.name, local_types, current_class, line, col)
        for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child, local_types, current_class)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, Expr):
                    walk_expr(a, local_types, current_class)

    def walk_stmts(
        stmts: list[Any],
        local_types: dict[str, str],
        current_class: str | None,
    ) -> None:
        local_types = dict(local_types)
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                if "." in stmt.name:
                    recv, _, member = stmt.name.rpartition(".")
                    if "." not in recv:
                        check_member(recv, member, local_types, current_class, line, col, stmt.name)
                elif stmt.declare_type and stmt.declare_type != "var":
                    local_types[stmt.name] = stmt.declare_type
                elif stmt.declare_type == "var":
                    inferred = _infer_type(stmt.value)
                    if inferred:
                        local_types[stmt.name] = inferred
                walk_expr(stmt.value, local_types, current_class)
            elif isinstance(stmt, (PrintStmt, ReturnStmt)):
                walk_expr(stmt.value, local_types, current_class)
            elif isinstance(stmt, ExprStmt):
                walk_expr(stmt.expr, local_types, current_class)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    method_types = dict(local_types)
                    for i, pname in enumerate(m.params):
                        ptype = m.param_types[i] if i < len(m.param_types) else ""
                        method_types[pname] = ptype or "int"
                    if m.body:
                        walk_stmts(m.body.statements, method_types, stmt.name)
            elif isinstance(stmt, FunctionDef):
                if stmt.body:
                    walk_stmts(stmt.body.statements, local_types, None)
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk_stmts(stmt.then_body.statements, local_types, current_class)
                if stmt.else_body:
                    walk_stmts(stmt.else_body.statements, local_types, current_class)
            elif isinstance(stmt, Block):
                walk_stmts(stmt.statements, local_types, current_class)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk_stmts(stmt.body.statements, local_types, current_class)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk_stmts(t.body.statements, local_types, current_class)

    walk_stmts(body, types, None)


def _check_interfaces(body: list[Any]) -> None:
    interfaces: dict[str, dict[str, int]] = {}
    for stmt in body:
        if isinstance(stmt, InterfaceDef):
            arities = dict(stmt.method_arities)
            for m in stmt.methods:
                arities.setdefault(m, 0)
            interfaces[stmt.name] = arities

    for stmt in body:
        if not isinstance(stmt, ClassDef):
            continue
        available: dict[str, int] = {}
        for m in stmt.methods:
            if m.is_constructor:
                continue
            available[m.name] = len(m.params)
        # Include inherited methods (single inheritance).
        parent = None
        for b in stmt.bases:
            if b not in interfaces:
                parent = b
                break
        seen_parents: set[str] = set()
        while parent and parent not in seen_parents:
            seen_parents.add(parent)
            parent_cls = next((c for c in body if isinstance(c, ClassDef) and c.name == parent), None)
            if parent_cls is None:
                break
            for m in parent_cls.methods:
                if not m.is_constructor:
                    available.setdefault(m.name, len(m.params))
            parent = None
            for b in parent_cls.bases:
                if b not in interfaces:
                    parent = b
                    break

        for b in stmt.bases:
            is_class = any(isinstance(c, ClassDef) and c.name == b for c in body)
            if is_class:
                continue
            line = stmt.span.line if stmt.span else 1
            if b not in interfaces:
                _transpile_error(
                    f"Unknown interface '{b}' implemented by class {stmt.name}.",
                    line,
                    1,
                    f"class {stmt.name}",
                )
            required = interfaces[b]
            for method_name, arity in required.items():
                if method_name not in available:
                    _transpile_error(
                        f"Class {stmt.name} must implement abstract method "
                        f"'{method_name}' from interface {b}.",
                        line,
                        1,
                        f"class {stmt.name}",
                    )
                if available[method_name] != arity:
                    _transpile_error(
                        f"Class {stmt.name} method '{method_name}' does not match "
                        f"interface {b} (expected {arity} parameter(s), "
                        f"found {available[method_name]}).",
                        line,
                        1,
                        f"class {stmt.name}",
                    )


def _check_shared_capture(body: list[Any]) -> None:
    """Policy B: outer captures are read-only inside tasks unless shared."""

    def walk(
        stmts: list[Any],
        *,
        declared: set[str],
        shared: set[str],
        in_task: bool,
        task_locals: set[str],
    ) -> None:
        declared = set(declared)
        shared = set(shared)
        task_locals = set(task_locals)
        for stmt in stmts:
            if isinstance(stmt, SharedDecl):
                declared.add(stmt.name)
                shared.add(stmt.name)
                continue
            if isinstance(stmt, AssignStmt):
                if stmt.declare_type or stmt.is_const or stmt.is_fix:
                    declared.add(stmt.name)
                    if in_task:
                        task_locals.add(stmt.name)
                elif in_task and _is_simple_name(stmt.name):
                    name = stmt.name
                    if name not in task_locals and name not in shared and name in declared:
                        line = stmt.span.line if stmt.span else 1
                        col = stmt.span.column if stmt.span else 1
                        _transpile_error(
                            f"Cannot assign to '{name}' inside task; captured variables are read-only. "
                            f"Declare it `shared` to allow cross-task mutation.",
                            line,
                            col,
                            f"{name} = ...",
                        )
            elif isinstance(stmt, AugAssignStmt):
                if in_task and _is_simple_name(stmt.name):
                    name = stmt.name
                    if name not in task_locals and name not in shared and name in declared:
                        line = stmt.span.line if stmt.span else 1
                        col = stmt.span.column if stmt.span else 1
                        _transpile_error(
                            f"Cannot assign to '{name}' inside task; captured variables are read-only. "
                            f"Declare it `shared` to allow cross-task mutation.",
                            line,
                            col,
                            f"{name}{stmt.op}",
                        )
            elif isinstance(stmt, ArrayDecl):
                declared.add(stmt.name)
                if in_task:
                    task_locals.add(stmt.name)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    locals_here = set(t.params)
                    if t.body:
                        walk(
                            t.body.statements,
                            declared=declared,
                            shared=shared,
                            in_task=True,
                            task_locals=locals_here,
                        )
            elif isinstance(stmt, FunctionDef):
                local_decl = set(declared) | set(stmt.params)
                if stmt.body:
                    walk(
                        stmt.body.statements,
                        declared=local_decl,
                        shared=shared,
                        in_task=False,
                        task_locals=set(),
                    )
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    local_decl = set(declared) | set(m.params)
                    if m.body:
                        walk(
                            m.body.statements,
                            declared=local_decl,
                            shared=shared,
                            in_task=False,
                            task_locals=set(),
                        )
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk(
                        stmt.then_body.statements,
                        declared=declared,
                        shared=shared,
                        in_task=in_task,
                        task_locals=task_locals,
                    )
                if stmt.else_body:
                    walk(
                        stmt.else_body.statements,
                        declared=declared,
                        shared=shared,
                        in_task=in_task,
                        task_locals=task_locals,
                    )
            elif isinstance(stmt, Block):
                walk(
                    stmt.statements,
                    declared=declared,
                    shared=shared,
                    in_task=in_task,
                    task_locals=task_locals,
                )
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(
                        stmt.body.statements,
                        declared=declared,
                        shared=shared,
                        in_task=in_task,
                        task_locals=task_locals,
                    )

    walk(body, declared=set(), shared=set(), in_task=False, task_locals=set())


def _check_await_placement(body: list[Any]) -> None:
    def has_await(expr: Expr | None) -> bool:
        if expr is None:
            return False
        if isinstance(expr, AwaitExpr):
            return True
        for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index", "target"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr) and has_await(child):
                return True
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, Expr) and has_await(a):
                    return True
        return False

    def walk(stmts: list[Any], *, in_task: bool) -> None:
        for stmt in stmts:
            if isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements, in_task=True)
                continue
            exprs: list[Expr | None] = []
            if isinstance(stmt, AssignStmt):
                exprs.append(stmt.value)
            elif isinstance(stmt, (PrintStmt, ReturnStmt)):
                exprs.append(stmt.value)
            elif isinstance(stmt, ExprStmt):
                exprs.append(stmt.expr)
            for e in exprs:
                if has_await(e) and not in_task:
                    line = stmt.span.line if stmt.span else 1
                    _transpile_error(
                        "`await` is only allowed inside a `task` body.",
                        line,
                        1,
                        "await",
                    )
            if isinstance(stmt, FunctionDef) and stmt.body:
                walk(stmt.body.statements, in_task=False)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements, in_task=False)
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk(stmt.then_body.statements, in_task=in_task)
                if stmt.else_body:
                    walk(stmt.else_body.statements, in_task=in_task)
            elif isinstance(stmt, Block):
                walk(stmt.statements, in_task=in_task)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(stmt.body.statements, in_task=in_task)

    walk(body, in_task=False)


def _check_seen_name_calls(body: list[Any], resolver: Any) -> None:
    builtins = {
        "print", "str", "int", "float", "bool", "len", "range", "super", "ABC", "abstractmethod",
    }
    imported = set(resolver.imported_names)
    exports = set(getattr(resolver, "exports", set()))
    declared = set(resolver.declared_variables)
    class_names = set(resolver.class_parents) | set(resolver.interfaces)
    seen = getattr(resolver, "seen_module_names", {})

    def check_name(name: str, line: int, column: int) -> None:
        if name in builtins or name in imported or name in exports or name in declared or name in class_names:
            return
        if name not in seen:
            return
        module_file, visibility, accessible = seen[name]
        if accessible:
            _transpile_error(
                f"'{name}' is defined in {module_file} but was not imported. "
                f"Import it with `import {name} from {module_file}` or `import all from {module_file}`.",
                line,
                column,
                f"{name}()",
            )
        where = {
            "module": "only within its own module",
            "package": "only within its package (same folder)",
            "global": "across the whole project",
        }.get(visibility, f"as {visibility}")
        _transpile_error(
            f"Access denied: '{name}' is defined in {module_file} but is not accessible here "
            f"({visibility}-scoped, visible {where}).",
            line,
            column,
            f"{name}()",
        )

    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            line = expr.span.line if expr.span else 1
            col = expr.span.column if expr.span else 1
            check_name(expr.callee.name, line, col)
        for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, Expr):
                    walk_expr(a)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                walk_expr(stmt.value)
            elif isinstance(stmt, (PrintStmt, ReturnStmt)):
                walk_expr(stmt.value)
            elif isinstance(stmt, ExprStmt):
                walk_expr(stmt.expr)
            elif isinstance(stmt, FunctionDef):
                if stmt.body:
                    walk(stmt.body.statements)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements)
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

    walk(body)


def _array_element_ok(elem_type: str, expr: Expr) -> bool:
    if not isinstance(expr, Literal):
        return True  # non-literals: leave to runtime / legacy
    if elem_type == "bool":
        return expr.kind == "bool" or expr.text in {"true", "false", "True", "False"}
    if elem_type == "string":
        return expr.kind == "string"
    if elem_type == "char":
        return expr.kind == "char"
    if elem_type == "int":
        return expr.kind == "int"
    if elem_type == "float":
        return expr.kind in {"int", "float"}
    return True


def _array_element_error(elem_type: str, expr: Expr) -> str:
    value = getattr(expr, "text", "?")
    if elem_type == "bool":
        return f"Bool array elements must be true or false, got '{value}'."
    if elem_type == "string":
        return f"String array elements must be string literals, got '{value}'."
    if elem_type == "char":
        return f"Char array elements must be single characters, got '{value}'."
    if elem_type == "int":
        return f"Int array elements must be integers, got '{value}'."
    if elem_type == "float":
        return f"Float array elements must be numbers, got '{value}'."
    return f"Unsupported array element type '{elem_type}'."


def _check_arrays(body: list[Any]) -> None:
    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ArrayDecl):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                elems: list[Expr] = []
                if isinstance(stmt.value, ArrayLiteral):
                    elems = list(stmt.value.elements)
                elif stmt.value is not None:
                    _transpile_error(
                        f"Array '{stmt.name}' must be initialized with a list literal like "
                        f"`[{stmt.elem_type} values...]`.",
                        line,
                        col,
                        f"{stmt.elem_type}[] {stmt.name}",
                    )
                if stmt.size is not None:
                    if len(elems) > stmt.size:
                        _transpile_error(
                            "Array index out of bounds, trying to place a value outside the array "
                            f"(capacity {stmt.size}, got {len(elems)} values).",
                            line,
                            col,
                            f"{stmt.elem_type}[{stmt.size}] {stmt.name}",
                        )
                    if len(elems) != stmt.size:
                        _transpile_error(
                            f"Array '{stmt.name}' expects exactly {stmt.size} elements, got {len(elems)}.",
                            line,
                            col,
                            f"{stmt.elem_type}[{stmt.size}] {stmt.name}",
                        )
                for el in elems:
                    if not _array_element_ok(stmt.elem_type, el):
                        _transpile_error(
                            _array_element_error(stmt.elem_type, el),
                            line,
                            col,
                            f"{stmt.elem_type}[] {stmt.name}",
                        )
            elif isinstance(stmt, FunctionDef) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements)
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

    walk(body)


def _check_class_member_modifiers(body: list[Any]) -> None:
    for stmt in body:
        if not isinstance(stmt, ClassDef):
            continue
        for f in stmt.fields:
            if f.access:
                continue
            line = f.span.line if f.span else (stmt.span.line if stmt.span else 1)
            _transpile_error(
                "Class member declarations require an access modifier. Use public/private/protected/module.",
                line,
                1,
                f"{f.type_name} {f.name}".strip(),
            )
        for m in stmt.methods:
            if m.access:
                continue
            line = m.span.line if m.span else (stmt.span.line if stmt.span else 1)
            _transpile_error(
                "Class member declarations require an access modifier. Use public/private/protected/module.",
                line,
                1,
                m.name,
            )
