"""Semantic checks on AST (types, scopes, await DAG, library boundary)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .ast_nodes import (
    ArrayAlloc,
    ArrayDecl,
    ArrayLiteral,
    AssignStmt,
    AtomicDecl,
    AugAssignStmt,
    AwaitExpr,
    BinaryOp,
    Block,
    BraceLiteral,
    BreakStmt,
    Call,
    Cast,
    ClassDef,
    DataDef,
    DictLiteral,
    EnumDef,
    EntityDef,
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
    Index,
    KeywordArg,
    LambdaExpr,
    Literal,
    Member,
    Module,
    PrintStmt,
    PropagateExpr,
    RepeatStmt,
    ResultCtor,
    ResultPattern,
    ReturnStmt,
    ContinueStmt,
    SharedDecl,
    StructDef,
    SwitchCase,
    SwitchExpr,
    SwitchStmt,
    TasksBlock,
    TraitDef,
    TraitRequire,
    TraitUse,
    TraitRequire,
    TupleLiteral,
    UnaryOp,
    WhileStmt,
)

_TYPED_INTERP = re.compile(r"#([sficbo])\{([^}]+)\}")
_WIDTH_ALIASES = frozenset({"byte", "nibble", "int16", "int32", "int64", "dword"})
_INT_LIKE = frozenset({"int"}) | _WIDTH_ALIASES
_WIDTH_MAX: dict[str, int] = {
    "nibble": (1 << 4) - 1,
    "byte": (1 << 8) - 1,
    "int16": (1 << 16) - 1,
    "int32": (1 << 32) - 1,
    "dword": (1 << 32) - 1,
    "int64": (1 << 64) - 1,
}
_PRIMITIVES = frozenset({"int", "float", "char", "string", "bool"}) | _WIDTH_ALIASES
_SPEC_TYPES: dict[str, set[str]] = {
    "s": {"string"},
    "i": set(_INT_LIKE),
    "f": {"float"},
    "c": {"char"},
    "b": {"bool"},
    "o": set(),
}
_BITWISE_BINOPS = frozenset({"&", "|", "^", "<<", ">>"})
_INT_ARITH_BINOPS = frozenset({"//", "**"})


def _is_simple_name(name: str) -> bool:
    """True for bare identifiers; false for member/index lvalues."""
    return "." not in name and "[" not in name


def analyze(
    module: Module,
    *,
    source_path: Path | None = None,
    allow_runtime_introspection: bool = False,
    is_entrypoint: bool = False,
) -> Module:
    """Validate module; raise TranspileError on known AST-checkable faults.

    Non-fatal issues are appended to ``module.analysis_warnings``.
    """
    from .transpiler import TranspileWarning

    warnings: list[TranspileWarning] = []
    module.analysis_warnings = warnings
    _reject_let(module)
    _check_return_types(module.body)
    declared: set[str] = set()
    constants: set[str] = set()
    types: dict[str, str] = {}
    fixed: set[str] = set()
    import_resolver = _seed_imports(
        module,
        source_path,
        declared,
        constants,
        types,
        fixed,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    class_parents = _class_parents_map(module.body)
    struct_info = _struct_info_map(module.body)
    # `data` types participate in the same value/fix/copy SA as fix structs.
    for stmt in module.body:
        if isinstance(stmt, DataDef):
            struct_info[stmt.name] = {
                "type_fix": True,
                "fields": [f.name for f in stmt.fields],
                "access": {f.name: "public" for f in stmt.fields},
                "types": {f.name: f.type_name for f in stmt.fields},
                "fix_fields": {f.name for f in stmt.fields},
                "defaults": {f.name for f in stmt.fields if f.default is not None},
                "kind": "data",
            }
    if import_resolver is not None:
        for name in getattr(import_resolver, "structs", set()):
            struct_info.setdefault(
                name,
                {
                    "type_fix": name in getattr(import_resolver, "struct_type_fix", set()),
                    "fields": list(import_resolver.struct_fields.get(name, [])),
                    "access": dict(import_resolver.struct_field_access.get(name, {})),
                    "types": dict(import_resolver.struct_field_types.get(name, {})),
                    "fix_fields": set(import_resolver.struct_field_fix.get(name, set())),
                    "defaults": set(import_resolver.struct_field_defaults.get(name, set())),
                },
            )
    enum_info = _enum_info_map(module.body, warnings=warnings)
    if import_resolver is not None:
        for name in getattr(import_resolver, "enums", set()):
            enum_info.setdefault(
                name,
                {
                    "members": list(import_resolver.enum_members.get(name, [])),
                    "value_kind": import_resolver.enum_value_kinds.get(name, "auto"),
                    "member_values": dict(
                        import_resolver.enum_member_values.get(name, {})
                    ),
                },
            )
    struct_names = set(struct_info)
    enum_names = set(enum_info)
    entity_names = {s.name for s in module.body if isinstance(s, EntityDef)}
    class_names = set(class_parents) | {
        s.name for s in module.body if isinstance(s, ClassDef)
    } | struct_names | enum_names | entity_names
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
    function_returns = {
        stmt.name: stmt.return_type
        for stmt in module.body
        if isinstance(stmt, FunctionDef)
    }
    function_params = {
        stmt.name: list(stmt.param_types)
        for stmt in module.body
        if isinstance(stmt, FunctionDef)
    }
    # Built-in recoverable parsers (Python emit target defines acceptance).
    function_returns.setdefault("parseFloat", "result<float, string>")
    function_params.setdefault("parseFloat", ["string"])
    function_returns.setdefault("parseInt", "result<int, string>")
    function_params.setdefault("parseInt", ["string"])
    # Console I/O (like print): no import required.
    function_returns.setdefault("input", "string")
    function_params.setdefault("input", ["string"])  # optional; arity checked separately
    if import_resolver is not None:
        function_returns.update(import_resolver.function_returns)
        function_params.update(import_resolver.function_params)
    _check_results(
        module.body,
        types=types,
        function_returns=function_returns,
        function_params=function_params,
        class_names=class_names,
        class_parents=class_parents,
        class_implements=class_implements,
        interfaces=interfaces,
        is_entrypoint=is_entrypoint,
    )
    _check_nullability(
        module,
        types=types,
        function_returns=function_returns,
        function_params=function_params,
        class_parents=class_parents,
        class_implements=class_implements,
        interfaces=interfaces,
        warnings=warnings,
    )
    _check_width_ranges(module.body, types=types)
    _check_int_ops(module.body, types=types, class_names=class_names)
    _check_structs(module.body, types=types, fixed=fixed, struct_info=struct_info)
    _check_data_and_entities(module.body, types=types)
    _check_enums(module.body, types=types, fixed=fixed, enum_info=enum_info)
    _check_switch(
        module.body,
        types=types,
        enum_info=enum_info,
        warnings=warnings,
        class_names=class_names,
    )
    _check_oop(module.body, types=types, resolver=import_resolver)
    _check_traits(module.body, types=types)
    _check_abstract_classes(module.body)
    _check_interfaces(module.body)
    _check_lambdas(module.body, types=types)
    _check_atomics(module.body, types=types)
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


def _transpile_warning(
    warnings: list,
    message: str,
    line: int = 1,
    column: int = 1,
    code_line: str = "",
    *,
    code: str | None = None,
    suggested_fix: str | None = None,
    tips: list[str] | None = None,
) -> None:
    from .transpiler import TranspileWarning

    warnings.append(
        TranspileWarning(
            message,
            line,
            column,
            code_line,
            code=code,
            suggested_fix=suggested_fix,
            tips=tips,
        )
    )


def _literal_int_value(expr: Expr | None) -> int | None:
    """Parse an int literal text (`0b…` / `0x…` / decimal with `_`)."""
    if not isinstance(expr, Literal) or expr.kind != "int":
        return None
    try:
        return int(expr.text.replace("_", ""), 0)
    except ValueError:
        return None


def _expr_is_int_like(
    expr: Expr | None,
    types: dict[str, str],
    class_names: set[str],
) -> bool | None:
    """True/False when known; None when type cannot be determined."""
    if expr is None:
        return None
    if isinstance(expr, Literal):
        if expr.kind == "int":
            return True
        if expr.kind in {"float", "string", "char", "bool", "null"}:
            return False
        return None
    if isinstance(expr, Identifier):
        t = _base_type_name(types.get(expr.name, ""))
        if t in _INT_LIKE:
            return True
        if t in {"float", "string", "char", "bool"}:
            return False
        return None
    if isinstance(expr, UnaryOp) and expr.op in {"+", "-", "~"}:
        return _expr_is_int_like(expr.operand, types, class_names)
    if isinstance(expr, BinaryOp) and expr.op in (
        _BITWISE_BINOPS | _INT_ARITH_BINOPS | {"+", "-", "*", "/", "%"}
    ):
        left = _expr_is_int_like(expr.left, types, class_names)
        right = _expr_is_int_like(expr.right, types, class_names)
        if left is False or right is False:
            return False
        if left is True and right is True:
            return True
        return None
    inferred = _infer_type(expr, class_names)
    if inferred in _INT_LIKE:
        return True
    if inferred in {"float", "string", "char", "bool"}:
        return False
    return None


def _check_width_ranges(body: list[Any], *, types: dict[str, str]) -> None:
    """Reject literal assigns outside unsigned width-alias ranges."""

    def check_assign(declare_type: str | None, value: Expr | None, line: int, col: int) -> None:
        if not declare_type:
            return
        base = _base_type_name(declare_type)
        if base not in _WIDTH_MAX:
            return
        lit = _literal_int_value(value)
        if lit is None:
            return
        if lit < 0 or lit > _WIDTH_MAX[base]:
            _transpile_error(
                f"Value {lit} is out of range for {base} "
                f"(unsigned 0..{_WIDTH_MAX[base]}).",
                line,
                col,
                declare_type,
            )

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                check_assign(stmt.declare_type, stmt.value, line, col)
            elif isinstance(stmt, SharedDecl):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                check_assign(stmt.declare_type, stmt.value, line, col)
            elif isinstance(stmt, AtomicDecl):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                check_assign(stmt.declare_type, stmt.value, line, col)
            elif isinstance(stmt, FunctionDef) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, (ClassDef, EntityDef)):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, SwitchStmt):
                for case in stmt.cases:
                    if case.body:
                        walk(case.body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(stmt.body.statements)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements)

    walk(body)


def _check_int_ops(
    body: list[Any],
    *,
    types: dict[str, str],
    class_names: set[str],
) -> None:
    """Require int-like operands for bitwise / shift / // / ** / ~."""

    def require_int(expr: Expr | None, op: str, line: int, col: int) -> None:
        ok = _expr_is_int_like(expr, types, class_names)
        if ok is False:
            _transpile_error(
                f"Operator '{op}' requires int-like operands "
                f"(int / byte / nibble / int16 / int32 / int64 / dword).",
                line,
                col,
                op,
            )

    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        line = expr.span.line if expr.span else 1
        col = expr.span.column if expr.span else 1
        if isinstance(expr, UnaryOp) and expr.op == "~":
            require_int(expr.operand, "~", line, col)
            walk_expr(expr.operand)
            return
        if isinstance(expr, BinaryOp) and expr.op in (_BITWISE_BINOPS | _INT_ARITH_BINOPS):
            require_int(expr.left, expr.op, line, col)
            require_int(expr.right, expr.op, line, col)
        if isinstance(expr, SwitchExpr):
            walk_expr(expr.subject)
            for case in expr.cases:
                for lab in case.labels:
                    walk_expr(lab)
                walk_expr(case.value)
            return
        for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, KeywordArg):
                    walk_expr(a.value)
                elif isinstance(a, Expr):
                    walk_expr(a)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                walk_expr(stmt.value)
            elif isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt, AugAssignStmt)):
                walk_expr(getattr(stmt, "value", None) or getattr(stmt, "expr", None))
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond)
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, SwitchStmt):
                walk_expr(stmt.subject)
                for case in stmt.cases:
                    for lab in case.labels:
                        walk_expr(lab)
                    if case.body:
                        walk(case.body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if isinstance(stmt, WhileStmt):
                    walk_expr(stmt.cond)
                elif isinstance(stmt, ForEachStmt):
                    walk_expr(stmt.iterable)
                if stmt.body:
                    walk(stmt.body.statements)
            elif isinstance(stmt, FunctionDef) and stmt.body:
                local = dict(types)
                for i, p in enumerate(stmt.params):
                    if i < len(stmt.param_types) and stmt.param_types[i]:
                        local[p] = stmt.param_types[i]
                _check_int_ops(stmt.body.statements, types=local, class_names=class_names)
            elif isinstance(stmt, (ClassDef, EntityDef)):
                for m in stmt.methods:
                    if m.body:
                        _check_int_ops(m.body.statements, types=dict(types), class_names=class_names)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements)

    walk(body)


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
    *,
    allow_runtime_introspection: bool = False,
) -> Any | None:
    """Pull imported names (and const/fix) into scope when source_path is known."""
    if source_path is None:
        return None
    from .transpiler import TranspileError

    if source_path is None:
        return None
    from . import imports as imports_mod

    resolver = imports_mod.make_resolver(
        module.source,
        source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
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
    primitives = {
        "int",
        "float",
        "char",
        "string",
        "bool",
        "byte",
        "nibble",
        "int16",
        "int32",
        "int64",
        "dword",
        "list",
        "dict",
        "tuple",
        "set",
        "lambda",
        "result",
        "nullable",
        "var",
    }
    if not base or base in primitives:
        return True
    if base in resolver.class_parents or base in resolver.interfaces or base in resolver.exports:
        return True
    if base in getattr(resolver, "type_modules", {}):
        return True
    if not resolver.allow_runtime_introspection and resolver.imported_modules:
        # Safe analysis cannot inspect third-party modules. Treat the type as
        # unverified instead of importing package code or inventing an error.
        return True
    site_paths = resolver._deps_paths()
    for mod in sorted(set(resolver.imported_modules.values())):
        cls = _find_class_in_package(
            mod,
            base,
            site_paths,
            allow_runtime_imports=resolver.allow_runtime_introspection,
        )
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
            allow_runtime_imports=resolver.allow_runtime_introspection,
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
        if isinstance(stmt, ClassDef):
            parent: str | None = None
            for b in stmt.bases:
                if b not in interfaces:
                    parent = b
                    break
            if stmt.parent:
                parent = stmt.parent
            parents[stmt.name] = parent
        elif isinstance(stmt, EntityDef):
            parents[stmt.name] = stmt.parent or None
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
    # `var` is the dynamic escape hatch for foreign/driver values (e.g. SQL cells).
    if declared == "var":
        return True
    declared_inner = _nullable_inner(declared)
    actual_inner = _nullable_inner(actual)
    if declared_inner is not None:
        if actual == "null":
            return True
        if actual_inner is not None:
            # Nullable generics are invariant; only the canonical exact type
            # was accepted above.
            return False
        return _is_assignable_type(
            actual,
            declared_inner,
            class_parents,
            class_implements=class_implements,
            interfaces=interfaces,
        )
    if actual == "null":
        return False
    if actual_inner is not None:
        return False
    a_base = _base_type_name(actual)
    d_base = _base_type_name(declared)
    if "result" in {a_base, d_base}:
        return False
    if a_base == d_base:
        return True
    if a_base in _INT_LIKE and d_base in _INT_LIKE:
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
                if m.is_abstract:
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
        elif isinstance(node, SwitchStmt):
            for case in node.cases:
                if case.body:
                    _check_return_types(case.body.statements)
        elif isinstance(node, Block):
            _check_return_types(node.statements)
        elif isinstance(node, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
            if node.body:
                _check_return_types(node.body.statements)


def _check_fn_returns(return_type: str, body: Block | None, line: int) -> None:
    if not body:
        return
    is_void = return_type == "void"

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ReturnStmt) and stmt.value is not None:
                if is_void:
                    _transpile_error(
                        "A `void` method cannot return a value "
                        "(use bare `return` or omit the return).",
                        stmt.span.line if stmt.span else line,
                        stmt.span.column if stmt.span else 1,
                        "return",
                        code="pys.void-return",
                    )
                elif not return_type:
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
            elif isinstance(stmt, SwitchStmt):
                for case in stmt.cases:
                    if case.body:
                        walk(case.body.statements)
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
    # EnumName.MEMBER → EnumName (enums are registered in class_names).
    if isinstance(expr, Member) and isinstance(expr.object, Identifier):
        if class_names and expr.object.name in class_names:
            return expr.object.name
    if isinstance(expr, SwitchExpr):
        arm_types: list[str] = []
        for case in expr.cases:
            t = _infer_type(case.value, class_names)
            if t is None:
                return None
            arm_types.append(t)
        if not arm_types:
            return None
        first = arm_types[0]
        if all(t == first for t in arm_types):
            return first
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
    if isinstance(expr, TupleLiteral):
        return "tuple"
    if isinstance(expr, DictLiteral):
        return "dict"
    if isinstance(expr, BraceLiteral):
        return None
    if isinstance(expr, ArrayLiteral):
        return "list"
    return None


def _check_brace_literal_assign(
    value: BraceLiteral,
    expected: str | None,
    *,
    line: int,
    col: int,
    name: str,
) -> None:
    """Validate unresolved `{…}` against an expected binding type."""
    tip_type = (
        "Type the binding: `dict<K, V> name = {}`, `set<T> name = {}`, "
        "or `list<T> name = []`."
    )
    if not expected or expected == "var":
        shape = "{}" if not value.elements else "{…}"
        _transpile_error(
            f"Ambiguous brace literal `{shape}` — PYS needs a typed binding to "
            "choose dict, set, list, or array.",
            line,
            col,
            f"var {name} = {shape}" if expected == "var" else f"{name} = {shape}",
            tips=[tip_type],
        )
    base = _base_type_name(expected)
    if base == "dict":
        if value.elements:
            _transpile_error(
                "Dict literals use `key: value` pairs, not a bare element list. "
                'Example: `dict<string, int> ages = {"Ada": 36}`.',
                line,
                col,
                f"{expected} {name} = {{…}}",
                tips=['Use keyed entries: `{"key": value}`.'],
            )
        return
    if base == "set":
        return
    if base == "list":
        return
    if base == "tuple":
        _transpile_error(
            "Tuple values use parentheses: `(a, b)` or `(a,)`, not braces.",
            line,
            col,
            f"{expected} {name} = (…)",
            tips=["Write `tuple<…> name = (a, b)`."],
        )
    _transpile_error(
        f"Brace literal cannot initialize '{name}' of type {expected}.",
        line,
        col,
        f"{expected} {name} = {{…}}",
        tips=[tip_type],
    )


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


def _result_type_parts(type_name: str | None) -> tuple[str, str] | None:
    if not type_name or _base_type_name(type_name) != "result":
        return None
    args = _extract_type_args(type_name)
    if len(args) != 2:
        return None
    return args[0], args[1]


def _nullable_inner(type_name: str | None) -> str | None:
    """Return T for canonical ``nullable<T>`` strings."""
    if not type_name or _base_type_name(type_name) != "nullable":
        return None
    args = _extract_type_args(type_name)
    if len(args) != 1:
        return None
    return args[0]


def _check_nullability(
    module: Module,
    *,
    types: dict[str, str],
    function_returns: dict[str, str],
    function_params: dict[str, list[str]],
    class_parents: dict[str, str | None],
    class_implements: dict[str, list[str]],
    interfaces: set[str],
    warnings: list,
) -> None:
    """Enforce nullable use and maintain conservative lexical flow facts."""

    module.analysis_narrowed_types = {}
    shared_names = {
        stmt.name for stmt in module.body if isinstance(stmt, SharedDecl)
    }

    def storage_path(expr: Expr | None) -> str | None:
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, Member):
            parent = storage_path(expr.object)
            if parent:
                return f"{parent}.{expr.name}"
        return None

    def declared_type(expr: Expr | None, env: dict[str, str]) -> str | None:
        path = storage_path(expr)
        if path and path in env:
            return env[path]
        if isinstance(expr, Literal):
            return expr.kind
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            return function_returns.get(expr.callee.name)
        return _infer_type(expr)

    def expr_type(
        expr: Expr | None,
        env: dict[str, str],
        present: set[str],
    ) -> str | None:
        path = storage_path(expr)
        dtype = declared_type(expr, env)
        inner = _nullable_inner(dtype)
        if path and inner is not None and path in present:
            if expr and expr.span:
                module.analysis_narrowed_types[
                    f"{expr.span.line}:{expr.span.column}"
                ] = inner
            return inner
        return dtype

    def nullable_use_error(
        expr: Expr,
        dtype: str,
        operation: str,
    ) -> None:
        path = storage_path(expr) or "value"
        line = expr.span.line if expr.span else 1
        col = expr.span.column if expr.span else 1
        _transpile_error(
            f"'{path}' has type {dtype} and may be null before {operation}.",
            line,
            col,
            path,
            code="pys.nullable-use-before-check",
            suggested_fix=(
                f"if ({path} != null) {{\n    # use {path} here\n}}"
                if isinstance(expr, Identifier) and path not in shared_names
                else None
            ),
            tips=[f"Check `{path} != null` and handle both paths."],
        )

    def require_present(
        expr: Expr | None,
        env: dict[str, str],
        present: set[str],
        operation: str,
    ) -> None:
        if not isinstance(expr, Expr):
            return
        dtype = declared_type(expr, env)
        path = storage_path(expr)
        if _nullable_inner(dtype) is not None and (not path or path not in present):
            nullable_use_error(expr, dtype or "nullable<?>", operation)
            return
        # Record successful proofs for IDE hover (declared → narrowed).
        expr_type(expr, env, present)

    def null_comparison(
        expr: Expr | None,
        env: dict[str, str],
    ) -> tuple[str, bool] | None:
        if not isinstance(expr, BinaryOp) or expr.op not in {"==", "!=", "<>"}:
            return None
        left_null = isinstance(expr.left, Literal) and expr.left.kind == "null"
        right_null = isinstance(expr.right, Literal) and expr.right.kind == "null"
        target = expr.right if left_null else expr.left if right_null else None
        path = storage_path(target)
        if not path:
            return None
        dtype = declared_type(target, env)
        if dtype and _nullable_inner(dtype) is None and dtype not in {"var", "null"}:
            line = target.span.line if target and target.span else 1
            col = target.span.column if target and target.span else 1
            _transpile_warning(
                warnings,
                f"'{path}' has non-null type {dtype}, so this null check is redundant.",
                line,
                col,
                path,
                code="pys.null-redundant-check",
                tips=[
                    "Remove the check, or make the declaration nullable if absence is intentional."
                ],
            )
        if _nullable_inner(dtype) is None:
            return None
        # True means the target is present when the comparison is true.
        return path, expr.op in {"!=", "<>"}

    def condition_facts(
        expr: Expr | None,
        env: dict[str, str],
    ) -> tuple[set[str], set[str]]:
        comparison = null_comparison(expr, env)
        if comparison:
            path, true_is_present = comparison
            if path in shared_names:
                return set(), set()
            if true_is_present:
                return {path}, set()
            return set(), {path}
        if isinstance(expr, UnaryOp) and expr.op == "not":
            when_true, when_false = condition_facts(expr.operand, env)
            return when_false, when_true
        return set(), set()

    def walk_expr(
        expr: Expr | None,
        env: dict[str, str],
        present: set[str],
    ) -> None:
        if expr is None:
            return
        if isinstance(expr, BinaryOp):
            if expr.op in {"and", "or"}:
                walk_expr(expr.left, env, present)
                when_true, when_false = condition_facts(expr.left, env)
                right_present = set(present)
                right_present |= when_true if expr.op == "and" else when_false
                walk_expr(expr.right, env, right_present)
                return
            if null_comparison(expr, env):
                # The compared storage is legal; its receiver still must be safe.
                if isinstance(expr.left, Member):
                    walk_expr(expr.left.object, env, present)
                if isinstance(expr.right, Member):
                    walk_expr(expr.right.object, env, present)
                return
            if expr.op not in {"==", "!=", "<>"}:
                require_present(expr.left, env, present, f"operator '{expr.op}'")
                require_present(expr.right, env, present, f"operator '{expr.op}'")
            walk_expr(expr.left, env, present)
            walk_expr(expr.right, env, present)
            return
        if isinstance(expr, Member):
            require_present(expr.object, env, present, f"member access '.{expr.name}'")
            walk_expr(expr.object, env, present)
            return
        if isinstance(expr, Index):
            require_present(expr.object, env, present, "indexing")
            walk_expr(expr.object, env, present)
            walk_expr(expr.index, env, present)
            return
        if isinstance(expr, Call):
            walk_expr(expr.callee, env, present)
            expected: list[str] = []
            if isinstance(expr.callee, Identifier):
                expected = function_params.get(expr.callee.name, [])
            for idx, arg in enumerate(expr.args):
                value = arg.value if isinstance(arg, KeywordArg) else arg
                if idx < len(expected) and expected[idx] and expected[idx] != "var":
                    actual = expr_type(value, env, present)
                    if actual and not _is_assignable_type(
                        actual,
                        expected[idx],
                        class_parents,
                        class_implements=class_implements,
                        interfaces=interfaces,
                    ):
                        if _nullable_inner(actual) is not None:
                            require_present(
                                value,
                                env,
                                present,
                                f"passing to non-null parameter {idx + 1}",
                            )
                        else:
                            _transpile_error(
                                f"Argument {idx + 1} has type {actual}; "
                                f"expected {expected[idx]}.",
                                value.span.line if value.span else 1,
                                value.span.column if value.span else 1,
                                "argument",
                                code="pys.argument-type",
                            )
                walk_expr(value, env, present)
            # A call on a receiver may mutate its fields. Retain local facts but
            # conservatively invalidate member-path facts.
            present.difference_update({path for path in present if "." in path})
            return
        for attr in ("operand", "value", "expr", "cond", "object", "index"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child, env, present)
        for attr in ("args", "elements"):
            children = getattr(expr, attr, None)
            if isinstance(children, list):
                for child in children:
                    value = child.value if isinstance(child, KeywordArg) else child
                    if isinstance(value, Expr):
                        walk_expr(value, env, present)
        entries = getattr(expr, "entries", None)
        if isinstance(entries, list):
            for key, value in entries:
                walk_expr(key, env, present)
                walk_expr(value, env, present)

    def block_exits(stmts: list[Any]) -> bool:
        if not stmts:
            return False
        last = stmts[-1]
        if isinstance(last, (ReturnStmt, BreakStmt, ContinueStmt)):
            return True
        if (
            isinstance(last, ExprStmt)
            and isinstance(last.expr, Call)
            and isinstance(last.expr.callee, Identifier)
            and last.expr.callee.name == "panic"
        ):
            return True
        if isinstance(last, IfStmt) and last.then_body and last.else_body:
            else_stmts = (
                last.else_body.statements
                if isinstance(last.else_body, Block)
                else [last.else_body]
            )
            return block_exits(last.then_body.statements) and block_exits(else_stmts)
        return False

    def walk_block(
        stmts: list[Any],
        env: dict[str, str],
        present: set[str],
        *,
        return_type: str = "",
    ) -> tuple[dict[str, str], set[str], bool]:
        local_env = dict(env)
        facts = set(present)
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                walk_expr(stmt.value, local_env, facts)
                target_type = stmt.declare_type or local_env.get(stmt.name)
                if stmt.declare_type:
                    local_env[stmt.name] = stmt.declare_type
                facts.discard(stmt.name)
                if _nullable_inner(target_type) is not None:
                    actual = expr_type(stmt.value, local_env, facts)
                    if actual not in {None, "null"} and _nullable_inner(actual) is None:
                        facts.add(stmt.name)
                elif target_type and stmt.value is not None:
                    actual = expr_type(stmt.value, local_env, facts)
                    if actual and not _is_assignable_type(
                        actual,
                        target_type,
                        class_parents,
                        class_implements=class_implements,
                        interfaces=interfaces,
                    ):
                        if _nullable_inner(actual) is not None:
                            require_present(
                                stmt.value, local_env, facts, "assignment to a non-null target"
                            )
                continue
            if isinstance(stmt, PrintStmt):
                walk_expr(stmt.value, local_env, facts)
                continue
            if isinstance(stmt, ExprStmt):
                walk_expr(stmt.expr, local_env, facts)
                if (
                    isinstance(stmt.expr, Call)
                    and isinstance(stmt.expr.callee, Identifier)
                    and stmt.expr.callee.name == "panic"
                ):
                    return local_env, facts, True
                continue
            if isinstance(stmt, ReturnStmt):
                walk_expr(stmt.value, local_env, facts)
                actual = expr_type(stmt.value, local_env, facts)
                if return_type and return_type != "void" and actual and not _is_assignable_type(
                    actual,
                    return_type,
                    class_parents,
                    class_implements=class_implements,
                    interfaces=interfaces,
                ):
                    if _nullable_inner(actual) is not None:
                        require_present(
                            stmt.value, local_env, facts, "return from a non-null function"
                        )
                    _raise_assignment_mismatch(
                        actual=actual,
                        declared_type=return_type,
                        name="return value",
                        line=stmt.span.line if stmt.span else 1,
                        col=stmt.span.column if stmt.span else 1,
                        declaration=False,
                    )
                return local_env, facts, True
            if isinstance(stmt, IfStmt):
                walk_expr(stmt.cond, local_env, facts)
                direct_type = expr_type(stmt.cond, local_env, facts)
                if _nullable_inner(direct_type) is not None:
                    require_present(stmt.cond, local_env, facts, "use as a boolean condition")
                true_add, false_add = condition_facts(stmt.cond, local_env)
                if stmt.negated:
                    true_add, false_add = false_add, true_add
                then_facts = set(facts) | true_add
                then_env, then_out, then_exits = walk_block(
                    stmt.then_body.statements if stmt.then_body else [],
                    local_env,
                    then_facts,
                    return_type=return_type,
                )
                if stmt.else_body:
                    else_stmts = (
                        stmt.else_body.statements
                        if isinstance(stmt.else_body, Block)
                        else [stmt.else_body]
                    )
                    else_env, else_out, else_exits = walk_block(
                        else_stmts,
                        local_env,
                        set(facts) | false_add,
                        return_type=return_type,
                    )
                else:
                    else_env, else_out, else_exits = dict(local_env), set(facts) | false_add, False
                if then_exits and else_exits:
                    return local_env, facts, True
                if then_exits:
                    local_env, facts = else_env, else_out
                elif else_exits:
                    local_env, facts = then_env, then_out
                else:
                    facts = then_out & else_out
                    local_env.update(
                        {
                            name: dtype
                            for name, dtype in then_env.items()
                            if else_env.get(name) == dtype
                        }
                    )
                continue
            if isinstance(stmt, SwitchStmt):
                walk_expr(stmt.subject, local_env, facts)
                subject_path = storage_path(stmt.subject)
                subject_type = declared_type(stmt.subject, local_env)
                nullable_subject = _nullable_inner(subject_type) is not None
                has_null_case = any(
                    isinstance(label, Literal) and label.kind == "null"
                    for case in stmt.cases
                    for label in case.labels
                )
                surviving: list[set[str]] = []
                for case in stmt.cases:
                    case_facts = set(facts)
                    is_null_case = any(
                        isinstance(label, Literal) and label.kind == "null"
                        for label in case.labels
                    )
                    if subject_path and nullable_subject:
                        if is_null_case:
                            case_facts.discard(subject_path)
                        elif not case.is_default or has_null_case:
                            case_facts.add(subject_path)
                    _, case_out, case_exits = walk_block(
                        case.body.statements if case.body else [],
                        local_env,
                        case_facts,
                        return_type=return_type,
                    )
                    if not case_exits:
                        surviving.append(case_out)
                if surviving:
                    facts = set.intersection(*surviving)
                continue
            if isinstance(stmt, (WhileStmt, RepeatStmt, ForRangeStmt, ForEachStmt)):
                cond = getattr(stmt, "cond", None)
                walk_expr(cond, local_env, facts)
                loop_env = dict(local_env)
                if isinstance(stmt, ForEachStmt) and stmt.var_type:
                    loop_env[stmt.var] = stmt.var_type
                if stmt.body:
                    walk_block(
                        stmt.body.statements,
                        loop_env,
                        set(facts),
                        return_type=return_type,
                    )
                # A loop can execute zero or many times; no inner proof survives.
                continue
            if isinstance(stmt, Block):
                walk_block(stmt.statements, local_env, set(facts), return_type=return_type)
        return local_env, facts, block_exits(stmts)

    global_env = dict(types)
    for stmt in module.body:
        if isinstance(stmt, FunctionDef) and stmt.body:
            env = dict(global_env)
            env.update(zip(stmt.params, stmt.param_types))
            walk_block(stmt.body.statements, env, set(), return_type=stmt.return_type)
        elif isinstance(stmt, (ClassDef, EntityDef)):
            fields = {
                f.name: f.type_name for f in getattr(stmt, "fields", [])
            }
            for method in stmt.methods:
                if not method.body:
                    continue
                env = dict(global_env)
                env.update(zip(method.params, method.param_types))
                env["self"] = stmt.name
                env["this"] = stmt.name
                for name, dtype in fields.items():
                    env[f"self.{name}"] = dtype
                    env[f"this.{name}"] = dtype
                walk_block(
                    method.body.statements,
                    env,
                    set(),
                    return_type=method.return_type,
                )
    top_level = [
        stmt
        for stmt in module.body
        if not isinstance(stmt, (FunctionDef, ClassDef, EntityDef, StructDef, DataDef))
    ]
    walk_block(top_level, global_env, set())


