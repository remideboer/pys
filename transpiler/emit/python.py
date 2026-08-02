"""Python emitter for PYS AST."""
from __future__ import annotations

from pathlib import Path

import re

from ..ast_nodes import (
    ArrayDecl,
    ArrayLiteral,
    AssignStmt,
    AugAssignStmt,
    AwaitExpr,
    BinaryOp,
    BlankStmt,
    Block,
    BreakStmt,
    Call,
    Cast,
    ClassDef,
    CommentStmt,
    ContinueStmt,
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
    Literal,
    Member,
    MethodDef,
    Module,
    PassStmt,
    PrintStmt,
    RepeatStmt,
    ReturnStmt,
    SharedDecl,
    Slice,
    EnumDef,
    StructDef,
    SwitchCase,
    SwitchExpr,
    SwitchStmt,
    TaskDef,
    TasksBlock,
    UnaryOp,
    WhileStmt,
)

_STRUCT_COPY_HELPER = '''def _pys_struct_copy(value):
    copy = getattr(value, "_pys_copy", None)
    return copy() if callable(copy) else value
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
    ast_out = _Emitter(
        source=module.source,
        source_path=source_path,
    ).emit_module(module)
    from .overloads import rewrite_overloaded_methods

    return rewrite_overloaded_methods(ast_out)


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
    def __init__(self, *, source: str = "", source_path: Path | None = None) -> None:
        self.source_path = source_path
        self.lines: list[str] = []
        self.needs_array = False
        self.needs_abc = False
        self.needs_concurrency = False
        self.needs_dataclass = False
        self.needs_struct_copy = False
        self.needs_enum = False
        self.shared_vars: set[str] = set()
        self.tg_name: str | None = None
        self.var_kinds: dict[str, str] = {}  # name -> "string"|"number"|...
        self.var_types: dict[str, str] = {}  # name -> PYS type (for struct copy)
        self.fn_return_types: dict[str, str] = {}
        self.struct_names: set[str] = set()
        self.struct_field_types: dict[str, dict[str, str]] = {}
        self._import_resolver = None
        if source_path is not None:
            from .. import imports as imports_mod

            self._import_resolver = imports_mod.make_resolver(source, source_path)

    def emit_module(self, module: Module) -> str:
        self.struct_names = {
            s.name for s in module.body if isinstance(s, StructDef)
        }
        self.struct_field_types = {
            s.name: {f.name: f.type_name for f in s.fields}
            for s in module.body
            if isinstance(s, StructDef)
        }
        self.fn_return_types = {
            s.name: s.return_type
            for s in module.body
            if isinstance(s, FunctionDef) and s.return_type
        }
        if self._import_resolver is not None:
            self.struct_names |= set(getattr(self._import_resolver, "structs", set()))
            for name, ftypes in getattr(self._import_resolver, "struct_field_types", {}).items():
                self.struct_field_types.setdefault(name, dict(ftypes))
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
        out = preamble + self.lines
        return "\n".join(out) + ("\n" if out else "")

    def _emit(self, indent: int, text: str) -> None:
        self.lines.append(("    " * indent) + text)

    def _stmt(self, stmt, indent: int) -> None:
        if isinstance(stmt, BlankStmt):
            self.lines.append("")
        elif isinstance(stmt, CommentStmt):
            # Comments are always column-0 in legacy output (stripped lines).
            self.lines.append(stmt.text)
        elif isinstance(stmt, PrintStmt):
            self._emit(indent, f"print({self._expr(stmt.value)})")
        elif isinstance(stmt, AssignStmt):
            self._assign(stmt, indent)
        elif isinstance(stmt, ArrayDecl):
            self._array_decl(stmt, indent)
        elif isinstance(stmt, AugAssignStmt):
            if stmt.name in self.shared_vars:
                if stmt.op == "++":
                    self._emit(indent, f"{stmt.name}.iadd(1)")
                elif stmt.op == "--":
                    self._emit(indent, f"{stmt.name}.isub(1)")
                elif stmt.op == "+=":
                    self._emit(indent, f"{stmt.name}.iadd({self._expr(stmt.value)})")
                elif stmt.op == "-=":
                    self._emit(indent, f"{stmt.name}.isub({self._expr(stmt.value)})")
                else:
                    self._emit(
                        indent,
                        f"{stmt.name}.set({stmt.name}.value {stmt.op[0]} {self._expr(stmt.value)})",
                    )
            elif stmt.op == "++":
                self._emit(indent, f"{stmt.name} += 1")
            elif stmt.op == "--":
                self._emit(indent, f"{stmt.name} -= 1")
            else:
                self._emit(indent, f"{stmt.name} {stmt.op} {self._expr(stmt.value)}")
        elif isinstance(stmt, SharedDecl):
            self.needs_concurrency = True
            self.shared_vars.add(stmt.name)
            self._emit(indent, f"{stmt.name} = _PysShared({self._expr(stmt.value)})")
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
            self._block(stmt.body, indent + 1)
        elif isinstance(stmt, ForRangeStmt):
            self._emit(
                indent,
                f"for {stmt.var} in range({self._expr(stmt.start)}, {self._expr(stmt.stop)}):",
            )
            self._block(stmt.body, indent + 1)
        elif isinstance(stmt, ForEachStmt):
            self._emit(indent, f"for {stmt.var} in {self._expr(stmt.iterable)}:")
            self._block(stmt.body, indent + 1)
        elif isinstance(stmt, RepeatStmt):
            self._emit(indent, f"for _ in range({self._expr(stmt.count)}):")
            self._block(stmt.body, indent + 1)
        elif isinstance(stmt, ImportStmt):
            self._import(stmt, indent)
        elif isinstance(stmt, FunctionDef):
            params = ", ".join(stmt.params)
            if stmt.return_type:
                self.fn_return_types[stmt.name] = stmt.return_type
            self._emit(indent, f"def {stmt.name}({params}):")
            prev_types = dict(self.var_types)
            for i, pname in enumerate(stmt.params):
                if i < len(stmt.param_types) and stmt.param_types[i]:
                    self.var_types[pname] = stmt.param_types[i]
            self._block(stmt.body, indent + 1)
            self.var_types = prev_types
        elif isinstance(stmt, InterfaceDef):
            self._interface(stmt, indent)
        elif isinstance(stmt, ClassDef):
            self._class(stmt, indent)
        elif isinstance(stmt, StructDef):
            self._struct(stmt, indent)
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
        if "." not in stmt.name:
            self._track_binding_type(stmt.name, stmt.declare_type, stmt.value)
            value = self._maybe_copy_struct(stmt.value)
        else:
            value = self._expr(stmt.value)
        if "." not in stmt.name and stmt.name in self.shared_vars:
            self._emit(indent, f"{stmt.name}.set({value})")
            return
        self._emit(indent, f"{stmt.name} = {value}")

    @staticmethod
    def _base_type(type_name: str) -> str:
        return type_name.split("<", 1)[0] if type_name else ""

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

    def _maybe_copy_struct(self, expr: Expr | None) -> str:
        if expr is None:
            return ""
        if isinstance(expr, KeywordArg):
            return (
                f"{expr.name}={self._maybe_copy_struct(expr.value)}"
            )
        code = self._expr(expr)
        if self._expr_is_struct_value(expr):
            self.needs_struct_copy = True
            return f"_pys_struct_copy({code})"
        return code

    def _array_decl(self, stmt: ArrayDecl, indent: int) -> None:
        self.needs_array = True
        self.var_kinds[stmt.name] = "array"
        elems = stmt.value
        if isinstance(elems, ArrayLiteral):
            parts: list[str] = []
            for e in elems.elements:
                if isinstance(e, Literal) and e.kind == "bool":
                    parts.append("1" if e.text == "true" else "0")
                else:
                    parts.append(self._expr(e))
            inner = ", ".join(parts)
            code = _ARRAY_TYPECODE.get(stmt.elem_type, "i")
            if stmt.elem_type == "string":
                self._emit(indent, f"{stmt.name} = [{inner}]")
            else:
                self._emit(indent, f"{stmt.name} = array('{code}', [{inner}])")
        else:
            self._emit(indent, f"{stmt.name} = {self._expr(stmt.value)}")

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

    def _class(self, stmt: ClassDef, indent: int) -> None:
        if stmt.bases:
            bases = ", ".join(stmt.bases)
            self._emit(indent, f"class {stmt.name}({bases}):")
        else:
            self._emit(indent, f"class {stmt.name}:")
        if not stmt.fields and not stmt.methods:
            self._emit(indent + 1, "pass")
            return
        for f in stmt.fields:
            default = _default_value_for_type(f.type_name or "string")
            self._emit(indent + 1, f"{f.name} = {default}")
            self.var_kinds[f.name] = "string" if f.type_name == "string" else "number"
        # Subclass ctors get an implicit super().__init__() when the body never
        # calls super(...) or this(...). Interface-only classes are unchanged.
        inject_super = bool(stmt.parent)
        for i, m in enumerate(stmt.methods):
            if i > 0 and self.lines and self.lines[-1] != "":
                self.lines.append("")
            self._method(m, indent + 1, inject_super=inject_super and m.is_constructor)

    def _method(self, m: MethodDef, indent: int, *, inject_super: bool = False) -> None:
        if m.is_constructor:
            parts = ["self"]
            for i, name in enumerate(m.params):
                ptype = m.param_types[i] if i < len(m.param_types) else ""
                default = _default_value_for_type(ptype) if ptype else None
                if default is not None and ptype:
                    parts.append(f"{name}={default}")
                else:
                    parts.append(name)
            self._emit(indent, f"def __init__({', '.join(parts)}):")
        else:
            params = ", ".join(["self", *m.params])
            self._emit(indent, f"def {m.name}({params}):")
            if m.return_type:
                self.fn_return_types[m.name] = m.return_type
        need_super = inject_super and not _ctor_chains_to_parent(m.body)
        prev_types = dict(self.var_types)
        for i, pname in enumerate(m.params):
            if i < len(m.param_types) and m.param_types[i]:
                self.var_types[pname] = m.param_types[i]
        if need_super:
            self._emit(indent + 1, "super().__init__()")
            if m.body is None or not m.body.statements:
                self.var_types = prev_types
                return
        self._block(m.body, indent + 1)
        self.var_types = prev_types

    def _if(self, stmt: IfStmt, indent: int, *, first: bool) -> None:
        cond = self._expr(stmt.cond)
        if stmt.negated:
            head = f"if not ({cond}):" if first else f"elif not ({cond}):"
        else:
            head = f"if {cond}:" if first else f"elif {cond}:"
        self._emit(indent, head)
        self._block(stmt.then_body, indent + 1)
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
        self._block(stmt.else_body, indent + 1)

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
        subject = self._expr(stmt.subject)
        groups = self._switch_stmt_groups(stmt.cases)
        first = True
        for labels, body in groups:
            if labels is None:
                self._emit(indent, "else:")
                self._block(body, indent + 1)
                first = False
                continue
            cond = self._switch_labels_cond(subject, labels)
            head = f"if {cond}:" if first else f"elif {cond}:"
            self._emit(indent, head)
            self._block(body, indent + 1)
            first = False

    def _switch_expr(self, expr: SwitchExpr) -> str:
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

    def _block(self, block: Block | None, indent: int) -> None:
        if block is None or not block.statements:
            self._emit(indent, "pass")
            return
        for s in block.statements:
            self._stmt(s, indent)

    # ---- expressions ----

    def _expr(self, expr: Expr | None) -> str:
        if expr is None:
            return ""
        if isinstance(expr, Literal):
            return self._literal(expr)
        if isinstance(expr, InterpolatedString):
            text = _translate_string_literal(expr.raw)
            return re.sub(r"\bthis\b", "self", text)
        if isinstance(expr, Identifier):
            if expr.name in self.shared_vars:
                return f"{expr.name}.value"
            return expr.name
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
        if isinstance(expr, Call):
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
        if isinstance(expr, ArrayLiteral):
            return "[" + ", ".join(self._expr(e) for e in expr.elements) + "]"
        if isinstance(expr, SwitchExpr):
            return self._switch_expr(expr)
        raise TypeError(f"unsupported expr {type(expr).__name__}")

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
