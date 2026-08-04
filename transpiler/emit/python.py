"""Python emitter for PYS AST."""
from __future__ import annotations

from pathlib import Path

import re

from ..ast_nodes import (
    ArrayAlloc,
    ArrayDecl,
    ArrayLiteral,
    AssignStmt,
    AugAssignStmt,
    AwaitExpr,
    BinaryOp,
    BlankStmt,
    Block,
    BraceLiteral,
    BreakStmt,
    Call,
    Cast,
    ClassDef,
    CommentStmt,
    ContinueStmt,
    DataDef,
    DictLiteral,
    EntityDef,
    Expr,
    ExprStmt,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    Identifier,
    IfStmt,
    ImportStmt,
    Index,
    InterfaceDef,
    InterpolatedString,
    KeywordArg,
    LambdaExpr,
    Literal,
    Member,
    MethodDef,
    Module,
    PassStmt,
    PrintStmt,
    PropagateExpr,
    RepeatStmt,
    ResultCtor,
    ResultPattern,
    ReturnStmt,
    SharedDecl,
    AtomicDecl,
    SetLiteral,
    Slice,
    EnumDef,
    StructDef,
    SwitchCase,
    SwitchExpr,
    SwitchStmt,
    TaskDef,
    TasksBlock,
    TraitDef,
    TupleLiteral,
    UnaryOp,
    WhileStmt,
)

_STRUCT_COPY_HELPER = '''def _pys_struct_copy(value):
    copy = getattr(value, "_pys_copy", None)
    return copy() if callable(copy) else value
'''
_RESULT_PREAMBLE = '''class _PysResult:
    __slots__ = ("_pys_result_kind", "value", "sites")

    def __init__(self, kind, value, sites=None):
        self._pys_result_kind = kind
        self.value = value
        self.sites = list(sites or ())

    def __repr__(self):
        return f"{self._pys_result_kind}({self.value!r})"


class _PysPropagateSignal(BaseException):
    __slots__ = ("result",)

    def __init__(self, result):
        self.result = result


def _pys_ok(value=None):
    return _PysResult("ok", value)


def _pys_err(value):
    return _PysResult("err", value)


def _pys_propagate(result, file, line, function):
    kind = getattr(result, "_pys_result_kind", None)
    if kind == "ok":
        return result.value
    if kind != "err":
        raise TypeError("propagate expected a PYS result value")
    sites = [*result.sites, (file, line, function)]
    raise _PysPropagateSignal(_PysResult("err", result.value, sites))


def _pys_panic(result):
    import sys as _pys_sys
    print(f"PYS panic: {result.value}", file=_pys_sys.stderr)
    for file, line, function in result.sites:
        print(f"  at {file}:{line} in {function}", file=_pys_sys.stderr)
    raise SystemExit(1)
'''
from ..language_spec import _default_value_for_type, _translate_string_literal

_CAST = {
    "int": "int",
    "float": "float",
    "char": "str",
    "string": "str",
    "bool": "bool",
    "byte": "int",
    "nibble": "int",
    "int16": "int",
    "int32": "int",
    "int64": "int",
    "dword": "int",
}
_ARRAY_TYPECODE = {"int": "i", "float": "d", "char": "u", "bool": "b"}
_BINOP_PREC = {
    "or": 1,
    "||": 1,
    "and": 2,
    "&&": 2,
    "in": 3,
    "==": 3,
    "!=": 3,
    "<": 3,
    ">": 3,
    "<=": 3,
    ">=": 3,
    "|": 4,
    "^": 5,
    "&": 6,
    "<<": 7,
    ">>": 7,
    "+": 8,
    "-": 8,
    "*": 9,
    "/": 9,
    "%": 9,
    "//": 9,
    "**": 10,
}


def emit(module: Module, *, source_path: Path | None = None) -> str:
    text, _maps, _names = emit_with_map(module, source_path=source_path)
    return text


def emit_with_map(
    module: Module,
    *,
    source_path: Path | None = None,
    is_entrypoint: bool = False,
) -> tuple[str, list[dict[str, int]], dict[str, str]]:
    """Emit Python, a statement-level line map, and debug display names.

    Each map entry is ``{"py": <1-based python line>, "pys": <1-based .pys line>}``.
    ``names`` maps emitted locals (e.g. ``_c_hits``) → PYS display names (``hits``).
    """
    emitter = _Emitter(
        source=module.source,
        source_path=source_path,
        is_entrypoint=is_entrypoint,
    )
    raw_text, origins = emitter.emit_module_with_origins(module)
    from .overloads import rewrite_overloaded_methods

    rewritten = rewrite_overloaded_methods(raw_text)
    line_map = _transfer_line_origins(
        raw_text.splitlines(),
        rewritten.splitlines(),
        origins,
    )
    return rewritten, line_map, dict(emitter.debug_names)


def _transfer_line_origins(
    old_lines: list[str],
    new_lines: list[str],
    origins: list[int | None],
) -> list[dict[str, int]]:
    """Move pys line origins across a post-pass that may insert/delete lines."""
    entries: list[dict[str, int]] = []
    if len(old_lines) == len(new_lines):
        for i, orig in enumerate(origins):
            if orig is not None:
                entries.append({"py": i + 1, "pys": orig})
        return entries
    j = 0
    for i, nl in enumerate(new_lines):
        while j < len(old_lines) and old_lines[j] != nl:
            j += 1
        if j >= len(old_lines):
            break
        orig = origins[j] if j < len(origins) else None
        if orig is not None:
            entries.append({"py": i + 1, "pys": orig})
        j += 1
    return entries


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
    raise TypeError(stmt.kind)


def _ctor_chains_to_parent(body: Block | None) -> bool:
    """True if the constructor already calls ``super(...)`` or ``this(...)``."""
    if body is None:
        return False
    for stmt in body.statements:
        if not isinstance(stmt, ExprStmt) or not isinstance(stmt.expr, Call):
            continue
        callee = stmt.expr.callee
        if isinstance(callee, Identifier) and callee.name in {"super", "this"}:
            return True
    return False