def _check_results(
    body: list[Any],
    *,
    types: dict[str, str],
    function_returns: dict[str, str],
    function_params: dict[str, list[str]],
    class_names: set[str],
    class_parents: dict[str, str | None],
    class_implements: dict[str, list[str]],
    interfaces: set[str],
    is_entrypoint: bool,
) -> None:
    """Validate contextual result construction and postfix propagation."""

    reserved = {"ok", "err"}
    entry_error_type: str | None = None
    method_returns: dict[tuple[str, str], str] = {}
    method_params: dict[tuple[str, str], list[str]] = {}
    for stmt in body:
        if not isinstance(stmt, ClassDef):
            continue
        for method in stmt.methods:
            if method.return_type:
                method_returns[(stmt.name, method.name)] = method.return_type
            method_params[(stmt.name, method.name)] = list(method.param_types)

    def method_owner(type_name: str | None, method_name: str) -> str | None:
        owner = _base_type_name(type_name or "")
        seen: set[str] = set()
        while owner and owner not in seen:
            seen.add(owner)
            if (owner, method_name) in method_params:
                return owner
            owner = class_parents.get(owner) or ""
        return None

    def fail(
        message: str,
        expr: Expr | Any,
        *,
        code: str,
        tips: list[str] | None = None,
        suggested_fix: str | None = None,
    ) -> None:
        span = getattr(expr, "span", None)
        _transpile_error(
            message,
            span.line if span else 1,
            span.column if span else 1,
            "",
            code=code,
            tips=tips,
            suggested_fix=suggested_fix,
        )

    def check_name(name: str, node: Any) -> None:
        if name not in reserved:
            return
        fail(
            f"'{name}' is a reserved result constructor and cannot be redeclared.",
            node,
            code="pys.result-reserved",
            tips=["Choose a domain name that does not shadow PYS result syntax."],
        )

    def expr_type(
        expr: Expr | None,
        env: dict[str, str],
        *,
        return_type: str | None,
        scope_kind: str,
        expected_result: str | None = None,
    ) -> str | None:
        if expr is None:
            return None
        if isinstance(expr, Identifier):
            return env.get(expr.name)
        if isinstance(expr, Member):
            receiver_type = expr_type(
                expr.object,
                env,
                return_type=return_type,
                scope_kind=scope_kind,
            )
            owner = method_owner(receiver_type, expr.name)
            return method_returns.get((owner, expr.name)) if owner else None
        if isinstance(expr, ResultCtor):
            expected_parts = _result_type_parts(expected_result)
            if expected_parts is None:
                fail(
                    f"`{expr.kind}(...)` needs an expected `result<T, E>` type.",
                    expr,
                    code="pys.result-context",
                    tips=[
                        "Declare a `result<T, E>` binding or return it from a "
                        "`result<T, E>` function."
                    ],
                )
            success_type, error_type = expected_parts
            if expr.kind == "ok":
                if expr.value is None:
                    if success_type != "void":
                        fail(
                            f"`ok()` is only valid for `result<void, E>`, not "
                            f"`{expected_result}`.",
                            expr,
                            code="pys.result-ok-value",
                            tips=[f"Pass a value of type `{success_type}` to `ok(...)`."],
                        )
                else:
                    actual = expr_type(
                        expr.value,
                        env,
                        return_type=return_type,
                        scope_kind=scope_kind,
                    )
                    if success_type == "void" or (
                        actual
                        and not _is_assignable_type(
                            actual,
                            success_type,
                            class_parents,
                            class_implements=class_implements,
                            interfaces=interfaces,
                        )
                    ):
                        fail(
                            f"Result success payload has type {actual or 'unknown'}, "
                            f"expected {success_type}.",
                            expr,
                            code="pys.result-success-type",
                        )
            else:
                actual = expr_type(
                    expr.value,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                )
                if actual and not _is_assignable_type(
                    actual,
                    error_type,
                    class_parents,
                    class_implements=class_implements,
                    interfaces=interfaces,
                ):
                    fail(
                        f"Result error payload has type {actual}, expected {error_type}.",
                        expr,
                        code="pys.result-error-type",
                    )
            return expected_result
        if isinstance(expr, PropagateExpr):
            nonlocal entry_error_type
            operand_type = expr_type(
                expr.operand,
                env,
                return_type=return_type,
                scope_kind=scope_kind,
            )
            operand_parts = _result_type_parts(operand_type)
            if operand_parts is None:
                fail(
                    f"`propagate` only applies to result values, not "
                    f"{operand_type or 'an unknown type'}.",
                    expr,
                    code="pys.propagate-type",
                    tips=["Remove `propagate` or make the expression return `result<T, E>`."],
                )
            if scope_kind == "task":
                fail(
                    "`propagate` cannot cross a task boundary.",
                    expr,
                    code="pys.propagate-task",
                    tips=["Handle the result inside the task body."],
                )
            success_type, error_type = operand_parts
            if scope_kind == "entrypoint":
                if entry_error_type is None:
                    entry_error_type = error_type
                elif entry_error_type != error_type:
                    fail(
                        f"Entrypoint propagation mixes error type {error_type} "
                        f"with {entry_error_type}.",
                        expr,
                        code="pys.propagate-error-type",
                        tips=["Use exactly one error type at the entrypoint boundary."],
                    )
                return success_type
            enclosing_parts = _result_type_parts(return_type)
            if enclosing_parts is None:
                fail(
                    "`propagate` requires an enclosing function that returns "
                    "`result<T, E>`.",
                    expr,
                    code="pys.propagate-return",
                    tips=["Change the function return type or handle the result with `switch`."],
                )
            enclosing_error = enclosing_parts[1]
            if error_type != enclosing_error:
                fail(
                    f"Cannot propagate error type {error_type} from a function "
                    f"returning error type {enclosing_error}.",
                    expr,
                    code="pys.propagate-error-type",
                    tips=["Use exactly the same error type on both result types."],
                )
            return success_type
        if isinstance(expr, SwitchExpr):
            subject_type = expr_type(
                expr.subject,
                env,
                return_type=return_type,
                scope_kind=scope_kind,
            )
            result_parts = _result_type_parts(subject_type)
            arm_types: list[str | None] = []
            for case in expr.cases:
                case_env = dict(env)
                if result_parts:
                    for label in case.labels:
                        if isinstance(label, ResultPattern) and label.binding:
                            case_env[label.binding] = (
                                result_parts[0]
                                if label.kind == "ok"
                                else result_parts[1]
                            )
                arm_types.append(
                    expr_type(
                        case.value,
                        case_env,
                        return_type=return_type,
                        scope_kind=scope_kind,
                        expected_result=expected_result,
                    )
                )
            if arm_types and all(t == arm_types[0] for t in arm_types):
                return arm_types[0]
            return None
        if isinstance(expr, Call):
            expected_params: list[str] = []
            if isinstance(expr.callee, Identifier):
                expected_params = function_params.get(expr.callee.name, [])
                if expr.callee.name == "input" and len(expr.args) > 1:
                    fail(
                        "`input` takes at most one string prompt argument.",
                        expr,
                        code="pys.input-arity",
                        tips=['Use `input()` or `input("prompt")`.'],
                    )
            elif isinstance(expr.callee, Member):
                receiver_type = expr_type(
                    expr.callee.object,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                )
                owner = method_owner(receiver_type, expr.callee.name)
                if owner:
                    expected_params = method_params.get(
                        (owner, expr.callee.name),
                        [],
                    )
            for index, arg in enumerate(expr.args):
                value = arg.value if isinstance(arg, KeywordArg) else arg
                expected_param = (
                    expected_params[index] if index < len(expected_params) else None
                )
                actual_arg = expr_type(
                    value,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                    expected_result=(
                        expected_param
                        if _result_type_parts(expected_param)
                        else None
                    ),
                )
                if (
                    expected_param
                    and actual_arg
                    and (
                        _result_type_parts(expected_param)
                        or _result_type_parts(actual_arg)
                    )
                    and not _is_assignable_type(
                        actual_arg,
                        expected_param,
                        class_parents,
                        class_implements=class_implements,
                        interfaces=interfaces,
                    )
                ):
                    fail(
                        f"Argument {index + 1} has type {actual_arg}, expected "
                        f"{expected_param}.",
                        value,
                        code="pys.result-argument-type",
                        tips=(
                            ["Handle the result with `propagate` or `switch` first."]
                            if _result_type_parts(actual_arg)
                            and not _result_type_parts(expected_param)
                            else None
                        ),
                    )
            if isinstance(expr.callee, Identifier):
                return function_returns.get(expr.callee.name) or (
                    expr.callee.name if expr.callee.name in class_names else None
                )
            if isinstance(expr.callee, Member):
                return expr_type(
                    expr.callee,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                )
        if isinstance(expr, Cast):
            expr_type(
                expr.expr,
                env,
                return_type=return_type,
                scope_kind=scope_kind,
            )
            return expr.type_name
        if isinstance(expr, BinaryOp):
            left = expr_type(
                expr.left, env, return_type=return_type, scope_kind=scope_kind
            )
            right = expr_type(
                expr.right, env, return_type=return_type, scope_kind=scope_kind
            )
            if expr.op == "+" and "string" in {left, right}:
                return "string"
            return left if left == right else _infer_type(expr, class_names)
        if isinstance(expr, UnaryOp):
            return expr_type(
                expr.operand,
                env,
                return_type=return_type,
                scope_kind=scope_kind,
            )
        for attr in ("value", "expr", "cond", "callee", "object", "index", "subject"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                expr_type(
                    child,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                )
        for attr in ("args", "elements"):
            children = getattr(expr, attr, None)
            if isinstance(children, list):
                for child in children:
                    value = child.value if isinstance(child, KeywordArg) else child
                    if isinstance(value, Expr):
                        expr_type(
                            value,
                            env,
                            return_type=return_type,
                            scope_kind=scope_kind,
                        )
        return _infer_type(expr, class_names)

    def check_value(
        value: Expr | None,
        expected: str | None,
        env: dict[str, str],
        *,
        return_type: str | None,
        scope_kind: str,
        owner: Any,
    ) -> str | None:
        if isinstance(value, LambdaExpr) and expected:
            lambda_parts = _parse_lambda_type_parts(expected)
            if lambda_parts is not None:
                param_types, lambda_return = lambda_parts
                local = dict(env)
                for index, name in enumerate(value.params):
                    if index < len(param_types):
                        local[name] = param_types[index]
                if isinstance(value.body, Block):
                    walk(
                        value.body.statements,
                        local,
                        return_type=lambda_return,
                        scope_kind="lambda",
                    )
                else:
                    check_value(
                        value.body,
                        lambda_return,
                        local,
                        return_type=lambda_return,
                        scope_kind="lambda",
                        owner=value,
                    )
                return expected
        expected_result = expected if _result_type_parts(expected) else None
        actual = expr_type(
            value,
            env,
            return_type=return_type,
            scope_kind=scope_kind,
            expected_result=expected_result,
        )
        if expected_result and actual and actual != expected_result:
            fail(
                f"Result type mismatch: cannot use {actual} where "
                f"{expected_result} is required.",
                owner,
                code="pys.result-type",
            )
        if expected and not expected_result and _result_type_parts(actual):
            fail(
                f"A {actual} value must be handled before it can be used as {expected}.",
                owner,
                code="pys.result-unhandled",
                tips=["Use postfix `propagate` or an exhaustive `switch`."],
            )
        if (
            expected
            and actual
            and isinstance(value, PropagateExpr)
            and not _is_assignable_type(
                actual,
                expected,
                class_parents,
                class_implements=class_implements,
                interfaces=interfaces,
            )
        ):
            fail(
                f"Propagated success value has type {actual}, expected {expected}.",
                owner,
                code="pys.propagate-success-type",
            )
        return actual

    def walk(
        statements: list[Any],
        env: dict[str, str],
        *,
        return_type: str | None,
        scope_kind: str,
    ) -> None:
        for stmt in statements:
            if isinstance(stmt, AssignStmt):
                check_name(stmt.name, stmt)
                expected = None if stmt.declare_type == "var" else stmt.declare_type
                if not expected and not stmt.declare_type:
                    expected = env.get(stmt.name)
                actual = check_value(
                    stmt.value,
                    expected,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                    owner=stmt,
                )
                if stmt.declare_type == "var" and actual:
                    env[stmt.name] = actual
                elif stmt.declare_type:
                    env[stmt.name] = stmt.declare_type
            elif isinstance(stmt, ReturnStmt):
                if _result_type_parts(return_type):
                    if stmt.value is None:
                        fail(
                            f"A function returning {return_type} must return a result value.",
                            stmt,
                            code="pys.result-return",
                        )
                    check_value(
                        stmt.value,
                        return_type,
                        env,
                        return_type=return_type,
                        scope_kind=scope_kind,
                        owner=stmt,
                    )
                elif stmt.value is not None:
                    actual = check_value(
                        stmt.value,
                        return_type or None,
                        env,
                        return_type=return_type,
                        scope_kind=scope_kind,
                        owner=stmt,
                    )
                    if _result_type_parts(actual):
                        fail(
                            f"A function returning {return_type or 'no value'} cannot "
                            f"return {actual}; the result must be handled.",
                            stmt,
                            code="pys.result-unhandled",
                        )
            elif isinstance(stmt, (PrintStmt, ExprStmt)):
                value = stmt.value if isinstance(stmt, PrintStmt) else stmt.expr
                check_value(
                    value,
                    None,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                    owner=stmt,
                )
            elif isinstance(stmt, FunctionDef):
                check_name(stmt.name, stmt)
                local = dict(env)
                for name, type_name in zip(stmt.params, stmt.param_types):
                    check_name(name, stmt)
                    local[name] = type_name
                if stmt.body:
                    walk(
                        stmt.body.statements,
                        local,
                        return_type=stmt.return_type,
                        scope_kind="function",
                    )
            elif isinstance(stmt, ClassDef):
                check_name(stmt.name, stmt)
                for field in stmt.fields:
                    check_name(field.name, field)
                for method in stmt.methods:
                    check_name(method.name, method)
                    local = dict(env)
                    local["self"] = stmt.name
                    if class_parents.get(stmt.name):
                        local["super"] = class_parents[stmt.name] or ""
                    local.update(zip(method.params, method.param_types))
                    if method.body:
                        walk(
                            method.body.statements,
                            local,
                            return_type=method.return_type,
                            scope_kind="function",
                        )
            elif isinstance(stmt, (StructDef, DataDef, EntityDef, EnumDef, InterfaceDef, TraitDef)):
                check_name(stmt.name, stmt)
            elif isinstance(stmt, TasksBlock):
                for task in stmt.tasks:
                    check_name(task.name, task)
                    if task.body:
                        walk(
                            task.body.statements,
                            dict(env),
                            return_type=None,
                            scope_kind="task",
                        )
            elif isinstance(stmt, IfStmt):
                expr_type(
                    stmt.cond,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                )
                if stmt.then_body:
                    walk(
                        stmt.then_body.statements,
                        dict(env),
                        return_type=return_type,
                        scope_kind=scope_kind,
                    )
                if stmt.else_body:
                    walk(
                        stmt.else_body.statements,
                        dict(env),
                        return_type=return_type,
                        scope_kind=scope_kind,
                    )
            elif isinstance(stmt, SwitchStmt):
                subject_type = expr_type(
                    stmt.subject,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                )
                result_parts = _result_type_parts(subject_type)
                for case in stmt.cases:
                    if case.body:
                        case_env = dict(env)
                        if result_parts:
                            for label in case.labels:
                                if isinstance(label, ResultPattern) and label.binding:
                                    case_env[label.binding] = (
                                        result_parts[0]
                                        if label.kind == "ok"
                                        else result_parts[1]
                                    )
                        walk(
                            case.body.statements,
                            case_env,
                            return_type=return_type,
                            scope_kind=scope_kind,
                        )
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                subject = (
                    stmt.cond
                    if isinstance(stmt, WhileStmt)
                    else stmt.iterable
                    if isinstance(stmt, ForEachStmt)
                    else None
                )
                expr_type(
                    subject,
                    env,
                    return_type=return_type,
                    scope_kind=scope_kind,
                )
                if stmt.body:
                    walk(
                        stmt.body.statements,
                        dict(env),
                        return_type=return_type,
                        scope_kind=scope_kind,
                    )

    walk(
        body,
        types,
        return_type=None,
        scope_kind="entrypoint" if is_entrypoint else "module",
    )


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


def _raise_assignment_mismatch(
    *,
    actual: str,
    declared_type: str,
    name: str,
    line: int,
    col: int,
    declaration: bool,
) -> None:
    if actual == "null" and _nullable_inner(declared_type) is None:
        suggested = (
            f"nullable<{declared_type}> {name} = null"
            if declaration and _is_simple_name(name)
            else None
        )
        _transpile_error(
            f"Type '{declared_type}' does not allow null.",
            line,
            col,
            f"{declared_type} {name} = null",
            code="pys.null-non-nullable",
            suggested_fix=suggested,
            tips=[
                f"Change the declaration to `nullable<{declared_type}>` if absence is intentional, "
                f"or provide a {declared_type} value."
            ],
        )
    _transpile_error(
        f"Type mismatch: cannot assign {actual} to '{name}' of type {declared_type}.",
        line,
        col,
        f"{declared_type} {name} = ...",
    )


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
            brace_expected: str | None
            if stmt.declare_type == "var":
                brace_expected = "var"
            elif stmt.declare_type:
                brace_expected = stmt.declare_type
            elif _is_simple_name(stmt.name):
                brace_expected = types.get(stmt.name)
            else:
                brace_expected = None
            if isinstance(stmt.value, BraceLiteral) and "[" not in stmt.name:
                _check_brace_literal_assign(
                    stmt.value,
                    brace_expected,
                    line=line,
                    col=col,
                    name=stmt.name,
                )
            if (
                isinstance(stmt.value, DictLiteral)
                and stmt.declare_type
                and stmt.declare_type != "var"
                and _base_type_name(stmt.declare_type) != "dict"
            ):
                _transpile_error(
                    f"Cannot assign a dict literal to '{stmt.name}' of type {stmt.declare_type}.",
                    line,
                    col,
                    f"{stmt.declare_type} {stmt.name} = {{…}}",
                )
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
                    inferred = _infer_type(stmt.value, class_names)
                    if inferred == "null":
                        _transpile_error(
                            "Cannot infer an underlying type from null.",
                            line,
                            col,
                            f"var {stmt.name} = null",
                            code="pys.null-infer",
                            tips=[
                                f"Write `nullable<T> {stmt.name} = null` with the intended type."
                            ],
                        )
                    types[stmt.name] = inferred or "int"
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
                        _raise_assignment_mismatch(
                            actual=inferred,
                            declared_type=stmt.declare_type,
                            name=stmt.name,
                            line=line,
                            col=col,
                            declaration=True,
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
                        _raise_assignment_mismatch(
                            actual=inferred,
                            declared_type=declared_t,
                            name=stmt.name,
                            line=line,
                            col=col,
                            declaration=False,
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
                dims = list(getattr(stmt, "dims", None) or [])
                rank = len(dims) if dims else 1
                types[stmt.name] = stmt.elem_type + ("[]" * rank)
        elif isinstance(stmt, SharedDecl):
            declared.add(stmt.name)
            if stmt.declare_type:
                types[stmt.name] = stmt.declare_type
        elif isinstance(stmt, AtomicDecl):
            declared.add(stmt.name)
            if stmt.declare_type:
                types[stmt.name] = stmt.declare_type
        elif isinstance(stmt, StructDef):
            declared.add(stmt.name)
            types[stmt.name] = stmt.name
        elif isinstance(stmt, DataDef):
            declared.add(stmt.name)
            types[stmt.name] = stmt.name
        elif isinstance(stmt, EntityDef):
            declared.add(stmt.name)
            types[stmt.name] = stmt.name
            for m in stmt.methods:
                local_decl = set(declared) | set(m.params) | {"self", "this"}
                local_types = dict(types)
                local_types.update(zip(m.params, m.param_types))
                local_types["self"] = stmt.name
                local_types["this"] = stmt.name
                if m.body:
                    _check_bindings(
                        m.body.statements,
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
        elif isinstance(stmt, EnumDef):
            declared.add(stmt.name)
            types[stmt.name] = stmt.name
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
            local_types.update(zip(stmt.params, stmt.param_types))
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
                local_types = dict(types)
                local_types.update(zip(m.params, m.param_types))
                local_types["self"] = stmt.name
                if m.body:
                    _check_bindings(
                        m.body.statements,
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
                    types=dict(types),
                    declared=set(declared),
                    constants=set(constants),
                    fixed=set(fixed),
                    loop_counters=set(loop_counters),
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
                )
            if stmt.else_body:
                _check_bindings(
                    stmt.else_body.statements,
                    types=dict(types),
                    declared=set(declared),
                    constants=set(constants),
                    fixed=set(fixed),
                    loop_counters=set(loop_counters),
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
                )
        elif isinstance(stmt, SwitchStmt):
            subject_type = (
                types.get(stmt.subject.name, "")
                if isinstance(stmt.subject, Identifier)
                else ""
            )
            result_parts = _result_type_parts(subject_type)
            for case in stmt.cases:
                if case.body:
                    if case.brace_scoped:
                        case_types = dict(types)
                        case_declared = set(declared)
                    else:
                        case_types = types
                        case_declared = declared
                    if result_parts:
                        needs_bind = any(
                            isinstance(label, ResultPattern) and label.binding
                            for label in case.labels
                        )
                        if needs_bind:
                            case_types = dict(case_types)
                            case_declared = set(case_declared)
                        for label in case.labels:
                            if isinstance(label, ResultPattern) and label.binding:
                                payload_type = (
                                    result_parts[0]
                                    if label.kind == "ok"
                                    else result_parts[1]
                                )
                                case_types[label.binding] = payload_type
                                case_declared.add(label.binding)
                    _check_bindings(
                        case.body.statements,
                        types=case_types,
                        declared=case_declared,
                        constants=set(constants),
                        fixed=set(fixed),
                        loop_counters=set(loop_counters),
                        class_parents=class_parents,
                        class_names=class_names,
                        class_implements=class_implements,
                        interfaces=interfaces,
                    )
        elif isinstance(stmt, Block):
            _check_bindings(
                stmt.statements,
                types=dict(types),
                declared=set(declared),
                constants=set(constants),
                fixed=set(fixed),
                loop_counters=set(loop_counters),
                class_parents=class_parents,
                class_names=class_names,
                class_implements=class_implements,
                interfaces=interfaces,
            )
        elif isinstance(stmt, ForRangeStmt):
            # Loop binder is scoped to the loop body `{ }` only.
            nested_declared = set(declared) | {stmt.var}
            nested_types = dict(types)
            nested_counters = set(loop_counters) | {stmt.var}
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=nested_types,
                    declared=nested_declared,
                    constants=set(constants),
                    fixed=set(fixed),
                    loop_counters=nested_counters,
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
                )
        elif isinstance(stmt, ForEachStmt):
            nested_declared = set(declared) | {stmt.var}
            nested_types = dict(types)
            if stmt.var_type:
                nested_types[stmt.var] = stmt.var_type
            # Immutable per iteration (lambda.md §3 / classic closure capture).
            nested_counters = set(loop_counters) | {stmt.var}
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=nested_types,
                    declared=nested_declared,
                    constants=set(constants),
                    fixed=set(fixed),
                    loop_counters=nested_counters,
                    class_parents=class_parents,
                    class_names=class_names,
                    class_implements=class_implements,
                    interfaces=interfaces,
                )
        elif isinstance(stmt, (WhileStmt, RepeatStmt)):
            if stmt.body:
                _check_bindings(
                    stmt.body.statements,
                    types=dict(types),
                    declared=set(declared),
                    constants=set(constants),
                    fixed=set(fixed),
                    loop_counters=set(loop_counters),
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


def _check_oop(body: list[Any], *, types: dict[str, str], resolver: Any | None = None) -> None:
    sealed: set[str] = set()
    class_names: set[str] = set()
    interfaces: set[str] = set()
    class_members: dict[str, dict[str, str]] = {}
    class_parents: dict[str, str | None] = {}
    class_implements: dict[str, list[str]] = {}
    traits = _trait_map(body)
    atomic_names: set[str] = set()

    def _collect_atomics(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AtomicDecl):
                atomic_names.add(stmt.name)
            elif isinstance(stmt, FunctionDef) and stmt.body:
                _collect_atomics(stmt.body.statements)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        _collect_atomics(m.body.statements)
            elif isinstance(stmt, EntityDef):
                for m in stmt.methods:
                    if m.body:
                        _collect_atomics(m.body.statements)
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    _collect_atomics(stmt.then_body.statements)
                if stmt.else_body:
                    _collect_atomics(stmt.else_body.statements)
            elif isinstance(stmt, SwitchStmt):
                for case in stmt.cases:
                    if case.body:
                        _collect_atomics(case.body.statements)
            elif isinstance(stmt, Block):
                _collect_atomics(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    _collect_atomics(stmt.body.statements)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        _collect_atomics(t.body.statements)

    _collect_atomics(body)

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
            # Flatten trait methods into the host's member map (public).
            for use in stmt.uses:
                tname = use.name
                trait = traits.get(tname)
                if trait is None:
                    continue
                for m in trait.methods:
                    members.setdefault(m.name, "public")
            class_members[stmt.name] = members
        elif isinstance(stmt, StructDef):
            # Struct fields are always public; type export uses top_visibility.
            class_members[stmt.name] = {f.name: "public" for f in stmt.fields}
        elif isinstance(stmt, DataDef):
            class_members[stmt.name] = {f.name: "public" for f in stmt.fields}
        elif isinstance(stmt, EntityDef):
            class_names.add(stmt.name)
            members = {f.name: (f.access or "public") for f in stmt.fields}
            for m in stmt.methods:
                if not m.is_constructor:
                    members[m.name] = m.access or "public"
            class_members[stmt.name] = members
            class_parents[stmt.name] = stmt.parent or None
        elif isinstance(stmt, EnumDef):
            members = {m.name: "public" for m in stmt.members}
            members["value"] = "public"
            class_members[stmt.name] = members

    if resolver is not None:
        for name, access in getattr(resolver, "struct_field_access", {}).items():
            class_members.setdefault(name, dict(access))
        for name, members in getattr(resolver, "enum_members", {}).items():
            access = {m: "public" for m in members}
            access["value"] = "public"
            class_members.setdefault(name, access)

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
        # Prefer explicit `inherits` parent when present.
        if stmt.parent:
            parent = stmt.parent
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

    type_modules: dict[str, str] = dict(getattr(resolver, "type_modules", {}) or {}) if resolver else {}
    imported_modules: dict[str, str] = (
        dict(getattr(resolver, "imported_modules", {}) or {}) if resolver else {}
    )
    site_paths: list[Path] = list(resolver._deps_paths()) if resolver is not None else []

    def library_member_status(type_name: str, member: str) -> str:
        """See ``library_type_member_status`` — PYS types are never introspected here."""
        if type_name in class_members or type_name in interfaces:
            return "not_library"
        if resolver is None:
            return "not_library"
        from .pytypes import library_type_member_status

        return library_type_member_status(
            type_name,
            member,
            type_modules=type_modules,
            imported_modules=imported_modules,
            site_paths=site_paths,
            allow_runtime_imports=resolver.allow_runtime_introspection,
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
        """Return ``(defining_type, access)``.

        Access ``\"unverified\"`` means a library parent is in scope but could not
        be loaded for introspection — callers must not treat that as an error.
        """
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

            status = library_member_status(current, member)
            if status == "found":
                return current, "public"
            if status == "unavailable":
                # Known import (e.g. QMainWindow) but binary module won't load.
                return current, "unverified"
            if status == "absent":
                # Library class loaded; member is not on that type/MRO.
                return None, None

            if current in seen:
                break
            seen.add(current)
            current = class_parents.get(current)

        if type_name in interfaces:
            members = class_members.get(type_name, {})
            if member in members:
                return type_name, members[member]

        status = library_member_status(type_name, member)
        if status == "found":
            return type_name, "public"
        if status == "unavailable":
            return type_name, "unverified"
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
        # Synthesized accessors on atomic variables (not class members).
        if recv in atomic_names and member in {"get", "compareAndSet"}:
            return
        recv_t = receiver_type(recv, local_types, current_class)
        if not recv_t:
            return
        recv_t = _base_type_name(recv_t)
        defining_cls, access = lookup_member(recv_t, member)
        if access == "unverified":
            # Environment cannot introspect the library; do not invent an error.
            return
        if defining_cls is None or access is None:
            # Strict missing-member errors only for types declared in PYS source.
            if recv_t in class_members or recv_t in interfaces:
                _transpile_error(
                    f"'{member}' is not a member of declared type {recv_t}.",
                    line,
                    column,
                    code or f"{recv}.{member}",
                )
                return
            # Library / unresolved external type: re-check via introspection.
            # (lookup may have returned None when the name was not yet in
            # type_modules but is still resolvable from imported packages.)
            status = library_member_status(recv_t, member)
            if status == "found":
                return
            if status == "unavailable":
                return
            if status == "absent":
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
        kind = "struct" if defining_cls in getattr(resolver, "structs", set()) or any(
            isinstance(s, StructDef) and s.name == defining_cls for s in body
        ) else "class"
        _transpile_error(
            f"Access denied: '{member}' is {access} in {kind} {defining_cls}.",
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
            elif isinstance(stmt, (ClassDef, EntityDef)):
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


def _check_abstract_classes(body: list[Any]) -> None:
    """Abstract method placement, subclass impl, no direct instantiation."""
    classes = _class_map(body)
    abstract_names = {n for n, c in classes.items() if c.abstract}

    for cls in classes.values():
        line = cls.span.line if cls.span else 1
        for m in cls.methods:
            if m.is_abstract and not cls.abstract:
                _transpile_error(
                    f"Abstract method '{m.name}' is only allowed inside an "
                    f"`abstract class` (declare `abstract class {cls.name}`).",
                    m.span.line if m.span else line,
                    m.span.column if m.span else 1,
                    m.name,
                    code="pys.abstract-method",
                    tips=[f"Change to `abstract class {cls.name}` or give '{m.name}' a body."],
                )

        if cls.abstract:
            continue

        # Concrete class: must implement all abstract methods from ancestors.
        required: dict[str, tuple[str, int, list[str]]] = {}
        current_name = cls.parent or ""
        if not current_name:
            for b in cls.bases:
                if b in classes:
                    current_name = b
                    break
        seen: set[str] = set()
        while current_name and current_name not in seen:
            seen.add(current_name)
            parent = classes.get(current_name)
            if parent is None:
                break
            # Concrete methods on ancestors satisfy abstracts further up.
            for m in parent.methods:
                if m.is_constructor:
                    continue
                if m.is_abstract:
                    required.setdefault(
                        m.name, (m.return_type or "", len(m.params), list(m.param_types))
                    )
                else:
                    required.pop(m.name, None)
            next_name = parent.parent or ""
            if not next_name:
                for b in parent.bases:
                    if b in classes:
                        next_name = b
                        break
            current_name = next_name

        provided = {
            m.name: (m.return_type or "", len(m.params), list(m.param_types))
            for m in cls.methods
            if not m.is_constructor and not m.is_abstract
        }
        for mname, (ret, arity, _pt) in required.items():
            if mname not in provided:
                _transpile_error(
                    f"Class {cls.name} must implement abstract method '{mname}' "
                    f"inherited from its abstract ancestors.",
                    line,
                    1,
                    mname,
                    code="pys.abstract-impl",
                    tips=[f"Add `public {ret or 'void'} {mname}(...) {{ … }}` on {cls.name}."],
                )
            got_ret, got_arity, _ = provided[mname]
            if got_arity != arity:
                _transpile_error(
                    f"Class {cls.name} method '{mname}' does not match abstract "
                    f"signature (expected {arity} parameter(s), found {got_arity}).",
                    line,
                    1,
                    mname,
                    code="pys.abstract-impl",
                )
            want = _base_type_name(ret)
            got = _base_type_name(got_ret)
            if want and got and want != got and want != "void" and got != "void":
                # Allow generic erasure / named type mismatch soft: only when both concrete.
                if want not in {"T", "U"} and got not in {"T", "U"}:
                    pass  # arity is the hard check; return types often erased generics

    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            if expr.callee.name in abstract_names:
                _transpile_error(
                    f"Abstract class '{expr.callee.name}' cannot be instantiated "
                    f"— construct a concrete subclass instead.",
                    expr.span.line if expr.span else 1,
                    expr.span.column if expr.span else 1,
                    expr.callee.name,
                    code="pys.abstract-new",
                    tips=[f"Use a class that `inherits {expr.callee.name}`."],
                )
        for attr in (
            "left",
            "right",
            "operand",
            "value",
            "expr",
            "cond",
            "callee",
            "object",
            "index",
            "subject",
        ):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, KeywordArg):
                    walk_expr(a.value)
                elif isinstance(a, Expr):
                    walk_expr(a)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                walk_expr(stmt.value)
            elif isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt, AugAssignStmt)):
                walk_expr(getattr(stmt, "value", None) or getattr(stmt, "expr", None))
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond)
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, SwitchStmt):
                walk_expr(stmt.subject)
                for case in stmt.cases:
                    if case.body:
                        walk(case.body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(stmt.body.statements)
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

    walk(body)


def _trait_map(body: list[Any]) -> dict[str, TraitDef]:
    return {s.name: s for s in body if isinstance(s, TraitDef)}


def _class_map(body: list[Any]) -> dict[str, ClassDef]:
    return {s.name: s for s in body if isinstance(s, ClassDef)}


def _host_fields_and_methods(
    cls: ClassDef, classes: dict[str, ClassDef]
) -> tuple[dict[str, str], dict[str, tuple[str, int, list[str]]]]:
    """Collect fields and methods from class + inherits chain.

    Methods map: name -> (return_type, arity, param_types).
    """
    fields: dict[str, str] = {}
    methods: dict[str, tuple[str, int, list[str]]] = {}
    current: ClassDef | None = cls
    seen: set[str] = set()
    while current and current.name not in seen:
        seen.add(current.name)
        for f in current.fields:
            fields.setdefault(f.name, f.type_name)
        for m in current.methods:
            if m.is_constructor:
                continue
            methods.setdefault(
                m.name, (m.return_type or "", len(m.params), list(m.param_types))
            )
        parent_name = current.parent or ""
        if not parent_name:
            for b in current.bases:
                if b in classes:
                    parent_name = b
                    break
        current = classes.get(parent_name) if parent_name else None
    return fields, methods


def _collect_self_members(expr: Expr | None, found: set[str]) -> None:
    """Collect ``self.x`` / ``this.x`` member names used in an expression."""
    if expr is None:
        return
    if isinstance(expr, Member) and isinstance(expr.object, Identifier):
        if expr.object.name in {"self", "this"}:
            found.add(expr.name)
        _collect_self_members(expr.object, found)
        return
    if isinstance(expr, Call):
        _collect_self_members(expr.callee, found)
        for a in expr.args:
            if isinstance(a, KeywordArg):
                _collect_self_members(a.value, found)
            else:
                _collect_self_members(a, found)
        return
    for attr in ("left", "right", "operand", "value", "expr", "cond", "object", "index"):
        child = getattr(expr, attr, None)
        if isinstance(child, Expr):
            _collect_self_members(child, found)
    elements = getattr(expr, "elements", None)
    if isinstance(elements, list):
        for el in elements:
            if isinstance(el, Expr):
                _collect_self_members(el, found)


def _collect_self_members_in_stmts(stmts: list[Any], found: set[str]) -> None:
    for stmt in stmts:
        if isinstance(stmt, AssignStmt):
            _collect_self_members(stmt.value, found)
            # lvalue this.x = …
            if "." in stmt.name:
                root, _, rest = stmt.name.partition(".")
                if root in {"self", "this"} and rest:
                    found.add(rest.split(".", 1)[0].split("[", 1)[0])
        elif isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt, AugAssignStmt)):
            _collect_self_members(
                getattr(stmt, "value", None) or getattr(stmt, "expr", None), found
            )
        elif isinstance(stmt, IfStmt):
            _collect_self_members(stmt.cond, found)
            if stmt.then_body:
                _collect_self_members_in_stmts(stmt.then_body.statements, found)
            if stmt.else_body:
                _collect_self_members_in_stmts(stmt.else_body.statements, found)
        elif isinstance(stmt, Block):
            _collect_self_members_in_stmts(stmt.statements, found)
        elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
            if isinstance(stmt, WhileStmt):
                _collect_self_members(stmt.cond, found)
            elif isinstance(stmt, ForEachStmt):
                _collect_self_members(stmt.iterable, found)
            if stmt.body:
                _collect_self_members_in_stmts(stmt.body.statements, found)
        elif isinstance(stmt, SwitchStmt):
            _collect_self_members(stmt.subject, found)
            for case in stmt.cases:
                if case.body:
                    _collect_self_members_in_stmts(case.body.statements, found)


