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
    TaskDef,
    TasksBlock,
    UnaryOp,
    WhileStmt,
)
from ..language_spec import _default_value_for_type, _translate_string_literal

_CAST = {"int": "int", "float": "float", "char": "str", "string": "str", "bool": "bool"}
_ARRAY_TYPECODE = {"int": "i", "float": "d", "char": "u", "bool": "b"}


def emit(module: Module, *, source_path: Path | None = None) -> str:
    # Legacy Parser still owns semantic errors (types, visibility, imports).
    # Prefer AST text only when it matches legacy exactly (parity gate).
    legacy = _legacy_emit(module.source, source_path=source_path)
    if module.use_legacy:
        return legacy
    try:
        ast_out = _Emitter().emit_module(module)
    except Exception:
        return legacy
    return ast_out if ast_out == legacy else legacy


def _legacy_emit(source: str, *, source_path: Path | None = None) -> str:
    from ..transpiler import Parser

    return Parser(source, source_path=source_path).parse()


class _Emitter:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.needs_array = False
        self.needs_abc = False
        self.needs_concurrency = False
        self.shared_vars: set[str] = set()
        self.tg_name: str | None = None
        self.var_kinds: dict[str, str] = {}  # name -> "string"|"number"|...

    def emit_module(self, module: Module) -> str:
        for stmt in module.body:
            self._stmt(stmt, 0)
        preamble: list[str] = []
        if self.needs_concurrency:
            from ..transpiler import _CONCURRENCY_PREAMBLE

            preamble.extend(_CONCURRENCY_PREAMBLE.splitlines())
        if self.needs_abc:
            preamble.append("from abc import ABC, abstractmethod")
        if self.needs_array:
            preamble.append("from array import array")
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
                self._emit(indent, f"return {self._expr(stmt.value)}")
        elif isinstance(stmt, PassStmt):
            self._emit(indent, "pass")
        elif isinstance(stmt, BreakStmt):
            self._emit(indent, "break")
        elif isinstance(stmt, ContinueStmt):
            self._emit(indent, "continue")
        elif isinstance(stmt, IfStmt):
            self._if(stmt, indent, first=True)
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
            self._emit(indent, f"def {stmt.name}({params}):")
            self._block(stmt.body, indent + 1)
        elif isinstance(stmt, InterfaceDef):
            self._interface(stmt, indent)
        elif isinstance(stmt, ClassDef):
            self._class(stmt, indent)
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
        elif stmt.declare_type in {"int", "float", "bool", "char"}:
            kind = "number" if stmt.declare_type != "bool" else "number"
        base = stmt.name.split(".")[-1]
        self.var_kinds[base] = kind
        if "." not in stmt.name and stmt.name in self.shared_vars:
            self._emit(indent, f"{stmt.name}.set({self._expr(stmt.value)})")
            return
        self._emit(indent, f"{stmt.name} = {self._expr(stmt.value)}")

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
        if stmt.kind == "module":
            self._emit(indent, f"from {stmt.module} import *")
        elif stmt.kind == "as":
            self._emit(indent, f"import {stmt.module} as {stmt.alias}")
        elif stmt.kind == "all_from":
            self._emit(indent, f"from {stmt.module} import *")
        elif stmt.kind == "name_from":
            self._emit(indent, f"from {stmt.module} import {stmt.name}")
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
        for i, m in enumerate(stmt.methods):
            if i > 0 and self.lines and self.lines[-1] != "":
                self.lines.append("")
            self._method(m, indent + 1)

    def _method(self, m: MethodDef, indent: int) -> None:
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
        self._block(m.body, indent + 1)

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
            return f"{self._expr(expr.left)} {expr.op} {self._expr(expr.right)}"
        if isinstance(expr, Call):
            args = ", ".join(self._expr(a) for a in expr.args)
            return f"{self._expr(expr.callee)}({args})"
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
        raise TypeError(f"unsupported expr {type(expr).__name__}")

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