class _Emitter:
    def __init__(
        self,
        *,
        source: str = "",
        source_path: Path | None = None,
        is_entrypoint: bool = False,
    ) -> None:
        self.source_path = source_path
        self.is_entrypoint = is_entrypoint
        self.lines: list[str] = []
        self.needs_array = False
        self.needs_abc = False
        self.needs_concurrency = False
        self.needs_dataclass = False
        self.needs_struct_copy = False
        self.needs_enum = False
        self.needs_result = False
        self.shared_vars: set[str] = set()
        self.atomic_vars: set[str] = set()
        self.tg_name: str | None = None
        self.var_kinds: dict[str, str] = {}  # name -> "string"|"number"|...
        self.var_types: dict[str, str] = {}  # name -> PYS type (for struct copy)
        self.array_meta: dict[str, tuple[str, int]] = {}  # name -> (elem_type, rank)
        self.fn_return_types: dict[str, str] = {}
        self.struct_names: set[str] = set()
        self.struct_field_types: dict[str, dict[str, str]] = {}
        self.entity_defs: dict[str, EntityDef] = {}
        self.trait_defs: dict[str, TraitDef] = {}
        self.trait_names: set[str] = set()
        self.lambda_serial = 0
        self.result_switch_serial = 0
        self._current_function = "<module>"
        self._expr_indent = 0
        self._lambda_rename: dict[str, str] = {}
        self._brace_depth = 0
        self._scope_serial = 0
        self._current_pys_line: int | None = None
        self.line_origins: list[int | None] = []
        self.debug_names: dict[str, str] = {}  # emitted local -> PYS display name
        self._import_resolver = None
        if source_path is not None:
            from .. import imports as imports_mod

            self._import_resolver = imports_mod.make_resolver(source, source_path)

    def emit_module(self, module: Module) -> str:
        text, _origins = self.emit_module_with_origins(module)
        return text

    def _has_top_level_propagate(self, node: object | None) -> bool:
        if node is None:
            return False
        if isinstance(node, PropagateExpr):
            return True
        if isinstance(node, (FunctionDef, ClassDef, TraitDef, TasksBlock, LambdaExpr)):
            return False
        if isinstance(node, SwitchCase):
            return self._has_top_level_propagate(node.value) or self._has_top_level_propagate(
                node.body
            )
        if isinstance(node, list):
            return any(self._has_top_level_propagate(item) for item in node)
        if isinstance(node, tuple):
            return any(self._has_top_level_propagate(item) for item in node)
        if hasattr(node, "__dict__"):
            return any(
                self._has_top_level_propagate(value)
                for name, value in vars(node).items()
                if name not in {"span", "source", "analysis_warnings"}
            )
        return False

    def emit_module_with_origins(self, module: Module) -> tuple[str, list[int | None]]:
        self.lines = []
        self.line_origins = []
        self.debug_names = {}
        self._lambda_rename = {}
        self._brace_depth = 0
        self._scope_serial = 0
        self.struct_names = {
            s.name for s in module.body if isinstance(s, (StructDef, DataDef))
        }
        self.struct_field_types = {
            s.name: {f.name: f.type_name for f in s.fields}
            for s in module.body
            if isinstance(s, (StructDef, DataDef))
        }
        self.entity_defs = {
            s.name: s for s in module.body if isinstance(s, EntityDef)
        }
        self.trait_defs = {
            s.name: s for s in module.body if isinstance(s, TraitDef)
        }
        self.trait_names = set(self.trait_defs)
        self.fn_return_types = {
            s.name: s.return_type
            for s in module.body
            if isinstance(s, FunctionDef) and s.return_type
        }
        if self._import_resolver is not None:
            self.struct_names |= set(getattr(self._import_resolver, "structs", set()))
            self.fn_return_types.update(
                getattr(self._import_resolver, "function_returns", {})
            )
            for name, ftypes in getattr(self._import_resolver, "struct_field_types", {}).items():
                self.struct_field_types.setdefault(name, dict(ftypes))
        wrap_entrypoint = self.is_entrypoint and self._has_top_level_propagate(
            module.body
        )
        if wrap_entrypoint:
            self.needs_result = True
            self._current_function = "<entrypoint>"
            self._emit(0, "try:")
            if module.body:
                for stmt in module.body:
                    self._stmt(stmt, 1)
            else:
                self._emit(1, "pass")
            self._emit(0, "except _PysPropagateSignal as _pys_signal:")
            self._emit(1, "_pys_panic(_pys_signal.result)")
        else:
            for stmt in module.body:
                self._stmt(stmt, 0)
        preamble: list[str] = []
        if self.needs_concurrency:
            from ..concurrency import CONCURRENCY_PREAMBLE

            preamble.extend(CONCURRENCY_PREAMBLE.splitlines())
        if self.needs_abc:
            preamble.append("from abc import ABC, abstractmethod")
        if self.needs_array:
            preamble.append("from array import array")
        if self.needs_dataclass:
            preamble.append("from dataclasses import dataclass")
        if self.needs_enum:
            preamble.append("import enum")
        if self.needs_struct_copy:
            preamble.extend(_STRUCT_COPY_HELPER.splitlines())
        if self.needs_result:
            preamble.extend(_RESULT_PREAMBLE.splitlines())
        out = preamble + self.lines
        origins: list[int | None] = [None] * len(preamble) + list(self.line_origins)
        return "\n".join(out) + ("\n" if out else ""), origins

    def _append_raw(self, text: str, *, pys_line: int | None | object = ...) -> None:
        if pys_line is ...:
            pys_line = self._current_pys_line
        self.lines.append(text)
        self.line_origins.append(pys_line)  # type: ignore[arg-type]

    def _emit(self, indent: int, text: str) -> None:
        self._append_raw(("    " * indent) + text)

    def _stmt(self, stmt, indent: int) -> None:
        prev_indent = self._expr_indent
        prev_line = self._current_pys_line
        self._expr_indent = indent
        self._current_pys_line = stmt.span.line if getattr(stmt, "span", None) else None
        try:
            self._stmt_inner(stmt, indent)
        finally:
            self._expr_indent = prev_indent
            self._current_pys_line = prev_line

    def _stmt_inner(self, stmt, indent: int) -> None:
        if isinstance(stmt, BlankStmt):
            self._append_raw("", pys_line=None)
        elif isinstance(stmt, CommentStmt):
            # Comments are always column-0 in legacy output (stripped lines).
            self._append_raw(stmt.text)
        elif isinstance(stmt, PrintStmt):
            self._emit(indent, f"print({self._expr(stmt.value)})")
        elif isinstance(stmt, AssignStmt):
            self._assign(stmt, indent)
        elif isinstance(stmt, ArrayDecl):
            self._array_decl(stmt, indent)
        elif isinstance(stmt, AugAssignStmt):
            name = self._lambda_rename.get(stmt.name, stmt.name)
            shared = stmt.name in self.shared_vars
            atomic = stmt.name in self.atomic_vars
            if shared or atomic:
                if stmt.op == "++":
                    self._emit(indent, f"{name}.iadd(1)")
                elif stmt.op == "--":
                    self._emit(indent, f"{name}.isub(1)")
                elif stmt.op == "+=":
                    self._emit(indent, f"{name}.iadd({self._expr(stmt.value)})")
                elif stmt.op == "-=":
                    self._emit(indent, f"{name}.isub({self._expr(stmt.value)})")
                elif atomic:
                    # Sem rejects *=/=%= on atomics; defensive fallback.
                    self._emit(
                        indent,
                        f"{name}.set({name}.get() {stmt.op[0]} {self._expr(stmt.value)})",
                    )
                else:
                    self._emit(
                        indent,
                        f"{name}.set({name}.value {stmt.op[0]} {self._expr(stmt.value)})",
                    )
            elif stmt.op == "++":
                self._emit(indent, f"{name} += 1")
            elif stmt.op == "--":
                self._emit(indent, f"{name} -= 1")
            else:
                self._emit(indent, f"{name} {stmt.op} {self._expr(stmt.value)}")
        elif isinstance(stmt, SharedDecl):
            self.needs_concurrency = True
            self.shared_vars.add(stmt.name)
            name = stmt.name
            if self._brace_depth > 0:
                name = self._bind_brace_local(stmt.name)
            self._emit(indent, f"{name} = _PysShared({self._expr(stmt.value)})")
        elif isinstance(stmt, AtomicDecl):
            self.needs_concurrency = True
            self.atomic_vars.add(stmt.name)
            name = stmt.name
            if self._brace_depth > 0:
                name = self._bind_brace_local(stmt.name)
            self._emit(indent, f"{name} = _PysAtomic({self._expr(stmt.value)})")
        elif isinstance(stmt, TasksBlock):
            self._tasks(stmt, indent)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value is None:
                self._emit(indent, "return")
            elif isinstance(stmt.value, InterpolatedString) and "this." in stmt.value.raw:
                # Legacy return path skips f-string rewrite; only this.→self.
                text = stmt.value.raw.replace("this.", "self.")
                self._emit(indent, f"return {text}")
            else:
                self._emit(indent, f"return {self._maybe_copy_struct(stmt.value)}")
        elif isinstance(stmt, PassStmt):
            self._emit(indent, "pass")
        elif isinstance(stmt, BreakStmt):
            self._emit(indent, "break")
        elif isinstance(stmt, ContinueStmt):
            self._emit(indent, "continue")
        elif isinstance(stmt, IfStmt):
            self._if(stmt, indent, first=True)
        elif isinstance(stmt, SwitchStmt):
            self._switch_stmt(stmt, indent)
        elif isinstance(stmt, WhileStmt):
            self._emit(indent, f"while {self._expr(stmt.cond)}:")
            self._block(stmt.body, indent + 1, brace_scope=True)
        elif isinstance(stmt, ForRangeStmt):
            start = self._expr(stmt.start)
            stop = self._expr(stmt.stop)
            self._scoped_loop_binder(
                stmt.var,
                iterable_code=f"{start}, {stop}",
                body=stmt.body,
                indent=indent,
                kind="range",
            )
        elif isinstance(stmt, ForEachStmt):
            iterable = self._expr(stmt.iterable)
            self._scoped_loop_binder(
                stmt.var,
                iterable_code=iterable,
                body=stmt.body,
                indent=indent,
                kind="foreach",
            )
        elif isinstance(stmt, RepeatStmt):
            self._emit(indent, f"for _ in range({self._expr(stmt.count)}):")
            self._block(stmt.body, indent + 1, brace_scope=True)
        elif isinstance(stmt, ImportStmt):
            self._import(stmt, indent)
        elif isinstance(stmt, FunctionDef):
            params = ", ".join(stmt.params)
            if stmt.return_type:
                self.fn_return_types[stmt.name] = stmt.return_type
            self._emit(indent, f"def {stmt.name}({params}):")
            prev_types = dict(self.var_types)
            prev_function = self._current_function
            self._current_function = stmt.name
            for i, pname in enumerate(stmt.params):
                if i < len(stmt.param_types) and stmt.param_types[i]:
                    self.var_types[pname] = stmt.param_types[i]
            if self._is_result_type(stmt.return_type):
                self.needs_result = True
                self._emit(indent + 1, "try:")
                self._block(stmt.body, indent + 2)
                self._emit(indent + 1, "except _PysPropagateSignal as _pys_signal:")
                self._emit(indent + 2, "return _pys_signal.result")
            else:
                self._block(stmt.body, indent + 1)
            self._current_function = prev_function
            self.var_types = prev_types
        elif isinstance(stmt, InterfaceDef):
            self._interface(stmt, indent)
        elif isinstance(stmt, TraitDef):
            # Traits are composition-only; methods are flattened into `uses` hosts.
            return
        elif isinstance(stmt, ClassDef):
            self._class(stmt, indent)
        elif isinstance(stmt, StructDef):
            self._struct(stmt, indent)
        elif isinstance(stmt, DataDef):
            self._data(stmt, indent)
        elif isinstance(stmt, EntityDef):
            self._entity(stmt, indent)
        elif isinstance(stmt, EnumDef):
            self._enum(stmt, indent)
        elif isinstance(stmt, ExprStmt):
            self._emit(indent, self._expr(stmt.expr))
        elif isinstance(stmt, Block):
            self._block(stmt, indent)
        else:
            raise TypeError(f"unsupported stmt {type(stmt).__name__}")

    def _tasks(self, stmt: TasksBlock, indent: int) -> None:
        self.needs_concurrency = True
        tg = f"_pys_tg_{stmt.group_id}"
        prev = self.tg_name
        self.tg_name = tg
        self._emit(indent, "if True:")
        inner = indent + 1
        self._emit(inner, f"{tg} = _PysTaskGroup()")
        for task in stmt.tasks:
            self._task_def(task, inner, tg)
        self._emit(inner, f"{tg}.run()")
        self.tg_name = prev

    def _task_def(self, task: TaskDef, indent: int, tg: str) -> None:
        params = ", ".join(task.params)
        self._emit(indent, f"def __pys_task_{task.name}({params}):")
        self._block(task.body, indent + 1)
        if task.is_template:
            self._emit(indent, f"{tg}.add_template({task.name!r}, __pys_task_{task.name})")
        else:
            self._emit(indent, f"{tg}.add_auto({task.name!r}, __pys_task_{task.name})")

    def _assign(self, stmt: AssignStmt, indent: int) -> None:
        kind = self._infer_kind(stmt.value)
        if stmt.declare_type == "string":
            kind = "string"
        elif stmt.declare_type in {
            "int",
            "float",
            "bool",
            "char",
            "byte",
            "nibble",
            "int16",
            "int32",
            "int64",
            "dword",
        }:
            kind = "number" if stmt.declare_type != "bool" else "number"
        base = stmt.name.split(".")[-1]
        self.var_kinds[base] = kind
        if (
            "." not in stmt.name
            and "[" not in stmt.name
            and self._brace_depth > 0
            and (stmt.declare_type or stmt.is_const or stmt.is_fix)
        ):
            self._bind_brace_local(stmt.name)
        expected = stmt.declare_type if stmt.declare_type and stmt.declare_type != "var" else None
        if expected is None and "." not in stmt.name and "[" not in stmt.name:
            expected = self.var_types.get(stmt.name)
        array_rhs = self._array_assign_value(stmt.name, stmt.value)
        if "." not in stmt.name and "[" not in stmt.name:
            self._track_binding_type(stmt.name, stmt.declare_type, stmt.value)
            value = (
                array_rhs
                if array_rhs is not None
                else self._maybe_copy_struct(stmt.value, expected_type=expected)
            )
        else:
            value = (
                array_rhs
                if array_rhs is not None
                else self._expr(stmt.value, expected_type=expected)
            )
        if "." not in stmt.name and "[" not in stmt.name and stmt.name in self.shared_vars:
            lhs = self._lambda_rename.get(stmt.name, stmt.name)
            self._emit(indent, f"{lhs}.set({value})")
            return
        if "." not in stmt.name and "[" not in stmt.name and stmt.name in self.atomic_vars:
            lhs = self._lambda_rename.get(stmt.name, stmt.name)
            self._emit(indent, f"{lhs}.set({value})")
            return
        if "[" in stmt.name:
            lhs = stmt.name
        else:
            lhs = (
                self._lambda_rename.get(stmt.name, stmt.name)
                if "." not in stmt.name
                else stmt.name
            )
        self._emit(indent, f"{lhs} = {value}")

    def _array_assign_value(self, lhs: str, value: Expr | None) -> str | None:
        """Emit nested array.array when assigning a literal/alloc into an array slot."""
        if value is None or not isinstance(value, (ArrayLiteral, BraceLiteral, ArrayAlloc)):
            return None
        meta = self._array_lvalue_remaining(lhs)
        if meta is None:
            return None
        elem_type, rem_rank = meta
        if rem_rank < 1:
            return None
        return self._array_value_py(elem_type, rem_rank, value)

    def _array_lvalue_remaining(self, lhs: str) -> tuple[str, int] | None:
        """For ``arr[i][j]``, return (elem_type, remaining_rank) using array_meta."""
        m = re.match(r"^([A-Za-z_]\w*)((?:\[[^\]]+\])+)$", lhs)
        if not m:
            return None
        root = m.group(1)
        meta = self.array_meta.get(root)
        if meta is None:
            return None
        elem_type, rank = meta
        depth = m.group(2).count("[")
        return elem_type, rank - depth

    @staticmethod
    def _base_type(type_name: str) -> str:
        return type_name.split("<", 1)[0] if type_name else ""

    def _is_result_type(self, type_name: str) -> bool:
        return self._base_type(type_name) == "result"

    def _is_struct_type(self, type_name: str) -> bool:
        return self._base_type(type_name) in self.struct_names

    def _track_binding_type(
        self, name: str, declare_type: str | None, value: Expr | None
    ) -> None:
        if declare_type and declare_type != "var":
            self.var_types[name] = declare_type
            return
        inferred = self._infer_structish_type(value)
        if inferred:
            self.var_types[name] = inferred

    def _infer_structish_type(self, expr: Expr | None) -> str | None:
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            if expr.callee.name in self.struct_names:
                return expr.callee.name
        if isinstance(expr, Identifier):
            return self.var_types.get(expr.name)
        if isinstance(expr, Member) and isinstance(expr.object, Identifier):
            ot = self._base_type(self.var_types.get(expr.object.name, ""))
            ft = self.struct_field_types.get(ot, {}).get(expr.name, "")
            return ft or None
        return None

    def _expr_is_struct_value(self, expr: Expr | None) -> bool:
        if expr is None:
            return False
        if isinstance(expr, KeywordArg):
            return self._expr_is_struct_value(expr.value)
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            if expr.callee.name in self.struct_names:
                return True
            return self._is_struct_type(self.fn_return_types.get(expr.callee.name, ""))
        if isinstance(expr, Identifier):
            return self._is_struct_type(self.var_types.get(expr.name, ""))
        if isinstance(expr, Member) and isinstance(expr.object, Identifier):
            ot = self._base_type(self.var_types.get(expr.object.name, ""))
            ft = self.struct_field_types.get(ot, {}).get(expr.name, "")
            return self._is_struct_type(ft)
        return False

    def _maybe_copy_struct(
        self, expr: Expr | None, *, expected_type: str | None = None
    ) -> str:
        if expr is None:
            return ""
        if isinstance(expr, KeywordArg):
            return (
                f"{expr.name}={self._maybe_copy_struct(expr.value, expected_type=expected_type)}"
            )
        code = self._expr(expr, expected_type=expected_type)
        if self._expr_is_struct_value(expr):
            self.needs_struct_copy = True
            return f"_pys_struct_copy({code})"
        return code

    def _array_decl(self, stmt: ArrayDecl, indent: int) -> None:
        self.needs_array = True
        name = stmt.name
        if self._brace_depth > 0:
            name = self._bind_brace_local(stmt.name)
        self.var_kinds[stmt.name] = "array"
        dims = list(getattr(stmt, "dims", None) or [])
        rank = len(dims) if dims else 1
        self.array_meta[stmt.name] = (stmt.elem_type, rank)
        self._emit(indent, f"{name} = {self._array_value_py(stmt.elem_type, rank, stmt.value)}")

    def _array_leaf_py(self, elem_type: str, elements: list[Expr]) -> str:
        parts: list[str] = []
        for e in elements:
            if isinstance(e, Literal) and e.kind == "bool":
                parts.append("1" if e.text == "true" else "0")
            else:
                parts.append(self._expr(e))
        inner = ", ".join(parts)
        if elem_type == "string":
            return f"[{inner}]"
        code = _ARRAY_TYPECODE.get(elem_type, "i")
        return f"array('{code}', [{inner}])"

    def _array_zero_leaf_py(self, elem_type: str, length: int) -> str:
        if elem_type == "string":
            return "[" + ", ".join('""' for _ in range(length)) + "]"
        if elem_type == "float":
            zeros = ", ".join("0.0" for _ in range(length))
        elif elem_type == "bool":
            zeros = ", ".join("0" for _ in range(length))
        elif elem_type == "char":
            zeros = ", ".join(repr("\0") for _ in range(length))
        else:
            zeros = ", ".join("0" for _ in range(length))
        code = _ARRAY_TYPECODE.get(elem_type, "i")
        return f"array('{code}', [{zeros}])"

    def _array_alloc_py(self, elem_type: str, dims: list[int | None]) -> str:
        if not dims:
            return "None"
        head, *tail = dims
        if not tail:
            if head is None:
                if elem_type == "string":
                    return "[]"
                code = _ARRAY_TYPECODE.get(elem_type, "i")
                self.needs_array = True
                return f"array('{code}', [])"
            self.needs_array = True
            return self._array_zero_leaf_py(elem_type, head)
        if head is None:
            return "[]"
        if all(d is None for d in tail):
            return f"[None] * {head}"
        inner = self._array_alloc_py(elem_type, tail)
        return f"[{inner} for _ in range({head})]"

    def _array_value_py(self, elem_type: str, rank: int, value: Expr | None) -> str:
        if isinstance(value, ArrayAlloc):
            self.needs_array = True
            return self._array_alloc_py(value.elem_type or elem_type, list(value.dims))
        if isinstance(value, (ArrayLiteral, BraceLiteral)):
            if rank <= 1:
                self.needs_array = True
                return self._array_leaf_py(elem_type, list(value.elements))
            parts = [
                self._array_value_py(elem_type, rank - 1, el) for el in value.elements
            ]
            self.needs_array = True
            return "[" + ", ".join(parts) + "]"
        if value is None:
            return "None"
        return self._expr(value)

    def _import(self, stmt: ImportStmt, indent: int) -> None:
        if self._import_resolver is not None:
            from .. import imports as imports_mod

            line = _pys_import_line(stmt)
            resolved = imports_mod.translate_import(self._import_resolver, line, 1)
            if resolved is not None:
                self._emit(indent, resolved)
                return
        if stmt.kind == "module":
            self._emit(indent, f"from {Path(stmt.module).stem} import *")
        elif stmt.kind == "as":
            self._emit(indent, f"import {stmt.module} as {stmt.alias}")
        elif stmt.kind == "all_from":
            self._emit(indent, f"from {Path(stmt.module).stem} import *")
        elif stmt.kind == "name_from":
            names = stmt.names or ([stmt.name] if stmt.name else [])
            self._emit(indent, f"from {Path(stmt.module).stem} import {', '.join(names)}")
        else:
            raise TypeError(stmt.kind)

    def _interface(self, stmt: InterfaceDef, indent: int) -> None:
        self.needs_abc = True
        self._emit(indent, f"class {stmt.name}(ABC):")
        if not stmt.methods:
            self._emit(indent + 1, "pass")
            return
        for m in stmt.methods:
            self._emit(indent + 1, "@abstractmethod")
            self._emit(indent + 1, f"def {m}(self):")
            self._emit(indent + 2, "pass")

    def _enum(self, stmt: EnumDef, indent: int) -> None:
        self.needs_enum = True
        has_values = all(m.value is not None for m in stmt.members)
        if has_values:
            kinds = {
                m.value.kind
                for m in stmt.members
                if isinstance(m.value, Literal)
            }
            if kinds == {"string"}:
                base = "enum.StrEnum"
            else:
                base = "enum.IntEnum"
        else:
            base = "enum.Enum"
        self._emit(indent, f"class {stmt.name}({base}):")
        for m in stmt.members:
            if m.value is None:
                self._emit(indent + 1, f"{m.name} = enum.auto()")
            else:
                self._emit(indent + 1, f"{m.name} = {self._expr(m.value)}")

    def _struct(self, stmt: StructDef, indent: int) -> None:
        self.needs_dataclass = True
        self.needs_struct_copy = True
        self.struct_names.add(stmt.name)
        self.struct_field_types[stmt.name] = {f.name: f.type_name for f in stmt.fields}
        all_fix = stmt.type_fix or (bool(stmt.fields) and all(f.is_fix for f in stmt.fields))
        # Empty struct: treat as immutable/hashable (vacuous all-fields-fix).
        if not stmt.fields:
            all_fix = True
        fix_fields = {f.name for f in stmt.fields if f.is_fix or stmt.type_fix}
        partial_fix = (not all_fix) and bool(fix_fields)
        if all_fix:
            self._emit(indent, "@dataclass(frozen=True)")
        else:
            self._emit(indent, "@dataclass")
        self._emit(indent, f"class {stmt.name}:")
        if not stmt.fields:
            self._emit(indent + 1, "pass")
            self._emit(indent + 1, "def _pys_copy(self):")
            self._emit(indent + 2, f"return {stmt.name}()")
            return
        for f in stmt.fields:
            if f.default is not None:
                self._emit(indent + 1, f"{f.name}: object = {self._expr(f.default)}")
            else:
                self._emit(indent + 1, f"{f.name}: object")
        if not all_fix:
            self._emit(indent + 1, "__hash__ = None")
        if partial_fix:
            names = ", ".join(repr(n) for n in sorted(fix_fields))
            self._emit(indent + 1, f"_pys_fix_fields = frozenset({{{names}}})")
            self._emit(indent + 1, "def __setattr__(self, name, value):")
            self._emit(
                indent + 2,
                "if name in type(self)._pys_fix_fields and name in self.__dict__:",
            )
            self._emit(
                indent + 3,
                "raise AttributeError(f\"Cannot assign to fix field {name!r}\")",
            )
            self._emit(indent + 2, "object.__setattr__(self, name, value)")
        self._emit(indent + 1, "def _pys_copy(self):")
        copy_args = ", ".join(
            f"{f.name}=_pys_struct_copy(self.{f.name})" for f in stmt.fields
        )
        self._emit(indent + 2, f"return {stmt.name}({copy_args})")

    def _data(self, stmt: DataDef, indent: int) -> None:
        """Immutable value object: frozen dataclass + struct-style copy helper."""
        self.needs_dataclass = True
        self.needs_struct_copy = True
        self.struct_names.add(stmt.name)
        self.struct_field_types[stmt.name] = {f.name: f.type_name for f in stmt.fields}
        self._emit(indent, "@dataclass(frozen=True)")
        self._emit(indent, f"class {stmt.name}:")
        if not stmt.fields:
            self._emit(indent + 1, "pass")
            self._emit(indent + 1, "def _pys_copy(self):")
            self._emit(indent + 2, f"return {stmt.name}()")
            return
        for f in stmt.fields:
            if f.default is not None:
                self._emit(indent + 1, f"{f.name}: object = {self._expr(f.default)}")
            else:
                self._emit(indent + 1, f"{f.name}: object")
        self._emit(indent + 1, "def _pys_copy(self):")
        copy_args = ", ".join(
            f"{f.name}=_pys_struct_copy(self.{f.name})" for f in stmt.fields
        )
        self._emit(indent + 2, f"return {stmt.name}({copy_args})")

    def _entity_identity_keys(self, stmt: EntityDef) -> list[str]:
        keys: list[str] = []
        if stmt.parent and stmt.parent in self.entity_defs:
            keys.extend(self._entity_identity_keys(self.entity_defs[stmt.parent]))
        keys.extend(stmt.identity)
        return keys

    def _entity_fix_fields(self, stmt: EntityDef) -> set[str]:
        fixes = {f.name for f in stmt.fields if f.is_fix}
        if stmt.parent and stmt.parent in self.entity_defs:
            fixes |= self._entity_fix_fields(self.entity_defs[stmt.parent])
        return fixes

    def _entity(self, stmt: EntityDef, indent: int) -> None:
        """Identity-keyed type: class + eq/hash/repr on identity fields."""
        if stmt.parent:
            self._emit(indent, f"class {stmt.name}({stmt.parent}):")
        else:
            self._emit(indent, f"class {stmt.name}:")
        if not stmt.fields and not stmt.methods:
            self._emit(indent + 1, "pass")
            return
        for f in stmt.fields:
            default = _default_value_for_type(f.type_name or "string")
            self._emit(indent + 1, f"{f.name} = {default}")
            self.var_kinds[f.name] = "string" if f.type_name == "string" else "number"
        local_fix = {f.name for f in stmt.fields if f.is_fix}
        # Re-emit setattr when this body adds fix fields (must include parent keys).
        if local_fix:
            all_fix = self._entity_fix_fields(stmt)
            names = ", ".join(repr(n) for n in sorted(all_fix))
            self._emit(indent + 1, f"_pys_fix_fields = frozenset({{{names}}})")
            self._emit(indent + 1, "def __setattr__(self, name, value):")
            self._emit(
                indent + 2,
                "if name in type(self)._pys_fix_fields and name in self.__dict__:",
            )
            self._emit(
                indent + 3,
                "raise AttributeError(f\"Cannot assign to fix field {name!r}\")",
            )
            self._emit(indent + 2, "object.__setattr__(self, name, value)")
        inject_super = bool(stmt.parent)
        first_method = True
        for i, m in enumerate(stmt.methods):
            if (not first_method or i > 0) and self.lines and self.lines[-1] != "":
                self._append_raw("", pys_line=None)
            first_method = False
            self._method(m, indent + 1, inject_super=inject_super and m.is_constructor)
        keys = self._entity_identity_keys(stmt)
        if keys:
            if not first_method and self.lines and self.lines[-1] != "":
                self._append_raw("", pys_line=None)
            key_tuple = ", ".join(f"self.{k}" for k in keys)
            other_tuple = ", ".join(f"other.{k}" for k in keys)
            self._emit(indent + 1, "def __eq__(self, other):")
            self._emit(indent + 2, f"if not isinstance(other, {stmt.name}):")
            self._emit(indent + 3, "return NotImplemented")
            self._emit(indent + 2, f"return ({key_tuple},) == ({other_tuple},)")
            self._emit(indent + 1, "def __hash__(self):")
            self._emit(indent + 2, f"return hash(({key_tuple},))")
            repr_parts = ", ".join(f"{k}={{self.{k}!r}}" for k in keys)
            self._emit(indent + 1, "def __repr__(self):")
            self._emit(
                indent + 2,
                f"return f\"{stmt.name}({repr_parts})\"",
            )

    def _class(self, stmt: ClassDef, indent: int) -> None:
        bases_list = list(stmt.bases)
        if stmt.abstract:
            self.needs_abc = True
            if "ABC" not in bases_list:
                bases_list.append("ABC")
        if bases_list:
            bases = ", ".join(bases_list)
            self._emit(indent, f"class {stmt.name}({bases}):")
        else:
            self._emit(indent, f"class {stmt.name}:")
        host_names = {m.name for m in stmt.methods if not m.is_constructor}
        # Trait methods to flatten: public name if host does not override;
        # always emit mangled `_Trait_method` when host overrides that name
        # so `Trait.method(this)` can disambiguate.
        flat_methods: list = []
        mangled_methods: list[tuple[str, object]] = []
        for tname in stmt.uses:
            trait = self.trait_defs.get(tname)
            if trait is None:
                continue
            for m in trait.methods:
                mangled = f"_{tname}_{m.name}"
                if m.name in host_names:
                    mangled_methods.append((mangled, m))
                else:
                    flat_methods.append(m)
                    # Still emit mangled twin when multiple traits could share
                    # the name after an override path; keep one public body.
        if not stmt.fields and not stmt.methods and not flat_methods and not mangled_methods:
            self._emit(indent + 1, "pass")
            return
        for f in stmt.fields:
            if f.default is not None:
                self._emit(indent + 1, f"{f.name} = {self._expr(f.default)}")
            else:
                default = _default_value_for_type(f.type_name or "string")
                self._emit(indent + 1, f"{f.name} = {default}")
            self.var_kinds[f.name] = "string" if f.type_name == "string" else "number"
        frozen = {f.name for f in stmt.fields if f.is_fix or f.is_const}
        if frozen:
            names = ", ".join(repr(n) for n in sorted(frozen))
            self._emit(indent + 1, f"_pys_fix_fields = frozenset({{{names}}})")
            self._emit(indent + 1, "def __setattr__(self, name, value):")
            self._emit(
                indent + 2,
                "if name in type(self)._pys_fix_fields and name in self.__dict__:",
            )
            self._emit(
                indent + 3,
                'raise AttributeError(f"fix field {name!r} cannot be reassigned")',
            )
            self._emit(indent + 2, "object.__setattr__(self, name, value)")
        # Subclass ctors get an implicit super().__init__() when the body never
        # calls super(...) or this(...). Interface-only classes are unchanged.
        inject_super = bool(stmt.parent)
        first_method = True
        for mangled, m in mangled_methods:
            if not first_method and self.lines and self.lines[-1] != "":
                self._append_raw("", pys_line=None)
            first_method = False
            self._method(m, indent + 1, inject_super=False, emit_name=mangled)
        for i, m in enumerate(stmt.methods):
            if (not first_method or i > 0) and self.lines and self.lines[-1] != "":
                self._append_raw("", pys_line=None)
            first_method = False
            self._method(m, indent + 1, inject_super=inject_super and m.is_constructor)
        for m in flat_methods:
            if not first_method and self.lines and self.lines[-1] != "":
                self._append_raw("", pys_line=None)
            first_method = False
            self._method(m, indent + 1, inject_super=False)

    def _method(
        self,
        m: MethodDef,
        indent: int,
        *,
        inject_super: bool = False,
        emit_name: str | None = None,
    ) -> None:
        name = emit_name or m.name
        if m.is_abstract:
            self.needs_abc = True
            self._emit(indent, "@abstractmethod")
            params = ", ".join(["self", *m.params])
            self._emit(indent, f"def {name}({params}):")
            self._emit(indent + 1, "pass")
            return
        if m.is_constructor:
            parts = ["self"]
            for i, pname in enumerate(m.params):
                ptype = m.param_types[i] if i < len(m.param_types) else ""
                default = _default_value_for_type(ptype) if ptype else None
                if default is not None and ptype:
                    parts.append(f"{pname}={default}")
                else:
                    parts.append(pname)
            self._emit(indent, f"def __init__({', '.join(parts)}):")
        else:
            params = ", ".join(["self", *m.params])
            self._emit(indent, f"def {name}({params}):")
            if m.return_type and m.return_type != "void" and emit_name is None:
                self.fn_return_types[m.name] = m.return_type
        need_super = inject_super and not _ctor_chains_to_parent(m.body)
        prev_types = dict(self.var_types)
        prev_function = self._current_function
        self._current_function = name
        for i, pname in enumerate(m.params):
            if i < len(m.param_types) and m.param_types[i]:
                self.var_types[pname] = m.param_types[i]
        if not m.is_constructor and self._is_result_type(m.return_type):
            self.needs_result = True
            self._emit(indent + 1, "try:")
            self._block(m.body, indent + 2)
            self._emit(indent + 1, "except _PysPropagateSignal as _pys_signal:")
            self._emit(indent + 2, "return _pys_signal.result")
        else:
            if need_super:
                self._emit(indent + 1, "super().__init__()")
                if m.body is None or not m.body.statements:
                    self._current_function = prev_function
                    self.var_types = prev_types
                    return
            self._block(m.body, indent + 1)
        self._current_function = prev_function
        self.var_types = prev_types

    def _if(self, stmt: IfStmt, indent: int, *, first: bool) -> None:
        cond = self._expr(stmt.cond)
        if stmt.negated:
            head = f"if not ({cond}):" if first else f"elif not ({cond}):"
        else:
            head = f"if {cond}:" if first else f"elif {cond}:"
        self._emit(indent, head)
        self._block(stmt.then_body, indent + 1, brace_scope=True)
        if stmt.else_body is None:
            return
        # else if chain: else_body is Block with single IfStmt
        if (
            isinstance(stmt.else_body, Block)
            and len(stmt.else_body.statements) == 1
            and isinstance(stmt.else_body.statements[0], IfStmt)
        ):
            self._if(stmt.else_body.statements[0], indent, first=False)
            return
        self._emit(indent, "else:")
        self._block(stmt.else_body, indent + 1, brace_scope=True)

    def _switch_label_cmp(self, subject: str, label: Expr) -> str:
        return f"{subject} == {self._expr(label)}"

    def _switch_labels_cond(self, subject: str, labels: list[Expr]) -> str:
        if not labels:
            return "True"
        parts = [self._switch_label_cmp(subject, lab) for lab in labels]
        if len(parts) == 1:
            return parts[0]
        return " or ".join(f"({p})" for p in parts)

    def _switch_stmt_groups(
        self, cases: list[SwitchCase]
    ) -> list[tuple[list[Expr] | None, Block | None]]:
        """Collapse fall-through chains into (labels|None for default, body) groups."""
        groups: list[tuple[list[Expr] | None, Block | None]] = []
        pending: list[Expr] = []
        for case in cases:
            if case.is_default:
                if pending:
                    # Fall-through into default: treat pending labels with default body.
                    groups.append((pending, case.body))
                    pending = []
                else:
                    groups.append((None, case.body))
                continue
            pending.extend(case.labels)
            if case.fallthrough:
                continue
            groups.append((pending, case.body))
            pending = []
        if pending:
            # Sem rejects trailing fall-through; keep defensive emit.
            groups.append((pending, Block(statements=[])))
        return groups

    def _switch_stmt(self, stmt: SwitchStmt, indent: int) -> None:
        if any(
            isinstance(label, ResultPattern)
            for case in stmt.cases
            for label in case.labels
        ):
            self._result_switch_stmt(stmt, indent)
            return
        subject = self._expr(stmt.subject)
        groups = self._switch_stmt_groups(stmt.cases)
        first = True
        for labels, body in groups:
            if labels is None:
                self._emit(indent, "else:")
                self._block(body, indent + 1, brace_scope=True)
                first = False
                continue
            cond = self._switch_labels_cond(subject, labels)
            head = f"if {cond}:" if first else f"elif {cond}:"
            self._emit(indent, head)
            self._block(body, indent + 1, brace_scope=True)
            first = False

    def _result_switch_case_body(
        self,
        case: SwitchCase,
        subject: str,
        indent: int,
    ) -> None:
        prev_rename = dict(self._lambda_rename)
        self._brace_depth += 1
        try:
            pattern = case.labels[0] if case.labels else None
            if isinstance(pattern, ResultPattern) and pattern.binding:
                bound = self._bind_brace_local(pattern.binding)
                self._emit(indent, f"{bound} = {subject}.value")
            if case.body is None or not case.body.statements:
                if not isinstance(pattern, ResultPattern) or not pattern.binding:
                    self._emit(indent, "pass")
            else:
                for child in case.body.statements:
                    self._stmt(child, indent)
        finally:
            self._brace_depth -= 1
            self._lambda_rename = prev_rename

    def _result_switch_stmt(self, stmt: SwitchStmt, indent: int) -> None:
        self.needs_result = True
        serial = self.result_switch_serial
        self.result_switch_serial += 1
        subject = f"_pys_result_{serial}"
        self._emit(indent, f"{subject} = {self._expr(stmt.subject)}")
        patterns = [case for case in stmt.cases if not case.is_default]
        default = next((case for case in stmt.cases if case.is_default), None)
        for index, case in enumerate(patterns):
            pattern = case.labels[0]
            assert isinstance(pattern, ResultPattern)
            head = "if" if index == 0 else "elif"
            self._emit(
                indent,
                f"{head} {subject}._pys_result_kind == {pattern.kind!r}:",
            )
            self._result_switch_case_body(case, subject, indent + 1)
        if default is not None:
            if patterns:
                self._emit(indent, "else:")
                self._result_switch_case_body(default, subject, indent + 1)
            else:
                self._result_switch_case_body(default, subject, indent)

    def _switch_expr(self, expr: SwitchExpr) -> str:
        if any(
            isinstance(label, ResultPattern)
            for case in expr.cases
            for label in case.labels
        ):
            return self._result_switch_expr(expr)
        subject = self._expr(expr.subject)
        # Build nested conditional from last arm to first for readability.
        arms: list[tuple[list[Expr] | None, Expr | None]] = []
        for case in expr.cases:
            if case.is_default:
                arms.append((None, case.value))
            else:
                arms.append((case.labels, case.value))
        if not arms:
            return "None"
        # Default arm (if any) is the innermost else; otherwise last case.
        result = "None"
        for labels, value in reversed(arms):
            val = self._expr(value)
            if labels is None:
                result = val
            else:
                cond = self._switch_labels_cond(subject, labels)
                result = f"({val} if {cond} else {result})"
        return result

    def _result_switch_expr(self, expr: SwitchExpr) -> str:
        self.needs_result = True
        serial = self.result_switch_serial
        self.result_switch_serial += 1
        name = f"_pys_result_switch_{serial}"
        arg = "_pys_result_value"
        indent = self._expr_indent
        self._emit(indent, f"def {name}({arg}):")
        patterns = [case for case in expr.cases if not case.is_default]
        default = next((case for case in expr.cases if case.is_default), None)
        for index, case in enumerate(patterns):
            pattern = case.labels[0]
            assert isinstance(pattern, ResultPattern)
            head = "if" if index == 0 else "elif"
            self._emit(
                indent + 1,
                f"{head} {arg}._pys_result_kind == {pattern.kind!r}:",
            )
            prev_rename = self._lambda_rename
            if pattern.binding:
                self._lambda_rename = {**prev_rename, pattern.binding: pattern.binding}
                self._emit(indent + 2, f"{pattern.binding} = {arg}.value")
            self._emit(indent + 2, f"return {self._expr(case.value)}")
            self._lambda_rename = prev_rename
        if default is not None:
            if patterns:
                self._emit(indent + 1, "else:")
                self._emit(indent + 2, f"return {self._expr(default.value)}")
            else:
                self._emit(indent + 1, f"return {self._expr(default.value)}")
        else:
            self._emit(indent + 1, "raise RuntimeError('invalid PYS result tag')")
        return f"{name}({self._expr(expr.subject)})"

    def _bind_brace_local(self, name: str) -> str:
        """Mangle a name declared inside `{ }` so it cannot leak in Python."""
        self._scope_serial += 1
        mangled = f"_pys_b{self._scope_serial}_{name}"
        self._lambda_rename = {**self._lambda_rename, name: mangled}
        self.debug_names[mangled] = name
        return mangled

    def _block(self, block: Block | None, indent: int, *, brace_scope: bool = False) -> None:
        if block is None or not block.statements:
            self._emit(indent, "pass")
            return
        prev_rename = None
        if brace_scope:
            prev_rename = dict(self._lambda_rename)
            self._brace_depth += 1
        try:
            for s in block.statements:
                self._stmt(s, indent)
        finally:
            if brace_scope:
                self._brace_depth -= 1
                self._lambda_rename = prev_rename or {}

    def _scoped_loop_binder(
        self,
        var: str,
        *,
        iterable_code: str,
        body: Block | None,
        indent: int,
        kind: str = "foreach",
    ) -> None:
        """Emit a for-loop whose binder exists only inside the loop body scope."""
        prev_rename = dict(self._lambda_rename)
        self._brace_depth += 1
        mangled = self._bind_brace_local(var)
        if kind == "range":
            self._emit(indent, f"for {mangled} in range({iterable_code}):")
        else:
            self._emit(indent, f"for {mangled} in {iterable_code}:")
        if body is None or not body.statements:
            self._emit(indent + 1, "pass")
        else:
            for s in body.statements:
                self._stmt(s, indent + 1)
        self._brace_depth -= 1
        self._lambda_rename = prev_rename

    # ---- expressions ----

    def _expr(self, expr: Expr | None, *, expected_type: str | None = None) -> str:
        if expr is None:
            return ""
        if isinstance(expr, Literal):
            return self._literal(expr)
        if isinstance(expr, InterpolatedString):
            text = _translate_string_literal(expr.raw)
            text = re.sub(r"\bthis\b", "self", text)
            if self._lambda_rename:
                for pys_name, emitted in sorted(
                    self._lambda_rename.items(), key=lambda kv: -len(kv[0])
                ):
                    text = re.sub(rf"\b{re.escape(pys_name)}\b", emitted, text)
            return text
        if isinstance(expr, Identifier):
            name = self._lambda_rename.get(expr.name, expr.name)
            if expr.name in self.shared_vars:
                return f"{name}.value"
            if expr.name in self.atomic_vars:
                return f"{name}.get()"
            return name
        if isinstance(expr, AwaitExpr):
            return self._await(expr)
        if isinstance(expr, UnaryOp):
            if expr.op == "not":
                inner = self._expr(expr.operand)
                if isinstance(expr.operand, (BinaryOp, UnaryOp)):
                    return f"not ({inner})"
                return f"not {inner}"
            return f"{expr.op}{self._expr(expr.operand)}"
        if isinstance(expr, BinaryOp):
            if expr.op == "+":
                return self._plus(expr)
            prec = _BINOP_PREC.get(expr.op, 0)
            left = self._expr(expr.left)
            right = self._expr(expr.right)
            if isinstance(expr.left, BinaryOp) and _BINOP_PREC.get(expr.left.op, 0) < prec:
                left = f"({left})"
            if isinstance(expr.right, BinaryOp) and _BINOP_PREC.get(expr.right.op, 0) <= prec:
                right = f"({right})"
            return f"{left} {expr.op} {right}"
        if isinstance(expr, ResultCtor):
            self.needs_result = True
            if expr.kind == "ok" and expr.value is None:
                return "_pys_ok()"
            return f"_pys_{expr.kind}({self._expr(expr.value)})"
        if isinstance(expr, PropagateExpr):
            self.needs_result = True
            span = expr.span
            file = str(self.source_path) if self.source_path is not None else "<memory>"
            line = span.line if span else 1
            return (
                f"_pys_propagate({self._expr(expr.operand)}, {file!r}, "
                f"{line}, {self._current_function!r})"
            )
        if isinstance(expr, Call):
            # Atomic synthesized accessors: avoid Identifier → .get() on the receiver.
            if (
                isinstance(expr.callee, Member)
                and isinstance(expr.callee.object, Identifier)
                and expr.callee.object.name in self.atomic_vars
                and expr.callee.name in {"get", "compareAndSet"}
            ):
                recv = self._lambda_rename.get(
                    expr.callee.object.name, expr.callee.object.name
                )
                args = ", ".join(self._call_arg(a) for a in expr.args)
                return f"{recv}.{expr.callee.name}({args})"
            # TraitName.method(this, …) → self._TraitName_method(…)
            if (
                isinstance(expr.callee, Member)
                and isinstance(expr.callee.object, Identifier)
                and expr.callee.object.name in self.trait_names
            ):
                mangled = f"_{expr.callee.object.name}_{expr.callee.name}"
                args = list(expr.args)
                if args and isinstance(args[0], Identifier) and args[0].name == "self":
                    rest = ", ".join(self._call_arg(a) for a in args[1:])
                    return f"self.{mangled}({rest})" if rest else f"self.{mangled}()"
                joined = ", ".join(self._call_arg(a) for a in args)
                return f"{mangled}({joined})"
            # array.loop(fn) → list(map(fn, array))
            if (
                isinstance(expr.callee, Member)
                and expr.callee.name == "loop"
                and len(expr.args) == 1
            ):
                return f"list(map({self._expr(expr.args[0])}, {self._expr(expr.callee.object)}))"
            # super(args) → super().__init__(args); super.method(args) already Member+Call
            if isinstance(expr.callee, Identifier) and expr.callee.name == "super":
                args = ", ".join(self._call_arg(a) for a in expr.args)
                return f"super().__init__({args})"
            args = ", ".join(self._call_arg(a) for a in expr.args)
            return f"{self._expr(expr.callee)}({args})"
        if isinstance(expr, KeywordArg):
            return f"{expr.name}={self._expr(expr.value)}"
        if isinstance(expr, Member):
            return f"{self._expr(expr.object)}.{expr.name}"
        if isinstance(expr, Index):
            return f"{self._expr(expr.object)}[{self._expr(expr.index)}]"
        if isinstance(expr, Slice):
            return self._slice(expr)
        if isinstance(expr, Cast):
            py = _CAST.get(expr.type_name, "")
            inner = self._expr(expr.expr)
            if py:
                return f"{py}({inner})"
            return inner
        if isinstance(expr, TupleLiteral):
            return self._tuple_literal_py(expr)
        if isinstance(expr, DictLiteral):
            return self._dict_literal_py(expr)
        if isinstance(expr, SetLiteral):
            return self._set_literal_py(expr)
        if isinstance(expr, BraceLiteral):
            return self._brace_literal_py(expr, expected_type=expected_type)
        if isinstance(expr, ArrayLiteral):
            return "[" + ", ".join(self._expr(e) for e in expr.elements) + "]"
        if isinstance(expr, ArrayAlloc):
            self.needs_array = True
            return self._array_alloc_py(expr.elem_type, list(expr.dims))
        if isinstance(expr, SwitchExpr):
            return self._switch_expr(expr)
        if isinstance(expr, LambdaExpr):
            return self._lambda(expr, expected_type=expected_type)
        raise TypeError(f"unsupported expr {type(expr).__name__}")

    def _tuple_literal_py(self, expr: TupleLiteral) -> str:
        if not expr.elements:
            return "()"
        parts = [self._expr(e) for e in expr.elements]
        if len(parts) == 1:
            return f"({parts[0]},)"
        return "(" + ", ".join(parts) + ")"

    def _dict_literal_py(self, expr: DictLiteral) -> str:
        if not expr.entries:
            return "{}"
        parts = [f"{self._expr(k)}: {self._expr(v)}" for k, v in expr.entries]
        return "{" + ", ".join(parts) + "}"

    def _set_literal_py(self, expr: SetLiteral) -> str:
        if not expr.elements:
            return "set()"
        return "{" + ", ".join(self._expr(e) for e in expr.elements) + "}"

    def _brace_literal_py(
        self, expr: BraceLiteral, *, expected_type: str | None
    ) -> str:
        base = self._base_type(expected_type or "")
        if base == "dict":
            if expr.elements:
                raise TypeError("unkeyed brace cannot emit as dict")
            return "{}"
        if base == "set":
            if not expr.elements:
                return "set()"
            return "{" + ", ".join(self._expr(e) for e in expr.elements) + "}"
        if base == "list":
            return "[" + ", ".join(self._expr(e) for e in expr.elements) + "]"
        # ArrayDecl uses _array_value_py; bare emit without type is a programming error.
        if not expr.elements:
            raise TypeError("ambiguous empty brace literal without expected type")
        return "[" + ", ".join(self._expr(e) for e in expr.elements) + "]"

    def _lambda_free_names(self, expr: LambdaExpr) -> list[str]:
        params = set(expr.params)
        used: set[str] = set()

        def walk_expr(e: Expr | None, *, as_callee: bool = False) -> None:
            if e is None:
                return
            if isinstance(e, Identifier):
                if as_callee:
                    return
                if e.name in params:
                    return
                if e.name in {
                    "true",
                    "false",
                    "null",
                    "self",
                    "this",
                    "print",
                    "super",
                }:
                    return
                used.add(e.name)
                return
            if isinstance(e, Call):
                walk_expr(e.callee, as_callee=isinstance(e.callee, Identifier))
                if not isinstance(e.callee, Identifier):
                    walk_expr(e.callee)
                for a in e.args:
                    walk_expr(a)
                return
            if isinstance(e, KeywordArg):
                walk_expr(e.value)
                return
            if isinstance(e, LambdaExpr):
                # Nested lambda: outer free still free if not nested param.
                for name in self._lambda_free_names(e):
                    if name not in params:
                        used.add(name)
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
                child = getattr(e, attr, None)
                if isinstance(child, Expr):
                    walk_expr(child)
            elems = getattr(e, "elements", None)
            if isinstance(elems, list):
                for el in elems:
                    if isinstance(el, Expr):
                        walk_expr(el)
            entries = getattr(e, "entries", None)
            if isinstance(entries, list):
                for pair in entries:
                    if isinstance(pair, tuple) and len(pair) == 2:
                        walk_expr(pair[0])
                        walk_expr(pair[1])
            if isinstance(e, SwitchExpr):
                walk_expr(e.subject)
                for case in e.cases:
                    walk_expr(case.value)

        def walk_stmt(s) -> None:
            if isinstance(s, (AssignStmt, AugAssignStmt)):
                if isinstance(s, AssignStmt) and (
                    s.declare_type or s.is_const or s.is_fix
                ):
                    params.add(s.name)
                elif "." not in s.name and s.name not in params:
                    # Outer capture mutated inside the lambda (shared/atomic).
                    used.add(s.name)
                walk_expr(s.value)
            elif isinstance(s, (PrintStmt, ReturnStmt)):
                walk_expr(s.value)
            elif isinstance(s, ExprStmt):
                walk_expr(s.expr)
            elif isinstance(s, IfStmt):
                walk_expr(s.cond)
                if s.then_body:
                    for st in s.then_body.statements:
                        walk_stmt(st)
                if s.else_body:
                    for st in s.else_body.statements:
                        walk_stmt(st)
            elif isinstance(s, Block):
                for st in s.statements:
                    walk_stmt(st)
            elif isinstance(s, (WhileStmt, ForRangeStmt, ForEachStmt, RepeatStmt)):
                if isinstance(s, WhileStmt):
                    walk_expr(s.cond)
                if isinstance(s, ForEachStmt):
                    walk_expr(s.iterable)
                    params.add(s.var)
                if isinstance(s, ForRangeStmt):
                    params.add(s.var)
                if s.body:
                    for st in s.body.statements:
                        walk_stmt(st)

        if isinstance(expr.body, Block):
            for st in expr.body.statements:
                walk_stmt(st)
        else:
            walk_expr(expr.body)
        return sorted(used)

    @staticmethod
    def _lambda_return_type(type_name: str | None) -> str:
        text = (type_name or "").strip()
        if not text.startswith("lambda<") or not text.endswith(">"):
            return ""
        inner = text[len("lambda<") : -1]
        depth = 0
        last_comma = -1
        for index, char in enumerate(inner):
            if char == "<":
                depth += 1
            elif char == ">":
                depth -= 1
            elif char == "," and depth == 0:
                last_comma = index
        return inner[last_comma + 1 :].strip()

    def _lambda(
        self, expr: LambdaExpr, *, expected_type: str | None = None
    ) -> str:
        name = f"_pys_lam_{self.lambda_serial}"
        self.lambda_serial += 1
        frees = self._lambda_free_names(expr)
        rename = {f: f"_c_{f}" for f in frees}
        for free, emitted in rename.items():
            self.debug_names[emitted] = free
        parts = list(expr.params)
        for f in frees:
            # Default must read the *current* outer binding (e.g. mangled loop binder).
            outer = self._lambda_rename.get(f, f)
            parts.append(f"{rename[f]}={outer}")
        self._emit(self._expr_indent, f"def {name}({', '.join(parts)}):")
        prev_rename = self._lambda_rename
        prev_function = self._current_function
        self._current_function = name
        self._lambda_rename = {**prev_rename, **rename}
        body_indent = self._expr_indent + 1
        result_return = self._lambda_return_type(expected_type)
        if self._is_result_type(result_return):
            self.needs_result = True
            self._emit(body_indent, "try:")
            inner_indent = body_indent + 1
            if isinstance(expr.body, Block):
                if not expr.body.statements:
                    self._emit(inner_indent, "pass")
                else:
                    for st in expr.body.statements:
                        self._stmt(st, inner_indent)
            else:
                self._emit(inner_indent, f"return {self._expr(expr.body)}")
            self._emit(body_indent, "except _PysPropagateSignal as _pys_signal:")
            self._emit(body_indent + 1, "return _pys_signal.result")
        else:
            if isinstance(expr.body, Block):
                if not expr.body.statements:
                    self._emit(body_indent, "pass")
                else:
                    for st in expr.body.statements:
                        self._stmt(st, body_indent)
            else:
                self._emit(body_indent, f"return {self._expr(expr.body)}")
        self._current_function = prev_function
        self._lambda_rename = prev_rename
        return name

    def _call_arg(self, arg: Expr) -> str:
        return self._maybe_copy_struct(arg)

    def _await(self, expr: AwaitExpr) -> str:
        tg = self.tg_name or "_pys_tg_0"
        target = expr.target
        if isinstance(target, Call) and isinstance(target.callee, Identifier):
            args = ", ".join(self._expr(a) for a in target.args)
            if args:
                return f"_pys_await({tg}.call({target.callee.name!r}, {args}))"
            return f"_pys_await({tg}.call({target.callee.name!r}))"
        if isinstance(target, Identifier):
            # Zero-arg named task → futures; template without call unlikely here.
            return f"_pys_await({tg}.futures[{target.name!r}])"
        return f"_pys_await({self._expr(target)})"

    def _literal(self, lit: Literal) -> str:
        if lit.kind == "bool":
            return "True" if lit.text == "true" else "False"
        if lit.kind == "null":
            return "None"
        return lit.text

    def _infer_kind(self, expr: Expr | None) -> str:
        if expr is None:
            return "number"
        if isinstance(expr, Literal):
            if expr.kind == "string":
                return "string"
            if expr.kind == "char":
                return "string"
            return "number"
        if isinstance(expr, InterpolatedString):
            return "string"
        if isinstance(expr, Identifier):
            return self.var_kinds.get(expr.name, "number")
        if isinstance(expr, BinaryOp) and expr.op == "+":
            if self._infer_kind(expr.left) == "string" or self._infer_kind(expr.right) == "string":
                return "string"
            return "number"
        if isinstance(expr, Cast) and expr.type_name == "string":
            return "string"
        if isinstance(expr, Member):
            return self.var_kinds.get(expr.name, "number")
        return "number"

    def _plus(self, expr: BinaryOp) -> str:
        """Flatten + chain left-associatively with str() like language_spec."""
        parts = self._flatten_plus(expr)
        if len(parts) <= 1:
            return self._expr(parts[0]) if parts else ""

        result = self._expr(parts[0])
        mode = "string" if self._infer_kind(parts[0]) == "string" else "number"
        for part in parts[1:]:
            kind = self._infer_kind(part)
            translated = self._expr(part)
            if mode == "number" and kind != "string":
                result = f"{result} + {translated}"
                continue
            if mode == "number" and kind == "string":
                result = f"str({result}) + {translated}"
                mode = "string"
                continue
            if kind == "string":
                result = f"{result} + {translated}"
            else:
                result = f"{result} + str({translated})"
            mode = "string"
        return result

    def _flatten_plus(self, expr: Expr) -> list[Expr]:
        if isinstance(expr, BinaryOp) and expr.op == "+":
            return self._flatten_plus(expr.left) + self._flatten_plus(expr.right)  # type: ignore[arg-type]
        return [expr]

    def _slice(self, expr: Slice) -> str:
        # Inclusive stop → (stop) + 1 to match legacy
        obj = self._expr(expr.object)
        start = self._expr(expr.start) if expr.start is not None else ""
        if expr.stop is not None:
            stop = f"({self._expr(expr.stop)}) + 1"
        else:
            stop = ""
        if expr.step is not None:
            return f"{obj}[{start}:{stop}:{self._expr(expr.step)}]"
        return f"{obj}[{start}:{stop}]"