def _check_traits(body: list[Any], *, types: dict[str, str]) -> None:
    """Validate trait composition: requires, collisions, this.x, not-a-type."""
    traits = _trait_map(body)
    classes = _class_map(body)
    trait_names = set(traits)
    interfaces = {s.name for s in body if isinstance(s, InterfaceDef)}

    # Trait method bodies: this.x must be required or another method of the trait.
    for trait in traits.values():
        allowed = {r.name for r in trait.requires} | {m.name for m in trait.methods}
        for m in trait.methods:
            used: set[str] = set()
            if m.body:
                _collect_self_members_in_stmts(m.body.statements, used)
            for name in sorted(used):
                if name not in allowed:
                    line = m.span.line if m.span else 1
                    col = m.span.column if m.span else 1
                    _transpile_error(
                        f"Trait '{trait.name}' method '{m.name}' uses `this.{name}` "
                        f"but '{name}' is not declared in `requires` "
                        f"(and is not a method of this trait).",
                        line,
                        col,
                        name,
                        code="pys.trait-this",
                        tips=[
                            f"Add `requires … {name}` to trait {trait.name}, "
                            f"or remove the access."
                        ],
                    )

    for stmt in body:
        if not isinstance(stmt, ClassDef):
            continue
        line = stmt.span.line if stmt.span else 1
        # Trait listed in implements
        for b in stmt.bases:
            if b in trait_names:
                _transpile_error(
                    f"'{b}' is a trait, not an interface — use `uses {b}` "
                    f"for composition (traits are not nominal types).",
                    line,
                    1,
                    b,
                    code="pys.trait-not-interface",
                    tips=[f"Change `implements {b}` to `uses {b}`."],
                    suggested_fix=None,
                )

        if not stmt.uses:
            continue

        host_fields, host_methods = _host_fields_and_methods(stmt, classes)
        method_owners: dict[str, list[str]] = {}

        for use in stmt.uses:
            tname = use.name
            trait = traits.get(tname)
            if trait is None:
                _transpile_error(
                    f"Unknown trait '{tname}' used by class {stmt.name}.",
                    line,
                    1,
                    tname,
                    code="pys.trait-unknown",
                )
            req_by_name = {r.name: r for r in trait.requires}
            method_names = {m.name for m in trait.methods}
            remap_map: dict[str, str] = {}
            for left, right in use.remaps:
                if left in remap_map:
                    _transpile_error(
                        f"Duplicate remapping for requirement '{left}' on "
                        f"`uses {tname}` — each requirement may be mapped at most once.",
                        line,
                        1,
                        left,
                        code="pys.trait-remap",
                    )
                if left not in req_by_name:
                    if left in method_names:
                        _transpile_error(
                            f"Trait '{tname}' declares no requirement named '{left}' — "
                            f"'{left}' is a method offered by the trait, not a "
                            f"dependency it requires. Trait method names cannot be remapped.",
                            line,
                            1,
                            left,
                            code="pys.trait-remap",
                            tips=[
                                "Remap only `requires` names: "
                                f"`uses {tname}(requirement: hostMember)`.",
                            ],
                        )
                    hint = ""
                    if req_by_name:
                        # Simple tip: list first requires name as "did you mean"
                        sample = sorted(req_by_name)[0]
                        hint = f" — did you mean '{sample}'?"
                    _transpile_error(
                        f"Trait '{tname}' declares no requirement named '{left}'{hint}",
                        line,
                        1,
                        left,
                        code="pys.trait-remap",
                        tips=[
                            f"Remap entries must name a `requires` item of {tname}."
                        ],
                    )
                remap_map[left] = right

            for req in trait.requires:
                rline = req.span.line if req.span else line
                rcol = req.span.column if req.span else 1
                host_name = remap_map.get(req.name, req.name)
                mapped = host_name != req.name
                if mapped:
                    type_part = (
                        f"{req.type_name}, mapped from {tname}'s '{req.name}'"
                        if req.type_name
                        else f"mapped from {tname}'s '{req.name}'"
                    )
                else:
                    type_part = req.type_name or ""
                if req.kind == "field":
                    if host_name not in host_fields:
                        detail = f"'{host_name}' ({type_part})" if type_part else f"'{host_name}'"
                        _transpile_error(
                            f"{stmt.name} uses {tname} but does not provide "
                            f"{detail}, required by trait {tname}.",
                            rline,
                            rcol,
                            host_name,
                            code="pys.trait-requires",
                        )
                    got = _base_type_name(host_fields[host_name] or "")
                    want = _base_type_name(req.type_name or "")
                    if want and got and got != want:
                        _transpile_error(
                            f"{stmt.name} uses {tname} but '{host_name}' has type "
                            f"{got}, required {want} by trait {tname}.",
                            rline,
                            rcol,
                            host_name,
                            code="pys.trait-requires",
                        )
                else:
                    if host_name not in host_methods:
                        if mapped:
                            detail = (
                                f"'{host_name}' (..., mapped from {tname}'s '{req.name}')"
                            )
                        else:
                            detail = f"'{host_name}' (...)"
                        _transpile_error(
                            f"{stmt.name} uses {tname} but does not provide "
                            f"{detail}, required by trait {tname}.",
                            rline,
                            rcol,
                            host_name,
                            code="pys.trait-requires",
                        )
                    ret, arity, _ptypes = host_methods[host_name]
                    if arity != len(req.params):
                        _transpile_error(
                            f"{stmt.name} method '{host_name}' does not match "
                            f"trait {tname} requires (expected {len(req.params)} "
                            f"parameter(s), found {arity}).",
                            rline,
                            rcol,
                            host_name,
                            code="pys.trait-requires",
                        )
                    want_ret = _base_type_name(req.type_name or "")
                    got_ret = _base_type_name(ret or "")
                    if want_ret and got_ret and want_ret != got_ret:
                        _transpile_error(
                            f"{stmt.name} method '{host_name}' return type {got_ret} "
                            f"does not match trait {tname} requires {want_ret}.",
                            rline,
                            rcol,
                            host_name,
                            code="pys.trait-requires",
                        )
            for m in trait.methods:
                method_owners.setdefault(m.name, []).append(tname)

        host_method_names = {m.name for m in stmt.methods if not m.is_constructor}
        for mname, owners in method_owners.items():
            if len(set(owners)) > 1 and mname not in host_method_names:
                _transpile_error(
                    f"Class {stmt.name} uses traits that both define '{mname}' "
                    f"({', '.join(sorted(set(owners)))}) — provide an explicit "
                    f"override on {stmt.name} to disambiguate "
                    f"(e.g. call `TraitName.{mname}(this)` from the override).",
                    line,
                    1,
                    mname,
                    code="pys.trait-collision",
                    tips=[
                        f"Add `public … {mname}(...) {{ … }}` on {stmt.name} "
                        f"that chooses which trait method to call."
                    ],
                )

    # Reject trait construction / trait as binding type.
    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            if expr.callee.name in trait_names:
                _transpile_error(
                    f"Trait '{expr.callee.name}' cannot be instantiated "
                    f"— compose it with `uses` on a class.",
                    expr.span.line if expr.span else 1,
                    expr.span.column if expr.span else 1,
                    expr.callee.name,
                    code="pys.trait-not-type",
                )
        for attr in (
            "left",
            "right",
            "operand",
            "value",
            "expr",
            "cond",
            "callee",
            "object",
            "index",
            "subject",
        ):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, KeywordArg):
                    walk_expr(a.value)
                elif isinstance(a, Expr):
                    walk_expr(a)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                if stmt.declare_type and _base_type_name(stmt.declare_type) in trait_names:
                    _transpile_error(
                        f"'{stmt.declare_type}' is a trait, not a type — "
                        f"traits cannot be used as variable types.",
                        stmt.span.line if stmt.span else 1,
                        stmt.span.column if stmt.span else 1,
                        stmt.declare_type,
                        code="pys.trait-not-type",
                    )
                walk_expr(stmt.value)
            elif isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt, AugAssignStmt)):
                walk_expr(getattr(stmt, "value", None) or getattr(stmt, "expr", None))
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond)
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, SwitchStmt):
                walk_expr(stmt.subject)
                for case in stmt.cases:
                    if case.body:
                        walk(case.body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(stmt.body.statements)
            elif isinstance(stmt, FunctionDef) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, TraitDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements)

    walk(body)
    # silence unused in some type-checkers
    _ = (types, interfaces)


def _check_interfaces(body: list[Any]) -> None:
    interfaces: dict[str, dict[str, int]] = {}
    traits = _trait_map(body)
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
        # Trait-composed methods count toward interface satisfaction.
        for use in stmt.uses:
            trait = traits.get(use.name)
            if trait is None:
                continue
            for m in trait.methods:
                available.setdefault(m.name, len(m.params))
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
            for use in parent_cls.uses:
                trait = traits.get(use.name)
                if trait is None:
                    continue
                for m in trait.methods:
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
            # `inherits LibraryType` — not an interface; member checks use pytypes.
            if stmt.parent and b == stmt.parent:
                continue
            if b in traits:
                continue  # reported by _check_traits
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


def _struct_info_map(body: list[Any]) -> dict[str, dict[str, Any]]:
    info: dict[str, dict[str, Any]] = {}
    for stmt in body:
        if not isinstance(stmt, StructDef):
            continue
        order = [f.name for f in stmt.fields]
        access = {f.name: "public" for f in stmt.fields}
        ftypes = {f.name: f.type_name for f in stmt.fields}
        ffix = {f.name for f in stmt.fields if f.is_fix or stmt.type_fix}
        defaults = {f.name for f in stmt.fields if f.default is not None}
        info[stmt.name] = {
            "type_fix": stmt.type_fix,
            "fields": order,
            "access": access,
            "types": ftypes,
            "fix_fields": ffix,
            "defaults": defaults,
        }
    return info


def _base_type_name(type_name: str) -> str:
    """Strip generic args: ``Pair<int, string>`` → ``Pair``."""
    if "<" in type_name:
        return type_name.split("<", 1)[0]
    return type_name


def _is_null_lit(expr: Expr | None) -> bool:
    return isinstance(expr, Literal) and expr.kind == "null"


def _check_struct_field_assign(
    lvalue: str,
    value: Expr | None,
    *,
    types: dict[str, str],
    fixed: set[str],
    struct_info: dict[str, dict[str, Any]],
    line: int,
    col: int,
) -> None:
    """Reject illegal writes to struct fields, including nested paths (``a.b.c``)."""
    parts = lvalue.split(".")
    if len(parts) < 2:
        return
    root = parts[0]
    root_t = _base_type_name(types.get(root, ""))
    if root_t not in struct_info:
        return
    if struct_info[root_t]["type_fix"]:
        kind = struct_info[root_t].get("kind", "struct")
        label = "data" if kind == "data" else "fix struct"
        _transpile_error(
            f"Cannot assign to field path '{lvalue}' of {label} type {root_t}.",
            line,
            col,
            lvalue,
            code="pys.data-immutable" if kind == "data" else None,
        )
    if root in fixed:
        _transpile_error(
            f"Cannot assign to field path '{lvalue}' of fix-bound struct '{root}'.",
            line,
            col,
            lvalue,
        )
    cur_t = root_t
    for i, member in enumerate(parts[1:]):
        meta = struct_info[cur_t]
        if member not in meta["fields"]:
            _transpile_error(
                f"'{member}' is not a field of struct {cur_t}.",
                line,
                col,
                lvalue,
            )
        is_last = i == len(parts) - 2
        if member in meta["fix_fields"]:
            if is_last:
                _transpile_error(
                    f"Cannot assign to fix field '{member}' of struct {cur_t}.",
                    line,
                    col,
                    lvalue,
                )
            else:
                _transpile_error(
                    f"Cannot assign through fix field '{member}' of struct {cur_t}.",
                    line,
                    col,
                    lvalue,
                )
        if is_last:
            field_type = meta["types"].get(member, "")
            if _is_null_lit(value) and _nullable_inner(field_type) is None:
                _transpile_error(
                    f"Struct field '{member}' cannot be null.",
                    line,
                    col,
                    "null",
                )
            return
        next_t = _base_type_name(meta["types"].get(member, ""))
        if next_t not in struct_info:
            return
        cur_t = next_t


def _check_data_and_entities(body: list[Any], *, types: dict[str, str]) -> None:
    """SA for `data` value objects and `entity` identity types."""
    _EQ_BANNED = frozenset(
        {"equals", "hashCode", "toString", "__eq__", "__hash__", "__str__", "__repr__"}
    )
    entities = {s.name: s for s in body if isinstance(s, EntityDef)}

    def effective_identity(ent: EntityDef) -> list[str]:
        keys: list[str] = []
        if ent.parent:
            parent = entities.get(ent.parent)
            if parent is not None:
                keys.extend(effective_identity(parent))
        keys.extend(ent.identity)
        return keys

    for stmt in body:
        if isinstance(stmt, DataDef):
            line = stmt.span.line if stmt.span else 1
            # No methods on data (parser already forbids most); belt-and-suspenders.
            continue
        if not isinstance(stmt, EntityDef):
            continue
        line = stmt.span.line if stmt.span else 1
        field_map = {f.name: f for f in stmt.fields}
        if not stmt.parent and not stmt.identity:
            _transpile_error(
                f"Root entity '{stmt.name}' must declare `identity(...)` "
                f"(at least one key field).",
                line,
                1,
                stmt.name,
                code="pys.entity-identity",
                tips=[
                    f"Example: `entity {stmt.name} identity(id) {{ private fix int id … }}`."
                ],
            )
        if stmt.parent:
            if stmt.parent not in entities:
                # May be a class — reject non-entity parents.
                is_class = any(
                    isinstance(s, ClassDef) and s.name == stmt.parent for s in body
                )
                _transpile_error(
                    f"Entity '{stmt.name}' can only inherit another entity "
                    f"(found parent '{stmt.parent}'"
                    + (" which is a class" if is_class else "")
                    + ").",
                    line,
                    1,
                    stmt.parent,
                    code="pys.entity-inherits",
                    tips=["Change the parent to an `entity`, or use `class` instead."],
                )
        for key in stmt.identity:
            fld = field_map.get(key)
            if fld is None:
                _transpile_error(
                    f"Entity '{stmt.name}': identity field '{key}' is not declared "
                    f"in this entity's body.",
                    line,
                    1,
                    key,
                    code="pys.entity-identity",
                    tips=[f"Add `private fix <type> {key}` (or another access) in `{stmt.name}`."],
                )
            elif not fld.is_fix:
                _transpile_error(
                    f"Entity '{stmt.name}': identity field '{key}' must be declared `fix`.",
                    fld.span.line if fld.span else line,
                    fld.span.column if fld.span else 1,
                    key,
                    code="pys.entity-fix",
                    tips=[
                        f"Write `private fix <type> {key}` — mutable keys corrupt hash-based collections."
                    ],
                )
            elif _nullable_inner(fld.type_name) is not None:
                _transpile_error(
                    f"Entity '{stmt.name}': identity field '{key}' must have a non-null type.",
                    fld.span.line if fld.span else line,
                    fld.span.column if fld.span else 1,
                    key,
                    code="pys.nullable-identity",
                    tips=[
                        "Use a non-null identity type and supply the key before constructing the entity."
                    ],
                )
        has_ctor = any(m.is_constructor for m in stmt.methods)
        if not has_ctor:
            _transpile_error(
                f"Entity '{stmt.name}' must declare a constructor "
                f"`public {stmt.name}(...) {{ … }}`.",
                line,
                1,
                stmt.name,
                code="pys.entity-ctor",
            )
        for m in stmt.methods:
            if m.is_constructor:
                continue
            if m.name in _EQ_BANNED:
                _transpile_error(
                    f"Entity '{stmt.name}' cannot declare `{m.name}` — "
                    f"equality/hash/string form are generated from `identity(...)`.",
                    m.span.line if m.span else line,
                    m.span.column if m.span else 1,
                    m.name,
                    code="pys.entity-equals",
                    tips=["Remove the method; use `==` which compares identity fields only."],
                )

    # Fix-field assignment guards for entities (outside constructors).
    # Include inherited fix fields so subclasses cannot mutate parent keys.
    entity_fix: dict[str, set[str]] = {}
    for name, ent in entities.items():
        fixes: set[str] = set()
        cur: EntityDef | None = ent
        seen: set[str] = set()
        while cur is not None and cur.name not in seen:
            seen.add(cur.name)
            fixes |= {f.name for f in cur.fields if f.is_fix}
            cur = entities.get(cur.parent) if cur.parent else None
        entity_fix[name] = fixes

    def check_assign(stmt: AssignStmt, *, in_entity_ctor: bool, entity_type: str) -> None:
        if in_entity_ctor:
            return
        # AssignStmt.name is an lvalue string: `this.field` / `obj.field`.
        parts = stmt.name.split(".")
        if len(parts) < 2:
            return
        root, member = parts[0], parts[1]
        if root in {"this", "self"}:
            if member in entity_fix.get(entity_type, set()):
                _transpile_error(
                    f"Cannot assign to fix field '{member}' of entity {entity_type}.",
                    stmt.span.line if stmt.span else 1,
                    stmt.span.column if stmt.span else 1,
                    member,
                    code="pys.entity-fix",
                )
            return
        et = _base_type_name(types.get(root, ""))
        if et in entity_fix and member in entity_fix[et]:
            _transpile_error(
                f"Cannot assign to fix field '{member}' of entity {et}.",
                stmt.span.line if stmt.span else 1,
                stmt.span.column if stmt.span else 1,
                member,
                code="pys.entity-fix",
            )

    def walk(stmts: list[Any], *, in_entity_ctor: bool = False, entity_type: str = "") -> None:
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                check_assign(stmt, in_entity_ctor=in_entity_ctor, entity_type=entity_type)
            elif isinstance(stmt, EntityDef):
                for m in stmt.methods:
                    if m.body:
                        walk(
                            m.body.statements,
                            in_entity_ctor=m.is_constructor,
                            entity_type=stmt.name,
                        )
            elif isinstance(stmt, FunctionDef):
                if stmt.body:
                    walk(stmt.body.statements)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk(
                        stmt.then_body.statements,
                        in_entity_ctor=in_entity_ctor,
                        entity_type=entity_type,
                    )
                if stmt.else_body:
                    walk(
                        stmt.else_body.statements,
                        in_entity_ctor=in_entity_ctor,
                        entity_type=entity_type,
                    )
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(
                        stmt.body.statements,
                        in_entity_ctor=in_entity_ctor,
                        entity_type=entity_type,
                    )
            elif isinstance(stmt, Block):
                walk(
                    stmt.statements,
                    in_entity_ctor=in_entity_ctor,
                    entity_type=entity_type,
                )

    walk(body)


def _check_structs(
    body: list[Any],
    *,
    types: dict[str, str],
    fixed: set[str],
    struct_info: dict[str, dict[str, Any]],
) -> None:
    """SA rules for struct types, construction, and field mutability."""

    def check_null_in_struct_ctor(call: Call, struct_name: str) -> None:
        meta = struct_info[struct_name]
        kind = meta.get("kind", "struct")
        label = "data" if kind == "data" else "struct"
        fields: list[str] = meta["fields"]
        field_types: dict[str, str] = meta["types"]
        defaults: set[str] = meta["defaults"]
        line = call.span.line if call.span else 1
        col = call.span.column if call.span else 1
        positional: list[Expr] = []
        named: dict[str, Expr] = {}
        for arg in call.args:
            if isinstance(arg, KeywordArg):
                if arg.name in named:
                    _transpile_error(
                        f"Duplicate named argument '{arg.name}' in {label} {struct_name} constructor.",
                        arg.span.line if arg.span else line,
                        arg.span.column if arg.span else col,
                        arg.name,
                    )
                if arg.name not in fields:
                    _transpile_error(
                        f"Unknown field '{arg.name}' in {label} {struct_name} constructor.",
                        arg.span.line if arg.span else line,
                        arg.span.column if arg.span else col,
                        arg.name,
                    )
                named[arg.name] = arg.value
            else:
                if named:
                    _transpile_error(
                        f"Positional argument after named argument in {label} {struct_name} constructor.",
                        arg.span.line if arg.span else line,
                        arg.span.column if arg.span else col,
                        struct_name,
                    )
                positional.append(arg)
        if len(positional) > len(fields):
            _transpile_error(
                f"{label.capitalize()} {struct_name} constructor expects at most {len(fields)} "
                f"positional argument(s), got {len(positional)}.",
                line,
                col,
                struct_name,
            )
        for i, arg in enumerate(positional):
            if (
                _is_null_lit(arg)
                and _nullable_inner(field_types.get(fields[i], "")) is None
            ):
                _transpile_error(
                    f"{label.capitalize()} field '{fields[i]}' of type {struct_name} cannot be null.",
                    arg.span.line if arg.span else line,
                    arg.span.column if arg.span else col,
                    "null",
                )
        for fname, val in named.items():
            if _is_null_lit(val) and _nullable_inner(field_types.get(fname, "")) is None:
                _transpile_error(
                    f"{label.capitalize()} field '{fname}' of type {struct_name} cannot be null.",
                    val.span.line if val.span else line,
                    val.span.column if val.span else col,
                    "null",
                )
        provided = set(fields[: len(positional)]) | set(named)
        missing = [f for f in fields if f not in provided and f not in defaults]
        if missing:
            _transpile_error(
                f"{label.capitalize()} {struct_name} constructor missing field(s): {', '.join(missing)}.",
                line,
                col,
                struct_name,
            )

    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            name = expr.callee.name
            if name in struct_info:
                check_null_in_struct_ctor(expr, name)
        for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, KeywordArg):
                    walk_expr(a.value)
                elif isinstance(a, Expr):
                    walk_expr(a)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, SharedDecl):
                base = _base_type_name(stmt.declare_type or "")
                if base in struct_info:
                    _transpile_error(
                        f"`shared` cannot be used with struct type {base} "
                        f"(structs are identity-free value types).",
                        stmt.span.line if stmt.span else 1,
                        stmt.span.column if stmt.span else 1,
                        f"shared {stmt.declare_type}",
                    )
                if _is_null_lit(stmt.value) and base in struct_info:
                    _transpile_error(
                        f"Struct-typed binding cannot be null.",
                        stmt.span.line if stmt.span else 1,
                        stmt.span.column if stmt.span else 1,
                        "null",
                    )
            if isinstance(stmt, AtomicDecl):
                base = _base_type_name(stmt.declare_type or "")
                if base in struct_info:
                    _transpile_error(
                        f"`atomic` cannot be used with struct type {base} "
                        f"(structs are identity-free value types).",
                        stmt.span.line if stmt.span else 1,
                        stmt.span.column if stmt.span else 1,
                        f"atomic {stmt.declare_type}",
                    )
            if isinstance(stmt, AssignStmt):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                walk_expr(stmt.value)
                if stmt.declare_type:
                    base = _base_type_name(stmt.declare_type)
                    if base in struct_info and _is_null_lit(stmt.value):
                        _transpile_error(
                            f"Struct-typed binding '{stmt.name}' cannot be null.",
                            line,
                            col,
                            "null",
                        )
                if "." in stmt.name:
                    _check_struct_field_assign(
                        stmt.name,
                        stmt.value,
                        types=types,
                        fixed=fixed,
                        struct_info=struct_info,
                        line=line,
                        col=col,
                    )
                continue
            if isinstance(stmt, StructDef):
                seen_fields: set[str] = set()
                seen_default = False
                for f in stmt.fields:
                    if f.name in seen_fields:
                        _transpile_error(
                            f"Duplicate field '{f.name}' in struct {stmt.name}.",
                            f.span.line if f.span else 1,
                            f.span.column if f.span else 1,
                            f.name,
                        )
                    seen_fields.add(f.name)
                    if f.default is not None:
                        seen_default = True
                    elif seen_default:
                        _transpile_error(
                            f"Struct field '{f.name}' without a default cannot follow "
                            f"a field with a default in struct {stmt.name}.",
                            f.span.line if f.span else 1,
                            f.span.column if f.span else 1,
                            f.name,
                        )
                    if (
                        f.default is not None
                        and _is_null_lit(f.default)
                        and _nullable_inner(f.type_name) is None
                    ):
                        _transpile_error(
                            f"Struct field '{f.name}' cannot default to null.",
                            f.span.line if f.span else 1,
                            f.span.column if f.span else 1,
                            "null",
                        )
                continue
            if isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt, AugAssignStmt)):
                walk_expr(getattr(stmt, "value", None) or getattr(stmt, "expr", None))
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond)
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if stmt.body:
                    walk(stmt.body.statements)
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

    walk(body)


_SCREAMING_SNAKE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")


def _to_screaming_snake(name: str) -> str:
    """Suggest SCREAMING_SNAKE_CASE for an identifier."""
    if not name:
        return name
    if name.isupper() and "_" in name:
        return name
    spaced = re.sub(r"(?<!^)(?=[A-Z])", "_", name)
    spaced = re.sub(r"[\s\-]+", "_", spaced)
    return spaced.upper()


def _enum_info_map(
    body: list[Any],
    *,
    warnings: list | None = None,
) -> dict[str, dict[str, Any]]:
    """Build enum metadata; emit casing warnings; raise on declaration errors."""
    warnings = warnings if warnings is not None else []
    info: dict[str, dict[str, Any]] = {}
    for stmt in body:
        if not isinstance(stmt, EnumDef):
            continue
        line = stmt.span.line if stmt.span else 1
        col = stmt.span.column if stmt.span else 1
        if not stmt.members:
            _transpile_error(
                f"Enum '{stmt.name}' cannot be empty — declare at least one member.",
                line,
                col,
                f"enum {stmt.name}",
            )
        has_value = [m.value is not None for m in stmt.members]
        if any(has_value) and not all(has_value):
            bad = next(m for m in stmt.members if (m.value is None) == has_value[0])
            _transpile_error(
                f"Enum '{stmt.name}' must be fully implicit or fully explicit — "
                f"do not mix members with and without `=`.",
                bad.span.line if bad.span else line,
                bad.span.column if bad.span else col,
                bad.name,
            )
        value_kind = "auto"
        member_values: dict[str, str] = {}
        seen_names: set[str] = set()
        seen_values: dict[str, str] = {}
        if all(has_value):
            kinds: set[str] = set()
            for m in stmt.members:
                assert isinstance(m.value, Literal)
                if m.value.kind not in {"int", "string"}:
                    _transpile_error(
                        f"Enum member '{m.name}' value must be int or string.",
                        m.span.line if m.span else line,
                        m.span.column if m.span else col,
                        m.name,
                    )
                kinds.add(m.value.kind)
            if len(kinds) > 1:
                _transpile_error(
                    f"Enum '{stmt.name}' explicit values must be homogeneous "
                    f"(all int or all string).",
                    line,
                    col,
                    f"enum {stmt.name}",
                )
            value_kind = next(iter(kinds))
            for m in stmt.members:
                assert isinstance(m.value, Literal)
                key = m.value.text
                if key in seen_values:
                    _transpile_error(
                        f"Duplicate enum value in '{stmt.name}': "
                        f"'{m.name}' and '{seen_values[key]}' both use {key}.",
                        m.span.line if m.span else line,
                        m.span.column if m.span else col,
                        m.name,
                    )
                seen_values[key] = m.name
                member_values[m.name] = key
        for m in stmt.members:
            if m.name in seen_names:
                _transpile_error(
                    f"Duplicate enum member '{m.name}' in enum {stmt.name}.",
                    m.span.line if m.span else line,
                    m.span.column if m.span else col,
                    m.name,
                )
            seen_names.add(m.name)
            if not _SCREAMING_SNAKE.match(m.name):
                suggested = _to_screaming_snake(m.name)
                _transpile_warning(
                    warnings,
                    f"Enum member '{m.name}' should be SCREAMING_SNAKE_CASE "
                    f"(suggested: {suggested}).",
                    m.span.line if m.span else line,
                    m.span.column if m.span else col,
                    m.name,
                    code="pys.enum-naming",
                    suggested_fix=suggested,
                    tips=[
                        "Rename the member to SCREAMING_SNAKE_CASE "
                        "(e.g. OK, NOT_FOUND).",
                    ],
                )
        info[stmt.name] = {
            "members": [m.name for m in stmt.members],
            "value_kind": value_kind,
            "member_values": member_values,
        }
    return info


_SWITCH_PRIMITIVES = frozenset({"int", "string", "char", "bool", "float"}) | _WIDTH_ALIASES


def _switch_subject_type(
    expr: Expr | None,
    types: dict[str, str],
    enum_info: dict[str, dict[str, Any]],
    class_names: set[str],
) -> str | None:
    if expr is None:
        return None
    if isinstance(expr, Identifier):
        declared = types.get(expr.name, "") or ""
        if _result_type_parts(declared) or _nullable_inner(declared):
            return declared
        t = _base_type_name(declared)
        if t:
            return t
    if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
        # Built-in recoverable parsers (also seeded in analyze()).
        if expr.callee.name == "parseFloat":
            return "result<float, string>"
        if expr.callee.name == "parseInt":
            return "result<int, string>"
    if isinstance(expr, Member) and isinstance(expr.object, Identifier):
        ename = expr.object.name
        if ename in enum_info and expr.name in enum_info[ename]["members"]:
            return ename
    return _infer_type(expr, class_names)


def _switch_label_key(
    label: Expr,
    *,
    subject_type: str,
    enum_info: dict[str, dict[str, Any]],
) -> tuple[str, str] | None:
    """Return a comparable key for duplicate detection, or None if invalid shape."""
    if isinstance(label, Literal):
        return (label.kind, label.text)
    if isinstance(label, Member) and isinstance(label.object, Identifier):
        return ("enum", f"{label.object.name}.{label.name}")
    if isinstance(label, Identifier):
        if subject_type in enum_info:
            return ("enum", f"{subject_type}.{label.name}")
        return ("ident", label.name)
    return None


def _resolve_switch_label(
    label: Expr,
    *,
    subject_type: str,
    enum_info: dict[str, dict[str, Any]],
) -> Expr:
    """Rewrite bare enum member labels to ``Enum.MEMBER``; return label otherwise."""
    if (
        isinstance(label, Identifier)
        and subject_type in enum_info
        and label.name in enum_info[subject_type]["members"]
    ):
        sp = label.span
        return Member(
            span=sp,
            object=Identifier(span=sp, name=subject_type),
            name=label.name,
        )
    return label


def _validate_switch_label(
    label: Expr,
    *,
    subject_type: str,
    enum_info: dict[str, dict[str, Any]],
    allow_null: bool = False,
) -> None:
    line = label.span.line if label.span else 1
    col = label.span.column if label.span else 1
    if isinstance(label, Literal) and label.kind == "null":
        if allow_null:
            return
        _transpile_error(
            "Switch case labels cannot be null.",
            line,
            col,
            "null",
            code="pys.switch-label",
        )
    if subject_type in enum_info:
        members = set(enum_info[subject_type]["members"])
        if isinstance(label, Member) and isinstance(label.object, Identifier):
            if label.object.name != subject_type:
                _transpile_error(
                    f"Switch on {subject_type} cannot use label from enum "
                    f"{label.object.name}.",
                    line,
                    col,
                    label.object.name,
                    code="pys.switch-label",
                )
            if label.name not in members:
                _transpile_error(
                    f"'{label.name}' is not a member of enum {subject_type}.",
                    line,
                    col,
                    label.name,
                    code="pys.switch-label",
                    tips=[f"Known members: {', '.join(enum_info[subject_type]['members'])}."],
                )
            return
        if isinstance(label, Identifier):
            if label.name not in members:
                _transpile_error(
                    f"Unknown enum member '{label.name}' for switch on {subject_type}.",
                    line,
                    col,
                    label.name,
                    code="pys.switch-label",
                    tips=[
                        f"Use a member of {subject_type}, or qualify as "
                        f"{subject_type}.{label.name}."
                    ],
                )
            return
        _transpile_error(
            f"Switch on enum {subject_type} requires enum member labels "
            f"(e.g. {subject_type}.MEMBER or bare MEMBER).",
            line,
            col,
            getattr(label, "text", None) or getattr(label, "name", "label"),
            code="pys.switch-label",
        )
    # Primitive / int-like subjects: require compatible literals.
    expected_kind = "int" if subject_type in _INT_LIKE else subject_type
    if isinstance(label, Literal):
        kind = label.kind
        if expected_kind == "int" and kind == "int":
            return
        if kind == expected_kind:
            return
        _transpile_error(
            f"Switch on {subject_type} cannot use {kind} label.",
            line,
            col,
            label.text,
            code="pys.switch-label",
        )
    _transpile_error(
        f"Switch on {subject_type} requires {expected_kind} literal case labels.",
        line,
        col,
        getattr(label, "name", None) or "label",
        code="pys.switch-label",
    )


def _check_one_switch(
    *,
    subject: Expr | None,
    cases: list[SwitchCase],
    is_expr: bool,
    span_line: int,
    span_col: int,
    types: dict[str, str],
    enum_info: dict[str, dict[str, Any]],
    warnings: list,
    class_names: set[str],
) -> None:
    subject_type = _switch_subject_type(subject, types, enum_info, class_names)
    if not subject_type:
        _transpile_error(
            "Cannot determine type of switch subject.",
            subject.span.line if subject and subject.span else span_line,
            subject.span.column if subject and subject.span else span_col,
            "switch",
            code="pys.switch-subject",
            tips=["Declare the subject with a type (enum, int, string, char, or bool)."],
        )
    result_parts = _result_type_parts(subject_type)
    if result_parts:
        success_type, error_type = result_parts
        seen_patterns: set[str] = set()
        has_default = False
        arm_value_types: list[str | None] = []

        def result_arm_type(case: SwitchCase) -> str | None:
            value = case.value
            if isinstance(value, Identifier):
                for label in case.labels:
                    if (
                        isinstance(label, ResultPattern)
                        and label.binding == value.name
                    ):
                        return (
                            success_type if label.kind == "ok" else error_type
                        )
            return _infer_type(value, class_names)

        for case in cases:
            line = case.span.line if case.span else span_line
            col = case.span.column if case.span else span_col
            if case.is_default:
                if has_default:
                    _transpile_error(
                        "Switch may have at most one `default` arm.",
                        line,
                        col,
                        "default",
                        code="pys.switch-default",
                    )
                has_default = True
                if is_expr:
                    arm_value_types.append(result_arm_type(case))
                continue
            if len(case.labels) != 1 or not isinstance(
                case.labels[0], ResultPattern
            ):
                _transpile_error(
                    "Switch on a result requires `ok(value)` and `err(error)` "
                    "case patterns.",
                    line,
                    col,
                    "case",
                    code="pys.result-pattern",
                    tips=["Use `case ok(value)` or `case err(error)`."],
                )
            pattern = case.labels[0]
            if pattern.kind in seen_patterns:
                _transpile_error(
                    f"Duplicate result pattern '{pattern.kind}'.",
                    pattern.span.line if pattern.span else line,
                    pattern.span.column if pattern.span else col,
                    pattern.kind,
                    code="pys.switch-duplicate",
                )
            seen_patterns.add(pattern.kind)
            if pattern.binding in {"ok", "err"}:
                _transpile_error(
                    f"'{pattern.binding}' is reserved and cannot be a pattern binding.",
                    pattern.span.line if pattern.span else line,
                    pattern.span.column if pattern.span else col,
                    pattern.binding,
                    code="pys.result-reserved",
                )
            if pattern.kind == "ok":
                if success_type == "void" and pattern.binding:
                    _transpile_error(
                        "`result<void, E>` uses `case ok()` without a payload binding.",
                        line,
                        col,
                        pattern.binding,
                        code="pys.result-pattern",
                    )
                if success_type != "void" and not pattern.binding:
                    _transpile_error(
                        f"`ok` contains a {success_type} value; bind it as "
                        "`case ok(value)`.",
                        line,
                        col,
                        "ok",
                        code="pys.result-pattern",
                    )
            elif not pattern.binding:
                _transpile_error(
                    "`err` requires an error payload binding.",
                    line,
                    col,
                    "err",
                    code="pys.result-pattern",
                )
            if case.fallthrough:
                _transpile_error(
                    "Result pattern cases cannot fall through with `continue`.",
                    line,
                    col,
                    "continue",
                    code="pys.result-pattern",
                )
            if is_expr:
                arm_value_types.append(result_arm_type(case))

        missing = [kind for kind in ("ok", "err") if kind not in seen_patterns]
        if missing and not has_default:
            _transpile_error(
                "Result switch is not exhaustive "
                f"(missing {', '.join(missing)}); add the pattern or `default`.",
                span_line,
                span_col,
                "switch",
                code="pys.switch-exhaustive",
                tips=["Handle both success and failure explicitly."],
            )
        if is_expr:
            if any(t is None for t in arm_value_types):
                _transpile_error(
                    "Cannot infer a common type for result switch expression arms.",
                    span_line,
                    span_col,
                    "switch",
                    code="pys.switch-type",
                )
            first = arm_value_types[0] if arm_value_types else None
            if any(t != first for t in arm_value_types):
                _transpile_error(
                    "All result switch expression arms must yield the same type.",
                    span_line,
                    span_col,
                    "switch",
                    code="pys.switch-type",
                )
        return
    nullable_subject = _nullable_inner(subject_type)
    if nullable_subject is not None:
        subject_type = nullable_subject
    if subject_type not in enum_info and subject_type not in _SWITCH_PRIMITIVES:
        _transpile_error(
            f"Switch subject type '{subject_type}' is not supported "
            f"(use an enum or equality-comparable primitive).",
            subject.span.line if subject and subject.span else span_line,
            subject.span.column if subject and subject.span else span_col,
            subject_type,
            code="pys.switch-subject",
        )

    seen_keys: set[tuple[str, str]] = set()
    covered_members: set[str] = set()
    has_default = False
    arm_value_types: list[str | None] = []

    for idx, case in enumerate(cases):
        line = case.span.line if case.span else span_line
        col = case.span.column if case.span else span_col
        if case.fallthrough and idx == len(cases) - 1:
            _transpile_error(
                "`continue` fall-through requires a following case.",
                line,
                col,
                "continue",
                code="pys.switch-fallthrough",
            )
        if case.is_default:
            if has_default:
                _transpile_error(
                    "Switch may have at most one `default` arm.",
                    line,
                    col,
                    "default",
                    code="pys.switch-default",
                )
            has_default = True
            if is_expr:
                arm_value_types.append(
                    "result"
                    if isinstance(case.value, ResultCtor)
                    else _infer_type(case.value, class_names)
                )
            continue

        resolved: list[Expr] = []
        for label in case.labels:
            _validate_switch_label(
                label,
                subject_type=subject_type,
                enum_info=enum_info,
                allow_null=nullable_subject is not None,
            )
            key = _switch_label_key(
                label, subject_type=subject_type, enum_info=enum_info
            )
            if key is None:
                _transpile_error(
                    "Invalid switch case label.",
                    label.span.line if label.span else line,
                    label.span.column if label.span else col,
                    "case",
                    code="pys.switch-label",
                )
            if key in seen_keys:
                _transpile_error(
                    f"Duplicate switch case label '{key[1]}'.",
                    label.span.line if label.span else line,
                    label.span.column if label.span else col,
                    key[1],
                    code="pys.switch-duplicate",
                )
            seen_keys.add(key)
            new_label = _resolve_switch_label(
                label, subject_type=subject_type, enum_info=enum_info
            )
            resolved.append(new_label)
            if subject_type in enum_info and isinstance(new_label, Member):
                covered_members.add(new_label.name)
        case.labels = resolved
        if is_expr:
            arm_value_types.append(
                "result"
                if isinstance(case.value, ResultCtor)
                else _infer_type(case.value, class_names)
            )

    if is_expr:
        if any(t is None for t in arm_value_types):
            _transpile_error(
                "Cannot infer a common type for switch expression arms.",
                span_line,
                span_col,
                "switch",
                code="pys.switch-type",
            )
        first = arm_value_types[0]
        if any(t != first for t in arm_value_types):
            _transpile_error(
                "All switch expression arms must yield the same type "
                f"(found {', '.join(sorted({t for t in arm_value_types if t}))}).",
                span_line,
                span_col,
                "switch",
                code="pys.switch-type",
            )
        if subject_type in enum_info:
            missing = [
                m for m in enum_info[subject_type]["members"] if m not in covered_members
            ]
            if missing and not has_default:
                _transpile_error(
                    f"Switch expression on {subject_type} is not exhaustive "
                    f"(missing {', '.join(missing)}); add the members or `default`.",
                    span_line,
                    span_col,
                    "switch",
                    code="pys.switch-exhaustive",
                    tips=["Expression switches must yield a value on every path."],
                )
        elif not has_default:
            _transpile_error(
                f"Switch expression on {subject_type} requires a `default` arm.",
                span_line,
                span_col,
                "switch",
                code="pys.switch-default",
            )
    else:
        # Statement: warn when not proven exhaustive and no default.
        if not has_default:
            if subject_type in enum_info:
                missing = [
                    m
                    for m in enum_info[subject_type]["members"]
                    if m not in covered_members
                ]
                if missing:
                    _transpile_warning(
                        warnings,
                        f"Switch on {subject_type} is not exhaustive "
                        f"(missing {', '.join(missing)}); consider adding `default`.",
                        span_line,
                        span_col,
                        "switch",
                        code="pys.switch-exhaustive",
                        tips=[
                            "Statement switches warn when cases may not cover all members."
                        ],
                    )
            else:
                _transpile_warning(
                    warnings,
                    f"Switch on {subject_type} is not exhaustive without `default`.",
                    span_line,
                    span_col,
                    "switch",
                    code="pys.switch-exhaustive",
                    tips=["Add a `default` arm for values not listed in `case` labels."],
                )


def _check_switch(
    body: list[Any],
    *,
    types: dict[str, str],
    enum_info: dict[str, dict[str, Any]],
    warnings: list,
    class_names: set[str],
) -> None:
    """Resolve labels, enforce exhaustiveness/default, unify expression types."""

    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        if isinstance(expr, SwitchExpr):
            _check_one_switch(
                subject=expr.subject,
                cases=expr.cases,
                is_expr=True,
                span_line=expr.span.line if expr.span else 1,
                span_col=expr.span.column if expr.span else 1,
                types=types,
                enum_info=enum_info,
                warnings=warnings,
                class_names=class_names,
            )
            walk_expr(expr.subject)
            for case in expr.cases:
                for lab in case.labels:
                    walk_expr(lab)
                walk_expr(case.value)
            return
        for attr in (
            "left",
            "right",
            "operand",
            "value",
            "expr",
            "cond",
            "callee",
            "object",
            "index",
            "subject",
        ):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, KeywordArg):
                    walk_expr(a.value)
                elif isinstance(a, Expr):
                    walk_expr(a)
        elements = getattr(expr, "elements", None)
        if isinstance(elements, list):
            for el in elements:
                if isinstance(el, Expr):
                    walk_expr(el)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, SwitchStmt):
                _check_one_switch(
                    subject=stmt.subject,
                    cases=stmt.cases,
                    is_expr=False,
                    span_line=stmt.span.line if stmt.span else 1,
                    span_col=stmt.span.column if stmt.span else 1,
                    types=types,
                    enum_info=enum_info,
                    warnings=warnings,
                    class_names=class_names,
                )
                walk_expr(stmt.subject)
                for case in stmt.cases:
                    for lab in case.labels:
                        walk_expr(lab)
                    if case.body:
                        walk(case.body.statements)
                continue
            if isinstance(stmt, AssignStmt):
                if stmt.declare_type and stmt.declare_type != "var":
                    types[stmt.name] = stmt.declare_type
                walk_expr(stmt.value)
            elif isinstance(stmt, SharedDecl):
                if stmt.declare_type:
                    types[stmt.name] = stmt.declare_type
                walk_expr(stmt.value)
            elif isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt, AugAssignStmt)):
                walk_expr(getattr(stmt, "value", None) or getattr(stmt, "expr", None))
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond)
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if isinstance(stmt, ForEachStmt):
                    walk_expr(stmt.iterable)
                elif isinstance(stmt, WhileStmt):
                    walk_expr(stmt.cond)
                if stmt.body:
                    walk(stmt.body.statements)
            elif isinstance(stmt, FunctionDef) and stmt.body:
                local_types = dict(types)
                local_types.update(zip(stmt.params, stmt.param_types))
                _check_switch(
                    stmt.body.statements,
                    types=local_types,
                    enum_info=enum_info,
                    warnings=warnings,
                    class_names=class_names,
                )
            elif isinstance(stmt, (ClassDef, EntityDef)):
                for m in stmt.methods:
                    if m.body:
                        local_types = dict(types)
                        local_types.update(zip(m.params, m.param_types))
                        _check_switch(
                            m.body.statements,
                            types=local_types,
                            enum_info=enum_info,
                            warnings=warnings,
                            class_names=class_names,
                        )
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        _check_switch(
                            t.body.statements,
                            types=dict(types),
                            enum_info=enum_info,
                            warnings=warnings,
                            class_names=class_names,
                        )

    walk(body)


def _check_enums(
    body: list[Any],
    *,
    types: dict[str, str],
    fixed: set[str],
    enum_info: dict[str, dict[str, Any]],
) -> None:
    """SA: construction, ==, .value, immutability for enum types."""

    def expr_enum_type(expr: Expr | None) -> str | None:
        if expr is None:
            return None
        if isinstance(expr, Member) and isinstance(expr.object, Identifier):
            ename = expr.object.name
            if ename in enum_info and expr.name in enum_info[ename]["members"]:
                return ename
            # binding.MEMBER is not valid for enums; only EnumName.MEMBER
        if isinstance(expr, Identifier):
            t = _base_type_name(types.get(expr.name, ""))
            if t in enum_info:
                return t
        return None

    def underlying_of(enum_name: str) -> str:
        kind = enum_info[enum_name]["value_kind"]
        if kind == "string":
            return "string"
        return "int"  # auto and int

    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            if expr.callee.name in enum_info:
                _transpile_error(
                    f"Enum '{expr.callee.name}' values are constructed as "
                    f"{expr.callee.name}.MEMBER, not by calling the type.",
                    expr.span.line if expr.span else 1,
                    expr.span.column if expr.span else 1,
                    expr.callee.name,
                )
        if isinstance(expr, Member):
            if isinstance(expr.object, Identifier):
                ename = expr.object.name
                if ename in enum_info:
                    if expr.name == "value":
                        _transpile_error(
                            f"'.value' applies to enum members/variables, not the type "
                            f"'{ename}'.",
                            expr.span.line if expr.span else 1,
                            expr.span.column if expr.span else 1,
                            ".value",
                        )
                    elif expr.name not in enum_info[ename]["members"]:
                        _transpile_error(
                            f"'{expr.name}' is not a member of enum {ename}.",
                            expr.span.line if expr.span else 1,
                            expr.span.column if expr.span else 1,
                            expr.name,
                        )
                else:
                    root_t = _base_type_name(types.get(ename, ""))
                    if root_t in enum_info and expr.name not in {"value"} | set(
                        enum_info[root_t]["members"]
                    ):
                        # Allow .value on enum-typed bindings; reject unknown attrs.
                        if expr.name != "value":
                            _transpile_error(
                                f"'{expr.name}' is not a valid access on enum {root_t} "
                                f"(use .value for the underlying value).",
                                expr.span.line if expr.span else 1,
                                expr.span.column if expr.span else 1,
                                expr.name,
                            )
            # Nested: EnumName.MEMBER.value
            if (
                isinstance(expr.object, Member)
                and expr.name == "value"
                and isinstance(expr.object.object, Identifier)
            ):
                ename = expr.object.object.name
                if ename in enum_info and expr.object.name in enum_info[ename]["members"]:
                    pass  # ok
            walk_expr(expr.object)
            return
        if isinstance(expr, BinaryOp) and expr.op in {"==", "!="}:
            left_e = expr_enum_type(expr.left)
            right_e = expr_enum_type(expr.right)
            left_t = left_e or _infer_type(expr.left, set(enum_info))
            right_t = right_e or _infer_type(expr.right, set(enum_info))
            if left_e or right_e:
                if left_e and right_e and left_e != right_e:
                    _transpile_error(
                        f"Cannot compare enum {left_e} with enum {right_e} — "
                        f"only members of the same enum may use '{expr.op}'.",
                        expr.span.line if expr.span else 1,
                        expr.span.column if expr.span else 1,
                        expr.op,
                    )
                elif (left_e and not right_e) or (right_e and not left_e):
                    other = right_t if left_e else left_t
                    en = left_e or right_e
                    if other in {"int", "string", "float", "bool", "char"} or (
                        other and other in enum_info and other != en
                    ):
                        _transpile_error(
                            f"Cannot compare enum {en} with {other or 'non-enum'} — "
                            f"use .value for underlying interchange, or compare "
                            f"same-enum members.",
                            expr.span.line if expr.span else 1,
                            expr.span.column if expr.span else 1,
                            expr.op,
                        )
            walk_expr(expr.left)
            walk_expr(expr.right)
            return
        if isinstance(expr, SwitchExpr):
            walk_expr(expr.subject)
            for case in expr.cases:
                for lab in case.labels:
                    walk_expr(lab)
                walk_expr(case.value)
            return
        for attr in ("left", "right", "operand", "value", "expr", "cond", "callee", "object", "index"):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, KeywordArg):
                    walk_expr(a.value)
                elif isinstance(a, Expr):
                    walk_expr(a)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AssignStmt):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                walk_expr(stmt.value)
                # Reject EnumName.MEMBER = ... and enum_var.member = ...
                if "." in stmt.name:
                    parts = stmt.name.split(".")
                    root = parts[0]
                    if root in enum_info:
                        _transpile_error(
                            f"Cannot assign to enum member '{stmt.name}' — "
                            f"enum members are immutable.",
                            line,
                            col,
                            stmt.name,
                        )
                    root_t = _base_type_name(types.get(root, ""))
                    if root_t in enum_info:
                        _transpile_error(
                            f"Cannot assign through enum-typed '{root}' — "
                            f"enum values are immutable.",
                            line,
                            col,
                            stmt.name,
                        )
                if stmt.declare_type:
                    base = _base_type_name(stmt.declare_type)
                    if base in enum_info:
                        # Reject bare int/string assignment (already covered by
                        # _check_bindings type mismatch when inferred).
                        if _is_null_lit(stmt.value):
                            _transpile_error(
                                f"Enum-typed binding '{stmt.name}' cannot be null.",
                                line,
                                col,
                                "null",
                            )
                continue
            if isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt, AugAssignStmt)):
                walk_expr(getattr(stmt, "value", None) or getattr(stmt, "expr", None))
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond)
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, SwitchStmt):
                walk_expr(stmt.subject)
                for case in stmt.cases:
                    for lab in case.labels:
                        walk_expr(lab)
                    if case.body:
                        walk(case.body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if isinstance(stmt, ForEachStmt):
                    walk_expr(stmt.iterable)
                elif isinstance(stmt, WhileStmt):
                    walk_expr(stmt.cond)
                if stmt.body:
                    walk(stmt.body.statements)
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

    walk(body)


def _parse_lambda_type_parts(type_name: str) -> tuple[list[str], str] | None:
    """Split `lambda<P…, R>` into (param_types, return_type). `lambda<R>` → ([], R)."""
    name = (type_name or "").strip()
    if not name.startswith("lambda<") or not name.endswith(">"):
        return None
    inner = name[len("lambda<") : -1].strip()
    if not inner:
        return None
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(inner):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(inner[start:i].strip())
            start = i + 1
    parts.append(inner[start:].strip())
    if not parts or any(not p for p in parts):
        return None
    if len(parts) == 1:
        return [], parts[0]
    return parts[:-1], parts[-1]


def _infer_lambda_params(expr: LambdaExpr, target_type: str) -> None:
    """Fill omitted param types from a declared `lambda<…>` target (mutates expr)."""
    parsed = _parse_lambda_type_parts(target_type)
    if parsed is None:
        return
    param_types, _ret = parsed
    if len(param_types) != len(expr.params):
        line = expr.span.line if expr.span else 1
        col = expr.span.column if expr.span else 1
        _transpile_error(
            f"Lambda has {len(expr.params)} parameter(s) but type `{target_type}` "
            f"expects {len(param_types)}.",
            line,
            col,
            "=>",
            code="pys.lambda-arity",
        )
    for i, t in enumerate(param_types):
        if i < len(expr.param_types) and not expr.param_types[i]:
            expr.param_types[i] = t


def _check_lambdas(body: list[Any], *, types: dict[str, str]) -> None:
    """Infer lambda params from context; enforce capture mutation rules."""
    fn_param_types: dict[str, list[str]] = {}
    for stmt in body:
        if isinstance(stmt, FunctionDef):
            fn_param_types[stmt.name] = list(stmt.param_types)

    def check_assign_in_lambda(
        stmt: AssignStmt | AugAssignStmt,
        *,
        lambda_locals: set[str],
        shared: set[str],
        declared: set[str],
    ) -> None:
        if not _is_simple_name(stmt.name):
            return
        name = stmt.name
        if name in lambda_locals or name in shared:
            return
        if name not in declared:
            return
        line = stmt.span.line if stmt.span else 1
        col = stmt.span.column if stmt.span else 1
        op = getattr(stmt, "op", "=")
        _transpile_error(
            f"Cannot mutate captured variable '{name}' inside lambda — "
            f"declare it 'shared' or 'atomic' if mutation across closures is intended.",
            line,
            col,
            f"{name}{op}" if op != "=" else f"{name} = ...",
            code="pys.lambda-capture",
            tips=[
                f"Write `shared <type> {name} = …` or `atomic <type> {name} = …` "
                f"at the outer scope."
            ],
        )

    def walk_expr(
        expr: Expr | None,
        *,
        declared: set[str],
        shared: set[str],
        expected_type: str = "",
    ) -> None:
        if expr is None:
            return
        if isinstance(expr, LambdaExpr):
            if expected_type:
                _infer_lambda_params(expr, expected_type)
            lambda_locals = set(expr.params)
            if isinstance(expr.body, Block):
                walk_stmts(
                    expr.body.statements,
                    declared=declared,
                    shared=shared,
                    in_lambda=True,
                    lambda_locals=lambda_locals,
                )
            else:
                walk_expr(expr.body, declared=declared, shared=shared)
            return
        if isinstance(expr, Call):
            walk_expr(expr.callee, declared=declared, shared=shared)
            callee_name = ""
            if isinstance(expr.callee, Identifier):
                callee_name = expr.callee.name
            ptypes = fn_param_types.get(callee_name, [])
            for i, a in enumerate(expr.args):
                if isinstance(a, KeywordArg):
                    walk_expr(
                        a.value,
                        declared=declared,
                        shared=shared,
                        expected_type="",
                    )
                    continue
                et = ptypes[i] if i < len(ptypes) else ""
                walk_expr(a, declared=declared, shared=shared, expected_type=et)
            return
        if isinstance(expr, KeywordArg):
            walk_expr(expr.value, declared=declared, shared=shared)
            return
        for attr in (
            "left",
            "right",
            "operand",
            "value",
            "expr",
            "cond",
            "object",
            "index",
            "target",
        ):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child, declared=declared, shared=shared)
        elems = getattr(expr, "elements", None)
        if isinstance(elems, list):
            for e in elems:
                if isinstance(e, Expr):
                    walk_expr(e, declared=declared, shared=shared)
        if isinstance(expr, SwitchExpr):
            for case in expr.cases:
                walk_expr(case.value, declared=declared, shared=shared)
            walk_expr(expr.subject, declared=declared, shared=shared)

    def walk_stmts(
        stmts: list[Any],
        *,
        declared: set[str],
        shared: set[str],
        in_lambda: bool = False,
        lambda_locals: set[str] | None = None,
    ) -> None:
        declared = set(declared)
        shared = set(shared)
        lambda_locals = set(lambda_locals or ())
        for stmt in stmts:
            if isinstance(stmt, SharedDecl):
                declared.add(stmt.name)
                shared.add(stmt.name)
                continue
            if isinstance(stmt, AtomicDecl):
                declared.add(stmt.name)
                shared.add(stmt.name)
                continue
            if isinstance(stmt, AssignStmt):
                if in_lambda and not (stmt.declare_type or stmt.is_const or stmt.is_fix):
                    check_assign_in_lambda(
                        stmt,
                        lambda_locals=lambda_locals,
                        shared=shared,
                        declared=declared,
                    )
                et = ""
                if stmt.declare_type and stmt.declare_type.startswith("lambda"):
                    et = stmt.declare_type
                walk_expr(stmt.value, declared=declared, shared=shared, expected_type=et)
                if stmt.declare_type or stmt.is_const or stmt.is_fix:
                    declared.add(stmt.name)
                    if in_lambda:
                        lambda_locals.add(stmt.name)
            elif isinstance(stmt, AugAssignStmt):
                if in_lambda:
                    check_assign_in_lambda(
                        stmt,
                        lambda_locals=lambda_locals,
                        shared=shared,
                        declared=declared,
                    )
                walk_expr(stmt.value, declared=declared, shared=shared)
            elif isinstance(stmt, ArrayDecl):
                declared.add(stmt.name)
                if in_lambda:
                    lambda_locals.add(stmt.name)
            elif isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt)):
                val = getattr(stmt, "value", None) or getattr(stmt, "expr", None)
                walk_expr(val, declared=declared, shared=shared)
            elif isinstance(stmt, FunctionDef):
                local = set(declared) | set(stmt.params)
                if stmt.body:
                    # Match params to lambda types for nested inference in body.
                    walk_stmts(stmt.body.statements, declared=local, shared=shared)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    local = set(declared) | set(m.params)
                    if m.body:
                        walk_stmts(m.body.statements, declared=local, shared=shared)
            elif isinstance(stmt, EntityDef):
                for m in stmt.methods:
                    local = set(declared) | set(m.params)
                    if m.body:
                        walk_stmts(m.body.statements, declared=local, shared=shared)
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond, declared=declared, shared=shared)
                if stmt.then_body:
                    walk_stmts(
                        stmt.then_body.statements,
                        declared=declared,
                        shared=shared,
                        in_lambda=in_lambda,
                        lambda_locals=lambda_locals,
                    )
                if stmt.else_body:
                    walk_stmts(
                        stmt.else_body.statements,
                        declared=declared,
                        shared=shared,
                        in_lambda=in_lambda,
                        lambda_locals=lambda_locals,
                    )
            elif isinstance(stmt, Block):
                walk_stmts(
                    stmt.statements,
                    declared=declared,
                    shared=shared,
                    in_lambda=in_lambda,
                    lambda_locals=lambda_locals,
                )
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if isinstance(stmt, WhileStmt):
                    walk_expr(stmt.cond, declared=declared, shared=shared)
                if isinstance(stmt, ForEachStmt):
                    walk_expr(stmt.iterable, declared=declared, shared=shared)
                    local = set(declared) | {stmt.var}
                elif isinstance(stmt, ForRangeStmt):
                    local = set(declared) | {stmt.var}
                else:
                    local = declared
                if stmt.body:
                    walk_stmts(
                        stmt.body.statements,
                        declared=local,
                        shared=shared,
                        in_lambda=in_lambda,
                        lambda_locals=lambda_locals,
                    )
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk_stmts(
                            t.body.statements,
                            declared=set(declared) | set(t.params),
                            shared=shared,
                        )
            elif isinstance(stmt, SwitchStmt):
                walk_expr(stmt.subject, declared=declared, shared=shared)
                for case in stmt.cases:
                    if case.body:
                        walk_stmts(
                            case.body.statements,
                            declared=declared,
                            shared=shared,
                            in_lambda=in_lambda,
                            lambda_locals=lambda_locals,
                        )

    walk_stmts(body, declared=set(types), shared=set())


_ATOMIC_FORBIDDEN_OPS = frozenset({"*=", "/=", "%="})
_ATOMIC_METHODS = frozenset({"get", "compareAndSet"})


def _check_atomics(body: list[Any], *, types: dict[str, str]) -> None:
    """Reject non-guaranteed ops; validate get / compareAndSet; other members ban."""

    atomic: set[str] = set()

    def walk_expr(expr: Expr | None) -> None:
        if expr is None:
            return
        if isinstance(expr, Call) and isinstance(expr.callee, Member):
            mem = expr.callee
            if isinstance(mem.object, Identifier) and mem.object.name in atomic:
                line = expr.span.line if expr.span else (
                    mem.span.line if mem.span else 1
                )
                col = expr.span.column if expr.span else (
                    mem.span.column if mem.span else 1
                )
                if mem.name == "get":
                    if expr.args:
                        _transpile_error(
                            "`get()` on an atomic variable takes no arguments.",
                            line,
                            col,
                            f"{mem.object.name}.get(...)",
                            code="pys.atomic-op",
                            tips=["Write `name.get()` with an empty argument list."],
                        )
                elif mem.name == "compareAndSet":
                    if len(expr.args) != 2:
                        _transpile_error(
                            "`compareAndSet` on an atomic variable requires "
                            "exactly two arguments: expected and newValue.",
                            line,
                            col,
                            f"{mem.object.name}.compareAndSet(...)",
                            code="pys.atomic-op",
                            tips=[
                                "Write `name.compareAndSet(expected, newValue)` "
                                "and retry in a loop when it returns false."
                            ],
                        )
                else:
                    _transpile_error(
                        f"Atomic variable '{mem.object.name}' has no member "
                        f"'{mem.name}'. Allowed: get(), compareAndSet(expected, newValue).",
                        line,
                        col,
                        f"{mem.object.name}.{mem.name}",
                        code="pys.atomic-op",
                    )
                for a in expr.args:
                    if isinstance(a, KeywordArg):
                        walk_expr(a.value)
                    else:
                        walk_expr(a)
                walk_expr(mem.object)
                return
        if isinstance(expr, Member) and isinstance(expr.object, Identifier):
            if expr.object.name in atomic and expr.name not in _ATOMIC_METHODS:
                line = expr.span.line if expr.span else 1
                col = expr.span.column if expr.span else 1
                _transpile_error(
                    f"Atomic variable '{expr.object.name}' has no member "
                    f"'{expr.name}'. Allowed: get(), compareAndSet(expected, newValue).",
                    line,
                    col,
                    f"{expr.object.name}.{expr.name}",
                    code="pys.atomic-op",
                )
        for attr in (
            "left",
            "right",
            "operand",
            "value",
            "expr",
            "cond",
            "callee",
            "object",
            "index",
            "body",
            "subject",
        ):
            child = getattr(expr, attr, None)
            if isinstance(child, Expr):
                walk_expr(child)
        args = getattr(expr, "args", None)
        if isinstance(args, list):
            for a in args:
                if isinstance(a, KeywordArg):
                    walk_expr(a.value)
                elif isinstance(a, Expr):
                    walk_expr(a)
        elems = getattr(expr, "elements", None)
        if isinstance(elems, list):
            for e in elems:
                if isinstance(e, Expr):
                    walk_expr(e)
        if isinstance(expr, SwitchExpr):
            for case in expr.cases:
                walk_expr(case.value)
        if isinstance(expr, LambdaExpr) and isinstance(expr.body, Block):
            walk(expr.body.statements)

    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, AtomicDecl):
                atomic.add(stmt.name)
                walk_expr(stmt.value)
                continue
            if isinstance(stmt, AugAssignStmt) and _is_simple_name(stmt.name):
                if stmt.name in atomic and stmt.op in _ATOMIC_FORBIDDEN_OPS:
                    line = stmt.span.line if stmt.span else 1
                    col = stmt.span.column if stmt.span else 1
                    _transpile_error(
                        f"Operator '{stmt.op}' is not allowed on atomic "
                        f"'{stmt.name}' — multiply/divide/modulo are not "
                        f"guaranteed indivisible. Use get() / compareAndSet "
                        f"in a retry loop instead.",
                        line,
                        col,
                        f"{stmt.name} {stmt.op}",
                        code="pys.atomic-op",
                        tips=[
                            "Read with `name.get()`, then "
                            "`name.compareAndSet(expected, newValue)` until it succeeds."
                        ],
                    )
                walk_expr(stmt.value)
            elif isinstance(stmt, AssignStmt):
                walk_expr(stmt.value)
            elif isinstance(stmt, (PrintStmt, ReturnStmt, ExprStmt)):
                val = getattr(stmt, "value", None) or getattr(stmt, "expr", None)
                walk_expr(val)
            elif isinstance(stmt, FunctionDef) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, EntityDef):
                # Identity fields are `fix` members; `atomic` cannot appear there.
                # Belt-and-suspenders: reject if an identity key somehow collides
                # with a nested atomic binding of the same name in methods — N/A.
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, IfStmt):
                walk_expr(stmt.cond)
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, SwitchStmt):
                walk_expr(stmt.subject)
                for case in stmt.cases:
                    walk_expr(case.value)
                    if case.body:
                        walk(case.body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if isinstance(stmt, WhileStmt):
                    walk_expr(stmt.cond)
                elif isinstance(stmt, ForRangeStmt):
                    walk_expr(stmt.start)
                    walk_expr(stmt.stop)
                elif isinstance(stmt, ForEachStmt):
                    walk_expr(stmt.iterable)
                elif isinstance(stmt, RepeatStmt):
                    walk_expr(stmt.count)
                if stmt.body:
                    walk(stmt.body.statements)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements)

    walk(body)
    _ = types  # reserved for future typed CAS arg checks


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
            if isinstance(stmt, AtomicDecl):
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
                            f"Declare it `shared` or `atomic` to allow cross-task mutation.",
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
                            f"Declare it `shared` or `atomic` to allow cross-task mutation.",
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
        "parseFloat", "parseInt", "input",
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
            "package": "only within its package (same folder, or same root-relative path under pys.toml source_roots)",
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


def _array_dims(stmt: ArrayDecl) -> list[int | None]:
    dims = list(getattr(stmt, "dims", None) or [])
    if dims:
        return dims
    return [stmt.size]


def _check_array_init(
    elem_type: str,
    dims: list[int | None],
    value: Expr | None,
    *,
    name: str,
    line: int,
    col: int,
) -> None:
    if value is None:
        return
    if isinstance(value, ArrayAlloc):
        if value.elem_type and value.elem_type != elem_type:
            _transpile_error(
                f"Array '{name}' element type '{elem_type}' does not match allocation "
                f"'{value.elem_type}'.",
                line,
                col,
                f"{elem_type}{'[]' * len(dims)} {name}",
            )
        if len(value.dims) != len(dims):
            _transpile_error(
                f"Array '{name}' has rank {len(dims)} but allocation has rank {len(value.dims)}.",
                line,
                col,
                f"{elem_type}{'[]' * len(dims)} {name}",
            )
        return

    if not isinstance(value, (ArrayLiteral, BraceLiteral)):
        _transpile_error(
            f"Array '{name}' must be initialized with a list/brace literal or an allocation "
            f"like `{elem_type}[n][]…`.",
            line,
            col,
            f"{elem_type}{'[]' * len(dims)} {name}",
        )
        return

    rank = len(dims)
    expected = dims[0]
    elems = list(value.elements)
    if expected is not None and len(elems) != expected:
        if len(elems) > expected:
            _transpile_error(
                "Array index out of bounds, trying to place a value outside the array "
                f"(capacity {expected}, got {len(elems)} values).",
                line,
                col,
                f"{elem_type}[{expected}]{'[]' * (rank - 1)} {name}",
            )
        else:
            _transpile_error(
                f"Array '{name}' expects exactly {expected} elements, got {len(elems)}.",
                line,
                col,
                f"{elem_type}[{expected}]{'[]' * (rank - 1)} {name}",
            )

    if rank <= 1:
        for el in elems:
            if not _array_element_ok(elem_type, el):
                _transpile_error(
                    _array_element_error(elem_type, el),
                    line,
                    col,
                    f"{elem_type}[] {name}",
                )
        return

    for el in elems:
        if not isinstance(el, (ArrayLiteral, BraceLiteral)):
            _transpile_error(
                f"Array '{name}' rank {rank} initializer expects nested array literals.",
                line,
                col,
                f"{elem_type}{'[]' * rank} {name}",
            )
            continue
        _check_array_init(
            elem_type,
            dims[1:],
            el,
            name=name,
            line=line,
            col=col,
        )


def _check_arrays(body: list[Any]) -> None:
    def walk(stmts: list[Any]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ArrayDecl):
                line = stmt.span.line if stmt.span else 1
                col = stmt.span.column if stmt.span else 1
                dims = _array_dims(stmt)
                _check_array_init(
                    stmt.elem_type,
                    dims,
                    stmt.value,
                    name=stmt.name,
                    line=line,
                    col=col,
                )
            elif isinstance(stmt, FunctionDef) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, ClassDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, EntityDef):
                for m in stmt.methods:
                    if m.body:
                        walk(m.body.statements)
            elif isinstance(stmt, IfStmt):
                if stmt.then_body:
                    walk(stmt.then_body.statements)
                if stmt.else_body:
                    walk(stmt.else_body.statements)
            elif isinstance(stmt, Block):
                walk(stmt.statements)
            elif isinstance(stmt, ForEachStmt) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, ForRangeStmt) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, WhileStmt) and stmt.body:
                walk(stmt.body.statements)
            elif isinstance(stmt, SwitchStmt):
                for case in stmt.cases:
                    if case.body:
                        walk(case.body.statements)
            elif isinstance(stmt, TasksBlock):
                for t in stmt.tasks:
                    if t.body:
                        walk(t.body.statements)
            elif isinstance(stmt, RepeatStmt) and stmt.body:
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
