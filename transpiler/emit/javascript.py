"""JavaScript (Node/ESM) emitter for PYS AST.

Teaching-core parity with the Python backend: control flow, OO, collections,
switch/enum/entity/data/struct, result, lambdas, shared/atomic/tasks/await
(cooperative), and trait `uses` flattening. Fail-closed: third-party Python
packages (use ``pys.toml`` ``[dependencies.npm]`` + central npm for JS libraries) and library
decorators (no silent drop).
"""
from __future__ import annotations

import re
from pathlib import Path

from ..ast_nodes import (
    ArrayAlloc,
    ArrayDecl,
    ArrayLiteral,
    AssignStmt,
    AtomicDecl,
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
    EnumDef,
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
    SetLiteral,
    SharedDecl,
    Slice,
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
from ..language_spec import _translate_string_literal

from .js_packages import (
    JS_DEFAULT_EXPORT_PACKAGES as _JS_DEFAULT_EXPORT_PACKAGES,
    JS_PACKAGE_MAP as _JS_PACKAGE_MAP,
)
from .js_runtime import JS_CONCURRENCY_PREAMBLE, JS_VALUE_HELPERS


class JsEmitError(ValueError):
    """Raised when the JS emitter cannot lower a construct."""


def emit(module: Module, *, source_path: Path | None = None) -> str:
    text, _maps, _names = emit_with_map(module, source_path=source_path)
    return text


def emit_with_map(
    module: Module,
    *,
    source_path: Path | None = None,
    is_entrypoint: bool = False,
) -> tuple[str, list[dict[str, int]], dict[str, str]]:
    """Emit JavaScript, a statement-level line map, and debug display names.

    Map entries use ``{"js": int, "pys": int}`` (1-based). ``names`` maps
    emitted locals → PYS display names.
    """
    emitter = _JsEmitter(source_path=source_path, is_entrypoint=is_entrypoint)
    text, origins = emitter.emit_module_with_origins(module)
    line_map: list[dict[str, int]] = []
    for i, orig in enumerate(origins):
        if orig is not None:
            line_map.append({"js": i + 1, "pys": orig})
    return text, line_map, dict(emitter.debug_names)


class _JsEmitter:
    def __init__(
        self,
        *,
        source_path: Path | None = None,
        is_entrypoint: bool = False,
    ) -> None:
        self.source_path = source_path
        self.is_entrypoint = is_entrypoint
        self.lines: list[str] = []
        self.origins: list[int | None] = []
        self.debug_names: dict[str, str] = {}
        self.class_names: set[str] = set()
        self.data_names: set[str] = set()
        self.struct_names: set[str] = set()
        self.entity_names: set[str] = set()
        self.entity_defs: dict[str, EntityDef] = {}
        self.enum_names: set[str] = set()
        self.trait_defs: dict[str, TraitDef] = {}
        self.var_kinds: dict[str, str] = {}
        self.var_types: dict[str, str] = {}
        self.struct_field_types: dict[str, dict[str, str]] = {}
        self.shared_vars: set[str] = set()
        self.atomic_vars: set[str] = set()
        self.tg_name: str | None = None
        self._trait_requires_remap: dict[str, str] = {}
        self._current_function: str = "<module>"
        self._repeat_serial: int = 0
        self._result_switch_serial: int = 0

    def emit_module_with_origins(self, module: Module) -> tuple[str, list[int | None]]:
        self.lines = []
        self.origins = []
        for stmt in module.body:
            if isinstance(stmt, (ClassDef, DataDef, StructDef, EntityDef)):
                self.class_names.add(stmt.name)
                if isinstance(stmt, DataDef):
                    self.data_names.add(stmt.name)
                    self.struct_names.add(stmt.name)
                if isinstance(stmt, StructDef):
                    self.struct_names.add(stmt.name)
                if isinstance(stmt, EntityDef):
                    self.entity_names.add(stmt.name)
                    self.entity_defs[stmt.name] = stmt
            if isinstance(stmt, EnumDef):
                self.enum_names.add(stmt.name)
            if isinstance(stmt, TraitDef):
                self.trait_defs[stmt.name] = stmt
        for line in JS_RUNTIME_PREAMBLE.strip("\n").splitlines():
            self._append_raw(line, pys_line=None)
        self._append_raw("", pys_line=None)
        for stmt in module.body:
            self._stmt(stmt, 0)
        text = "\n".join(self.lines)
        if text and not text.endswith("\n"):
            text += "\n"
        return text, list(self.origins)

    def _pys_line(self, stmt) -> int | None:
        span = getattr(stmt, "span", None)
        if span is None:
            return None
        return getattr(span, "line", None) or getattr(span, "start_line", None)

    def _emit(self, indent: int, code: str, *, pys_line: int | None = None) -> None:
        self.lines.append(("  " * indent) + code)
        self.origins.append(pys_line)

    def _append_raw(self, code: str, *, pys_line: int | None = None) -> None:
        self.lines.append(code)
        self.origins.append(pys_line)

    def _unsupported(self, node) -> None:
        name = type(node).__name__
        raise JsEmitError(
            f"JavaScript emitter does not support {name}; "
            "use --target python or simplify the program."
        )

    def _stmt(self, stmt, indent: int) -> None:
        pys = self._pys_line(stmt)
        if isinstance(stmt, BlankStmt):
            self._append_raw("", pys_line=None)
        elif isinstance(stmt, CommentStmt):
            text = stmt.text
            if text.lstrip().startswith("#"):
                stripped = text.lstrip()
                lead = text[: len(text) - len(stripped)]
                text = lead + "//" + stripped[1:]
            self._append_raw(text, pys_line=pys)
        elif isinstance(stmt, PrintStmt):
            self._emit(
                indent,
                f"console.log(_pys_format({self._expr(stmt.value)}));",
                pys_line=pys,
            )
        elif isinstance(stmt, AssignStmt):
            self._assign(stmt, indent, pys_line=pys)
        elif isinstance(stmt, ArrayDecl):
            init = (
                self._typed_collection_rhs(stmt.elem_type, stmt.value)
                if stmt.value is not None
                else "[]"
            )
            self._emit(indent, f"let {stmt.name} = {init};", pys_line=pys)
        elif isinstance(stmt, AugAssignStmt):
            name = self._js_lvalue(stmt.name)
            shared = stmt.name in self.shared_vars
            atomic = stmt.name in self.atomic_vars
            if shared or atomic:
                if stmt.op == "++":
                    self._emit(indent, f"{name}.iadd(1);", pys_line=pys)
                elif stmt.op == "--":
                    self._emit(indent, f"{name}.isub(1);", pys_line=pys)
                elif stmt.op == "+=":
                    self._emit(
                        indent,
                        f"{name}.iadd({self._expr(stmt.value)});",
                        pys_line=pys,
                    )
                elif stmt.op == "-=":
                    self._emit(
                        indent,
                        f"{name}.isub({self._expr(stmt.value)});",
                        pys_line=pys,
                    )
                elif atomic:
                    self._emit(
                        indent,
                        f"{name}.set({name}.get() {stmt.op[0]} {self._expr(stmt.value)});",
                        pys_line=pys,
                    )
                else:
                    self._emit(
                        indent,
                        f"{name}.set({name}.value {stmt.op[0]} {self._expr(stmt.value)});",
                        pys_line=pys,
                    )
            elif stmt.op == "++":
                self._emit(indent, f"{name}++;", pys_line=pys)
            elif stmt.op == "--":
                self._emit(indent, f"{name}--;", pys_line=pys)
            else:
                self._emit(
                    indent,
                    f"{name} {stmt.op} {self._expr(stmt.value)};",
                    pys_line=pys,
                )
        elif isinstance(stmt, SharedDecl):
            self.shared_vars.add(stmt.name)
            self._emit(
                indent,
                f"let {stmt.name} = new _PysShared({self._expr(stmt.value)});",
                pys_line=pys,
            )
        elif isinstance(stmt, AtomicDecl):
            self.atomic_vars.add(stmt.name)
            self._emit(
                indent,
                f"let {stmt.name} = new _PysAtomic({self._expr(stmt.value)});",
                pys_line=pys,
            )
        elif isinstance(stmt, TasksBlock):
            self._tasks(stmt, indent)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value is None:
                self._emit(indent, "return;", pys_line=pys)
            else:
                self._emit(
                    indent,
                    f"return {self._maybe_copy_struct(stmt.value)};",
                    pys_line=pys,
                )
        elif isinstance(stmt, PassStmt):
            self._emit(indent, "/* pass */", pys_line=pys)
        elif isinstance(stmt, BreakStmt):
            self._emit(indent, "break;", pys_line=pys)
        elif isinstance(stmt, ContinueStmt):
            self._emit(indent, "continue;", pys_line=pys)
        elif isinstance(stmt, IfStmt):
            self._if(stmt, indent, first=True)
        elif isinstance(stmt, SwitchStmt):
            self._switch_stmt(stmt, indent)
        elif isinstance(stmt, WhileStmt):
            self._emit(indent, f"while ({self._expr(stmt.cond)}) {{", pys_line=pys)
            self._block(stmt.body, indent + 1)
            self._emit(indent, "}", pys_line=None)
        elif isinstance(stmt, ForRangeStmt):
            start = self._expr(stmt.start)
            stop = self._expr(stmt.stop)
            self._emit(
                indent,
                f"for (let {stmt.var} = {start}; {stmt.var} < {stop}; {stmt.var}++) {{",
                pys_line=pys,
            )
            self._block(stmt.body, indent + 1)
            self._emit(indent, "}", pys_line=None)
        elif isinstance(stmt, ForEachStmt):
            self._emit(
                indent,
                f"for (const {stmt.var} of _pys_iter({self._expr(stmt.iterable)})) {{",
                pys_line=pys,
            )
            self._block(stmt.body, indent + 1)
            self._emit(indent, "}", pys_line=None)
        elif isinstance(stmt, RepeatStmt):
            self._repeat(stmt, indent)
        elif isinstance(stmt, FunctionDef):
            if stmt.decorators:
                raise JsEmitError(
                    "JavaScript emitter does not support library decorators; "
                    "use --target python for decorated functions/methods."
                )
            self._function(stmt, indent)
        elif isinstance(stmt, ClassDef):
            self._class(stmt, indent)
        elif isinstance(stmt, InterfaceDef):
            self._emit(indent, f"/* interface {stmt.name} */", pys_line=pys)
        elif isinstance(stmt, TraitDef):
            # Flattened into uses hosts — no runtime type.
            return
        elif isinstance(stmt, DataDef):
            self._data_or_struct(stmt, indent, kind="data")
        elif isinstance(stmt, StructDef):
            self._data_or_struct(stmt, indent, kind="struct")
        elif isinstance(stmt, EntityDef):
            self._entity(stmt, indent)
        elif isinstance(stmt, EnumDef):
            self._enum(stmt, indent)
        elif isinstance(stmt, ImportStmt):
            self._import(stmt, indent)
        elif isinstance(stmt, ExprStmt):
            self._emit(indent, f"{self._expr(stmt.expr)};", pys_line=pys)
        else:
            self._unsupported(stmt)

    def _block(self, body: Block | None, indent: int) -> None:
        if body is None or not body.statements:
            self._emit(indent, "/* empty */", pys_line=None)
            return
        for s in body.statements:
            self._stmt(s, indent)

    def _assign(self, stmt: AssignStmt, indent: int, *, pys_line: int | None) -> None:
        expected = stmt.declare_type if stmt.declare_type and stmt.declare_type != "var" else None
        if expected is None and "." not in stmt.name and "[" not in stmt.name:
            expected = self.var_types.get(stmt.name)
        if isinstance(
            stmt.value,
            (BraceLiteral, ArrayLiteral, DictLiteral, SetLiteral, TupleLiteral),
        ):
            rhs = self._typed_collection_rhs(stmt.declare_type, stmt.value)
        else:
            rhs = self._maybe_copy_struct(stmt.value, expected_type=expected)
        name = self._js_lvalue(stmt.name)
        if "." not in stmt.name and "[" not in stmt.name and stmt.declare_type:
            self.var_types[stmt.name] = stmt.declare_type
        if "." not in stmt.name and "[" not in stmt.name and stmt.name in self.shared_vars:
            self._emit(indent, f"{name}.set({rhs});", pys_line=pys_line)
            return
        if "." not in stmt.name and "[" not in stmt.name and stmt.name in self.atomic_vars:
            self._emit(indent, f"{name}.set({rhs});", pys_line=pys_line)
            return
        if stmt.declare_type is not None:
            kw = "const" if (stmt.is_const or stmt.is_fix) else "let"
            if stmt.declare_type == "string" or stmt.declare_type.startswith("string"):
                self.var_kinds[stmt.name] = "string"
            base = (stmt.declare_type or "").split("<", 1)[0].strip()
            if base in ("list", "array"):
                self.var_kinds[stmt.name] = "array"
            exp = (
                "export "
                if stmt.visibility in ("global", "package") and indent == 0
                else ""
            )
            self._emit(indent, f"{exp}{kw} {name} = {rhs};", pys_line=pys_line)
            self.debug_names[stmt.name] = stmt.name
        else:
            self._emit(indent, f"{name} = {rhs};", pys_line=pys_line)

    def _typed_collection_rhs(self, declare_type: str | None, value: Expr | None) -> str:
        """Lower brace/list literals using declared collection type when present."""
        base = (declare_type or "").split("<", 1)[0].strip()
        if isinstance(value, BraceLiteral):
            elems = ", ".join(self._expr(e) for e in value.elements)
            if base == "set":
                return f"new Set([{elems}])" if elems else "new Set()"
            if base in ("list", "array", "") or declare_type is None:
                return f"[{elems}]"
            # typed arrays / unknown → array
            return f"[{elems}]"
        if isinstance(value, SetLiteral):
            elems = ", ".join(self._expr(e) for e in value.elements)
            return f"new Set([{elems}])" if elems else "new Set()"
        return self._expr(value)

    def _js_lvalue(self, name: str) -> str:
        # Assign targets are flattened strings (e.g. m[self.keyOf(a, b)]);
        # rewrite receiver self → this without touching identifiers like myself.
        if name == "self":
            return "this"
        return re.sub(r"\bself\.", "this.", name)

    def _if(self, stmt: IfStmt, indent: int, *, first: bool) -> None:
        kw = "if" if first else "else if"
        pys = self._pys_line(stmt)
        cond = self._expr(stmt.cond)
        if stmt.negated:
            cond = f"!({cond})"
        self._emit(indent, f"{kw} ({cond}) {{", pys_line=pys)
        self._block(stmt.then_body, indent + 1)
        if stmt.else_body is None:
            self._emit(indent, "}", pys_line=None)
            return
        if (
            isinstance(stmt.else_body, Block)
            and len(stmt.else_body.statements) == 1
            and isinstance(stmt.else_body.statements[0], IfStmt)
        ):
            self._emit(indent, "}", pys_line=None)
            self._if(stmt.else_body.statements[0], indent, first=False)
            return
        self._emit(indent, "} else {", pys_line=None)
        self._block(stmt.else_body, indent + 1)
        self._emit(indent, "}", pys_line=None)

    def _repeat(self, stmt: RepeatStmt, indent: int) -> None:
        pys = self._pys_line(stmt)
        serial = self._repeat_serial
        self._repeat_serial += 1
        var = f"_pys_rep_{serial}"
        self._emit(
            indent,
            f"for (let {var} = 0; {var} < {self._expr(stmt.count)}; {var}++) {{",
            pys_line=pys,
        )
        self._block(stmt.body, indent + 1)
        self._emit(indent, "}", pys_line=None)

    def _function(self, stmt: FunctionDef, indent: int) -> None:
        pys = self._pys_line(stmt)
        params = ", ".join(stmt.params)
        prev = self._current_function
        self._current_function = stmt.name
        exp = "export " if stmt.visibility in ("global", "package") else ""
        self._emit(indent, f"{exp}function {stmt.name}({params}) {{", pys_line=pys)
        if self._base_type(stmt.return_type) == "result":
            self._emit(indent + 1, "try {", pys_line=pys)
            self._block(stmt.body, indent + 2)
            self._emit(indent + 1, "} catch (_pys_signal) {", pys_line=None)
            self._emit(
                indent + 2,
                "if (_pys_signal && _pys_signal._pys_propagate) return _pys_signal.result;",
                pys_line=None,
            )
            self._emit(indent + 2, "throw _pys_signal;", pys_line=None)
            self._emit(indent + 1, "}", pys_line=None)
        else:
            self._block(stmt.body, indent + 1)
        self._emit(indent, "}", pys_line=None)
        self._current_function = prev

    def _tasks(self, stmt: TasksBlock, indent: int) -> None:
        pys = self._pys_line(stmt)
        tg = f"_pys_tg_{stmt.group_id}"
        prev = self.tg_name
        self.tg_name = tg
        self._emit(indent, f"const {tg} = new _PysTaskGroup();", pys_line=pys)
        for task in stmt.tasks:
            self._task_def(task, indent, tg)
        self._emit(indent, f"{tg}.run();", pys_line=pys)
        self.tg_name = prev

    def _task_def(self, task: TaskDef, indent: int, tg: str) -> None:
        pys = self._pys_line(task)
        params = ", ".join(task.params)
        self._emit(indent, f"function __pys_task_{task.name}({params}) {{", pys_line=pys)
        self._block(task.body, indent + 1)
        self._emit(indent, "}", pys_line=None)
        if task.is_template:
            self._emit(
                indent,
                f"{tg}.add_template({task.name!r}, __pys_task_{task.name});",
                pys_line=pys,
            )
        else:
            self._emit(
                indent,
                f"{tg}.add_auto({task.name!r}, __pys_task_{task.name});",
                pys_line=pys,
            )

    def _class(self, stmt: ClassDef, indent: int) -> None:
        pys = self._pys_line(stmt)
        # `inherits` → extends; interface `implements` stay duck-typed (no runtime base).
        extends = f" extends {stmt.parent}" if stmt.parent else ""
        exp = "export " if stmt.visibility in ("global", "package") else ""
        self._emit(indent, f"{exp}class {stmt.name}{extends} {{", pys_line=pys)
        for f in stmt.fields:
            if f.is_static:
                default = (
                    self._expr(f.default)
                    if f.default is not None
                    else self._js_default(f.type_name)
                )
                self._emit(indent + 1, f"static {f.name} = {default};", pys_line=pys)
            elif f.default is not None:
                self._emit(
                    indent + 1,
                    f"{f.name} = {self._expr(f.default)};",
                    pys_line=pys,
                )
        host_names = {m.name for m in stmt.methods if not m.is_constructor}
        flat_methods: list[tuple[dict[str, str], MethodDef]] = []
        mangled_methods: list[tuple[dict[str, str], str, MethodDef]] = []
        for use in stmt.uses:
            remaps = dict(use.remaps)
            trait = self.trait_defs.get(use.name)
            if trait is None:
                continue
            for m in trait.methods:
                mangled = f"_{use.name}_{m.name}"
                if m.name in host_names:
                    mangled_methods.append((remaps, mangled, m))
                else:
                    flat_methods.append((remaps, m))
        ctors = [m for m in stmt.methods if m.is_constructor]
        others = [m for m in stmt.methods if not m.is_constructor]
        self._emit_constructors(ctors, indent + 1)
        for remaps, mangled, m in mangled_methods:
            self._method(m, indent + 1, emit_name=mangled, requires_remap=remaps)
        self._emit_methods_grouped(others, indent + 1)
        for remaps, m in flat_methods:
            self._method(m, indent + 1, requires_remap=remaps)
        if not stmt.fields and not stmt.methods and not flat_methods and not mangled_methods:
            self._emit(indent + 1, "/* empty class */", pys_line=None)
        self._emit(indent, "}", pys_line=None)

    def _is_ctor_chain_only(self, m: MethodDef) -> bool:
        if m.body is None or len(m.body.statements) != 1:
            return False
        stmt = m.body.statements[0]
        if not isinstance(stmt, ExprStmt) or not isinstance(stmt.expr, Call):
            return False
        cal = stmt.expr.callee
        return isinstance(cal, Identifier) and cal.name in ("this", "self")

    def _emit_constructors(self, ctors: list[MethodDef], indent: int) -> None:
        if not ctors:
            return
        concrete = [m for m in ctors if not self._is_ctor_chain_only(m)]
        if not concrete:
            concrete = ctors
        # Prefer longest arity; chain-only overloads become defaults when possible.
        primary = max(concrete, key=lambda m: len(m.params))
        chain = [m for m in ctors if self._is_ctor_chain_only(m)]
        defaults: dict[int, str] = {}
        for m in chain:
            # this(a, b, LIT) → default for missing trailing params
            call = m.body.statements[0].expr  # type: ignore[union-attr]
            assert isinstance(call, Call)
            if len(call.args) == len(primary.params):
                for i, arg in enumerate(call.args):
                    if i >= len(m.params) and isinstance(arg, Literal):
                        defaults[i] = self._expr(arg)
        params: list[str] = []
        for i, name in enumerate(primary.params):
            if i in defaults:
                params.append(f"{name} = {defaults[i]}")
            else:
                params.append(name)
        pys = self._pys_line(primary)
        prev = self._current_function
        self._current_function = "constructor"
        self._emit(indent, f"constructor({', '.join(params)}) {{", pys_line=pys)
        self._block(primary.body, indent + 1)
        self._emit(indent, "}", pys_line=None)
        self._current_function = prev

    def _emit_methods_grouped(self, methods: list[MethodDef], indent: int) -> None:
        by_name: dict[str, list[MethodDef]] = {}
        order: list[str] = []
        for m in methods:
            if m.name not in by_name:
                order.append(m.name)
                by_name[m.name] = []
            by_name[m.name].append(m)
        for name in order:
            group = by_name[name]
            if len(group) == 1:
                self._method(group[0], indent)
            else:
                self._emit_method_overloads(name, group, indent)

    def _emit_method_overloads(
        self, name: str, group: list[MethodDef], indent: int
    ) -> None:
        pys = self._pys_line(group[0])
        static = "static " if group[0].is_static else ""
        self._emit(indent, f"{static}{name}(..._pys_args) {{", pys_line=pys)
        for m in sorted(group, key=lambda x: len(x.params)):
            n = len(m.params)
            self._emit(indent + 1, f"if (_pys_args.length === {n}) {{", pys_line=pys)
            for i, p in enumerate(m.params):
                self._emit(indent + 2, f"const {p} = _pys_args[{i}];", pys_line=pys)
            prev = self._current_function
            self._current_function = name
            self._block(m.body, indent + 2)
            self._emit(indent + 2, "return;", pys_line=None)
            self._current_function = prev
            self._emit(indent + 1, "}", pys_line=None)
        self._emit(
            indent + 1,
            f"throw new Error('no overload of {name} for ' + _pys_args.length + ' args');",
            pys_line=pys,
        )
        self._emit(indent, "}", pys_line=None)

    def _method(
        self,
        m: MethodDef,
        indent: int,
        *,
        emit_name: str | None = None,
        requires_remap: dict[str, str] | None = None,
    ) -> None:
        prev_remap = self._trait_requires_remap
        self._trait_requires_remap = dict(requires_remap or {})
        try:
            self._method_body(m, indent, emit_name=emit_name)
        finally:
            self._trait_requires_remap = prev_remap

    def _method_body(
        self, m: MethodDef, indent: int, *, emit_name: str | None = None
    ) -> None:
        pys = self._pys_line(m)
        prev = self._current_function
        name = emit_name or m.name
        self._current_function = name
        if m.decorators:
            raise JsEmitError(
                "JavaScript emitter does not support library decorators; "
                "use --target python for decorated methods."
            )
        if m.is_abstract:
            params = ", ".join(m.params)
            out_name = "constructor" if m.is_constructor else name
            self._emit(
                indent,
                f"{out_name}({params}) {{ throw new Error('abstract {m.name}'); }}",
                pys_line=pys,
            )
            self._current_function = prev
            return
        params = ", ".join(m.params)
        if m.is_static:
            self._emit(indent, f"static {name}({params}) {{", pys_line=pys)
        elif m.is_constructor:
            self._emit(indent, f"constructor({params}) {{", pys_line=pys)
        else:
            self._emit(indent, f"{name}({params}) {{", pys_line=pys)
        self._block(m.body, indent + 1)
        self._emit(indent, "}", pys_line=None)
        self._current_function = prev

    def _data_or_struct(
        self, stmt: DataDef | StructDef, indent: int, *, kind: str
    ) -> None:
        pys = self._pys_line(stmt)
        fields = stmt.fields
        self.struct_field_types[stmt.name] = {f.name: f.type_name for f in fields}
        params = ", ".join(f.name for f in fields)
        self._emit(indent, f"class {stmt.name} {{", pys_line=pys)
        self._emit(indent + 1, f"constructor({params}) {{", pys_line=pys)
        for f in fields:
            self._emit(indent + 2, f"this.{f.name} = {f.name};", pys_line=pys)
        if kind == "data":
            self._emit(indent + 2, "Object.freeze(this);", pys_line=pys)
        self._emit(indent + 1, "}", pys_line=None)
        self._emit(indent + 1, "equals(other) {", pys_line=pys)
        if not fields:
            self._emit(
                indent + 2,
                f"return other instanceof {stmt.name};",
                pys_line=pys,
            )
        else:
            checks = " && ".join(
                f"_pys_value_eq(this.{f.name}, other.{f.name})" for f in fields
            )
            self._emit(
                indent + 2,
                f"return other instanceof {stmt.name} && {checks};",
                pys_line=pys,
            )
        self._emit(indent + 1, "}", pys_line=None)
        self._emit(indent + 1, "_pys_copy() {", pys_line=pys)
        if not fields:
            self._emit(indent + 2, f"return new {stmt.name}();", pys_line=pys)
        else:
            copy_args = ", ".join(
                f"_pys_struct_copy(this.{f.name})" for f in fields
            )
            self._emit(
                indent + 2,
                f"return new {stmt.name}({copy_args});",
                pys_line=pys,
            )
        self._emit(indent + 1, "}", pys_line=None)
        self._emit(indent, "}", pys_line=None)
        if getattr(stmt, "visibility", "") in ("global", "package"):
            self._emit(indent, f"export {{ {stmt.name} }};", pys_line=pys)

    def _entity_identity_keys(self, stmt: EntityDef) -> list[str]:
        keys: list[str] = []
        if stmt.parent and stmt.parent in self.entity_defs:
            keys.extend(self._entity_identity_keys(self.entity_defs[stmt.parent]))
        keys.extend(stmt.identity)
        return keys

    def _entity(self, stmt: EntityDef, indent: int) -> None:
        pys = self._pys_line(stmt)
        extends = f" extends {stmt.parent}" if stmt.parent else ""
        self._emit(indent, f"class {stmt.name}{extends} {{", pys_line=pys)
        for f in stmt.fields:
            if f.default is not None:
                self._emit(
                    indent + 1,
                    f"{f.name} = {self._expr(f.default)};",
                    pys_line=pys,
                )
            else:
                self._emit(
                    indent + 1,
                    f"{f.name} = {self._js_default(f.type_name)};",
                    pys_line=pys,
                )
        for m in stmt.methods:
            self._method(m, indent + 1)
        keys = self._entity_identity_keys(stmt)
        if keys:
            key_self = ", ".join(f"this.{k}" for k in keys)
            key_other = ", ".join(f"other.{k}" for k in keys)
            self._emit(indent + 1, "equals(other) {", pys_line=pys)
            self._emit(
                indent + 2,
                f"return other instanceof {stmt.name} && "
                f"_pys_eq_tuple([{key_self}], [{key_other}]);",
                pys_line=pys,
            )
            self._emit(indent + 1, "}", pys_line=None)
            self._emit(indent + 1, "hashCode() {", pys_line=pys)
            self._emit(
                indent + 2,
                f"return _pys_hash_tuple([{key_self}]);",
                pys_line=pys,
            )
            self._emit(indent + 1, "}", pys_line=None)
        if not stmt.fields and not stmt.methods and not keys:
            self._emit(indent + 1, "/* empty entity */", pys_line=None)
        self._emit(indent, "}", pys_line=None)
        if getattr(stmt, "visibility", "") in ("global", "package"):
            self._emit(indent, f"export {{ {stmt.name} }};", pys_line=pys)

    def _enum(self, stmt: EnumDef, indent: int) -> None:
        pys = self._pys_line(stmt)
        parts: list[str] = []
        for i, m in enumerate(stmt.members):
            if m.value is None:
                val = str(i)
            else:
                val = self._expr(m.value)
            parts.append(f'{m.name}: _pys_enum_member({m.name!r}, {val})')
        body = ", ".join(parts)
        self._emit(
            indent,
            f"const {stmt.name} = Object.freeze({{ {body} }});",
            pys_line=pys,
        )
        if stmt.visibility in ("global", "package"):
            self._emit(indent, f"export {{ {stmt.name} }};", pys_line=pys)

    def _sibling_export_names(self, module: str) -> list[str]:
        if self.source_path is None:
            return []
        path = self.source_path.parent / f"{module}.pys"
        if not path.is_file():
            return []
        from ..imports import _parse_module

        info = _parse_module(path, path.read_text(encoding="utf-8")).info
        return sorted(
            n for n, vis in info.exports.items() if vis in ("global", "package")
        )

    def _import(self, stmt: ImportStmt, indent: int) -> None:
        pys = self._pys_line(stmt)
        module = stmt.module or ""
        # Minimal stdlib shims used by teaching demos (no Node package).
        if module == "time" and stmt.kind in ("module", "as"):
            alias = stmt.alias if stmt.kind == "as" and stmt.alias else "time"
            self._emit(
                indent,
                f"const {alias} = {{ sleep(seconds) {{ "
                f"const end = Date.now() + (Number(seconds) * 1000); "
                f"while (Date.now() < end) {{ /* busy-wait; cooperative tasks */ }} "
                f"}}, "
                f"time() {{ return Date.now() / 1000; }}, "
                f"isoformat() {{ return new Date().toISOString().slice(0, 19); }} "
                f"}};",
                pys_line=pys,
            )
            return
        if module == "json" and stmt.kind in ("module", "as"):
            alias = stmt.alias if stmt.kind == "as" and stmt.alias else "json"
            self._emit(
                indent,
                f"const {alias} = {{ "
                f"dumps(value, ..._args) {{ return JSON.stringify(value); }}, "
                f"loads(text) {{ return JSON.parse(text); }} "
                f"}};",
                pys_line=pys,
            )
            return
        npm = _JS_PACKAGE_MAP.get(module)
        if npm is None and ("." in module or module in {"tkinter", "sys", "os", "re", "math"}):
            raise JsEmitError(
                f"JavaScript emitter cannot import Python package {module!r}; "
                "use --target python, a sibling .pys module, or an npm-mapped "
                "name (nodegui, mysql2, express, crypto, buffer)."
            )
        if npm is not None:
            use_default = module in _JS_DEFAULT_EXPORT_PACKAGES
            if stmt.kind == "module":
                if use_default:
                    self._emit(
                        indent,
                        f'import {stmt.module} from "{npm}";',
                        pys_line=pys,
                    )
                else:
                    self._emit(
                        indent,
                        f'import * as {stmt.module} from "{npm}";',
                        pys_line=pys,
                    )
            elif stmt.kind == "as":
                if use_default:
                    self._emit(
                        indent,
                        f'import {stmt.alias} from "{npm}";',
                        pys_line=pys,
                    )
                else:
                    self._emit(
                        indent,
                        f'import * as {stmt.alias} from "{npm}";',
                        pys_line=pys,
                    )
            elif stmt.kind == "name_from":
                names = ", ".join(stmt.names) if stmt.names else stmt.name
                self._emit(
                    indent,
                    f'import {{ {names} }} from "{npm}";',
                    pys_line=pys,
                )
            elif stmt.kind == "all_from":
                self._emit(
                    indent,
                    f'import * as _{stmt.module.replace("@", "").replace("/", "_")} from "{npm}";',
                    pys_line=pys,
                )
            else:
                self._unsupported(stmt)
            return
        if stmt.kind == "module":
            self._emit(
                indent,
                f'import * as {stmt.module} from "./{stmt.module}.mjs";',
                pys_line=pys,
            )
            names = self._sibling_export_names(stmt.module)
            if names:
                self._emit(
                    indent,
                    f"const {{ {', '.join(names)} }} = {stmt.module};",
                    pys_line=pys,
                )
                for n in names:
                    if n and n[0].isupper():
                        self.class_names.add(n)
        elif stmt.kind == "as":
            self._emit(
                indent,
                f'import * as {stmt.alias} from "./{stmt.module}.mjs";',
                pys_line=pys,
            )
        elif stmt.kind == "all_from":
            self._emit(
                indent,
                f'import * as _{stmt.module} from "./{stmt.module}.mjs";',
                pys_line=pys,
            )
            names = self._sibling_export_names(stmt.module)
            if names:
                self._emit(
                    indent,
                    f"const {{ {', '.join(names)} }} = _{stmt.module};",
                    pys_line=pys,
                )
                for n in names:
                    if n and n[0].isupper():
                        self.class_names.add(n)
        elif stmt.kind == "name_from":
            names = ", ".join(stmt.names) if stmt.names else stmt.name
            self._emit(
                indent,
                f'import {{ {names} }} from "./{stmt.module}.mjs";',
                pys_line=pys,
            )
            for n in (stmt.names or ([stmt.name] if stmt.name else [])):
                if n and n[0].isupper():
                    self.class_names.add(n)
        else:
            self._unsupported(stmt)

    def _switch_label_cmp(self, subject: str, label: Expr) -> str:
        return f"({subject} === {self._expr(label)})"

    def _switch_labels_cond(self, subject: str, labels: list[Expr]) -> str:
        if not labels:
            return "true"
        parts = [self._switch_label_cmp(subject, lab) for lab in labels]
        if len(parts) == 1:
            return parts[0]
        return " || ".join(parts)

    def _switch_stmt_groups(
        self, cases: list[SwitchCase]
    ) -> list[tuple[list[Expr] | None, Block | None]]:
        groups: list[tuple[list[Expr] | None, Block | None]] = []
        pending: list[Expr] = []
        for case in cases:
            if case.is_default:
                if pending:
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
                self._emit(indent, "else {", pys_line=self._pys_line(stmt))
                self._block(body, indent + 1)
                self._emit(indent, "}", pys_line=None)
                first = False
                continue
            cond = self._switch_labels_cond(subject, labels)
            head = f"if ({cond}) {{" if first else f"else if ({cond}) {{"
            self._emit(indent, head, pys_line=self._pys_line(stmt))
            self._block(body, indent + 1)
            self._emit(indent, "}", pys_line=None)
            first = False

    def _result_switch_stmt(self, stmt: SwitchStmt, indent: int) -> None:
        serial = self._result_switch_serial
        self._result_switch_serial += 1
        subject = f"_pys_result_{serial}"
        pys = self._pys_line(stmt)
        self._emit(
            indent, f"const {subject} = {self._expr(stmt.subject)};", pys_line=pys
        )
        patterns = [case for case in stmt.cases if not case.is_default]
        default = next((case for case in stmt.cases if case.is_default), None)
        for index, case in enumerate(patterns):
            pattern = case.labels[0]
            assert isinstance(pattern, ResultPattern)
            head = "if" if index == 0 else "else if"
            self._emit(
                indent,
                f"{head} ({subject}._pys_result_kind === {pattern.kind!r}) {{",
                pys_line=pys,
            )
            if pattern.binding:
                self._emit(
                    indent + 1,
                    f"const {pattern.binding} = {subject}.value;",
                    pys_line=pys,
                )
            self._block(case.body, indent + 1)
            self._emit(indent, "}", pys_line=None)
        if default is not None:
            if patterns:
                self._emit(indent, "else {", pys_line=pys)
                self._block(default.body, indent + 1)
                self._emit(indent, "}", pys_line=None)
            else:
                self._block(default.body, indent)

    def _switch_expr(self, expr: SwitchExpr) -> str:
        if any(
            isinstance(label, ResultPattern)
            for case in expr.cases
            for label in case.labels
        ):
            return self._result_switch_expr(expr)
        subject = self._expr(expr.subject)
        arms: list[tuple[list[Expr] | None, Expr | None]] = []
        for case in expr.cases:
            if case.is_default:
                arms.append((None, case.value))
            else:
                arms.append((case.labels, case.value))
        if not arms:
            return "null"
        result = "null"
        for labels, value in reversed(arms):
            val = self._expr(value)
            if labels is None:
                result = val
            else:
                cond = self._switch_labels_cond(subject, labels)
                result = f"(({cond}) ? ({val}) : ({result}))"
        return result

    def _result_switch_expr(self, expr: SwitchExpr) -> str:
        serial = self._result_switch_serial
        self._result_switch_serial += 1
        name = f"_pys_result_switch_{serial}"
        subject = self._expr(expr.subject)
        parts = [f"(function({name}) {{"]
        patterns = [case for case in expr.cases if not case.is_default]
        default = next((case for case in expr.cases if case.is_default), None)
        for index, case in enumerate(patterns):
            pattern = case.labels[0]
            assert isinstance(pattern, ResultPattern)
            head = "if" if index == 0 else "else if"
            bind = ""
            if pattern.binding:
                bind = f"const {pattern.binding} = {name}.value; "
            parts.append(
                f"{head} ({name}._pys_result_kind === {pattern.kind!r}) {{ "
                f"{bind}return {self._expr(case.value)}; }}"
            )
        if default is not None:
            parts.append(f"return {self._expr(default.value)};")
        else:
            parts.append("return null;")
        parts.append(f"}})({subject})")
        return " ".join(parts)

    def _expr(self, expr: Expr | None) -> str:
        if expr is None:
            return ""
        if isinstance(expr, Literal):
            return self._literal(expr)
        if isinstance(expr, InterpolatedString):
            text = _translate_string_literal(expr.raw)
            if self._trait_requires_remap:
                for req, host in sorted(
                    self._trait_requires_remap.items(), key=lambda kv: -len(kv[0])
                ):
                    text = re.sub(
                        rf"\bthis\.{re.escape(req)}\b",
                        f"this.{host}",
                        text,
                    )
            if text.startswith(("f'", 'f"', "F'", 'F"')):
                inner = text[2:-1]
                return "`" + inner.replace("{", "${") + "`"
            return text
        if isinstance(expr, Identifier):
            if expr.name == "self":
                return "this"
            if expr.name in self.shared_vars:
                return f"{expr.name}.value"
            if expr.name in self.atomic_vars:
                return f"{expr.name}.get()"
            return expr.name
        if isinstance(expr, AwaitExpr):
            return self._await(expr)
        if isinstance(expr, UnaryOp):
            if expr.op == "not":
                inner = self._expr(expr.operand)
                if isinstance(expr.operand, (BinaryOp, UnaryOp)):
                    return f"!({inner})"
                return f"!{inner}"
            return f"{expr.op}{self._expr(expr.operand)}"
        if isinstance(expr, BinaryOp):
            return self._binop(expr)
        if isinstance(expr, Call):
            return self._call(expr)
        if isinstance(expr, Member):
            attr = expr.name
            if (
                self._trait_requires_remap
                and isinstance(expr.object, Identifier)
                and expr.object.name in ("self", "this")
                and attr in self._trait_requires_remap
            ):
                attr = self._trait_requires_remap[attr]
            return f"{self._expr(expr.object)}.{attr}"
        if isinstance(expr, Index):
            return f"{self._expr(expr.object)}[{self._expr(expr.index)}]"
        if isinstance(expr, Slice):
            return self._slice(expr)
        if isinstance(expr, Cast):
            return self._cast(expr)
        if isinstance(expr, ArrayLiteral):
            elems = ", ".join(self._expr(e) for e in expr.elements)
            return f"[{elems}]"
        if isinstance(expr, TupleLiteral):
            elems = ", ".join(self._expr(e) for e in expr.elements)
            return f"[{elems}]"
        if isinstance(expr, SetLiteral):
            elems = ", ".join(self._expr(e) for e in expr.elements)
            return f"new Set([{elems}])"
        if isinstance(expr, DictLiteral):
            parts = []
            for k, v in expr.entries:
                parts.append(f"[{self._expr(k)}]: {self._expr(v)}")
            return "{" + ", ".join(parts) + "}"
        if isinstance(expr, BraceLiteral):
            elems = ", ".join(self._expr(e) for e in expr.elements)
            return f"[{elems}]"
        if isinstance(expr, ArrayAlloc):
            return self._array_alloc(expr)
        if isinstance(expr, ResultCtor):
            if expr.kind == "ok" and expr.value is None:
                return "_pys_ok()"
            return f"_pys_{expr.kind}({self._expr(expr.value)})"
        if isinstance(expr, PropagateExpr):
            span = expr.span
            file = str(self.source_path) if self.source_path is not None else "<memory>"
            line = span.line if span else 1
            return (
                f"_pys_propagate({self._expr(expr.operand)}, {file!r}, "
                f"{line}, {self._current_function!r})"
            )
        if isinstance(expr, SwitchExpr):
            return self._switch_expr(expr)
        if isinstance(expr, LambdaExpr):
            return self._lambda(expr)
        if isinstance(expr, KeywordArg):
            return self._expr(expr.value)
        self._unsupported(expr)
        return ""

    def _await(self, expr: AwaitExpr) -> str:
        tg = self.tg_name or "_pys_tg_0"
        target = expr.target
        if isinstance(target, Call) and isinstance(target.callee, Identifier):
            args = ", ".join(self._expr(a) for a in target.args)
            if args:
                return f"_pys_await({tg}.call({target.callee.name!r}, {args}))"
            return f"_pys_await({tg}.call({target.callee.name!r}))"
        if isinstance(target, Identifier):
            return f"_pys_await({tg}.futures[{target.name!r}])"
        return f"_pys_await({self._expr(target)})"

    def _base_type(self, type_name: str) -> str:
        return type_name.split("<", 1)[0].strip() if type_name else ""

    def _is_struct_type(self, type_name: str) -> bool:
        return self._base_type(type_name) in self.struct_names

    def _expr_is_struct_value(self, expr: Expr | None) -> bool:
        if expr is None:
            return False
        if isinstance(expr, Call) and isinstance(expr.callee, Identifier):
            return expr.callee.name in self.struct_names
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
            return self._maybe_copy_struct(expr.value, expected_type=expected_type)
        code = self._expr(expr)
        if self._expr_is_struct_value(expr) or (
            expected_type and self._is_struct_type(expected_type)
        ):
            return f"_pys_struct_copy({code})"
        return code

    def _lambda(self, expr: LambdaExpr) -> str:
        params = ", ".join(expr.params)
        if isinstance(expr.body, Expr):
            return f"({params}) => {self._expr(expr.body)}"
        if isinstance(expr.body, Block):
            stmts = expr.body.statements if expr.body else []
            if not stmts:
                return f"({params}) => {{}}"
            saved_lines = self.lines
            saved_origins = self.origins
            self.lines = []
            self.origins = []
            for s in stmts:
                self._stmt(s, 1)
            body_lines = list(self.lines)
            self.lines = saved_lines
            self.origins = saved_origins
            body = "\n".join(body_lines)
            return f"({params}) => {{\n{body}\n}}"
        raise JsEmitError(
            "JavaScript emitter supports expression or block lambdas only."
        )

    def _slice(self, expr: Slice) -> str:
        obj = self._expr(expr.object)
        start = self._expr(expr.start) if expr.start is not None else "null"
        stop = self._expr(expr.stop) if expr.stop is not None else "null"
        step = self._expr(expr.step) if expr.step is not None else "null"
        return f"_pys_slice({obj}, {start}, {stop}, {step})"

    def _array_alloc(self, expr: ArrayAlloc) -> str:
        default = self._js_default(expr.elem_type)

        def nest(dims: list[int | None]) -> str:
            if not dims:
                return default
            n = dims[0]
            rest = dims[1:]
            if n is None:
                return "[]"
            if not rest:
                return f"Array({n}).fill({default})"
            inner = nest(rest)
            return f"Array.from({{length: {n}}}, () => {inner})"

        return nest(list(expr.dims))

    def _call(self, expr: Call) -> str:
        # All-keyword call → options object for foreign APIs; positional for PYS types.
        all_kw = bool(expr.args) and all(isinstance(a, KeywordArg) for a in expr.args)
        kw_map = (
            {a.name: self._maybe_copy_struct(a.value) for a in expr.args if isinstance(a, KeywordArg)}
            if all_kw
            else {}
        )

        def positional_from_kwargs(type_name: str) -> str | None:
            fields = self.struct_field_types.get(type_name)
            if fields:
                return ", ".join(kw_map[f] for f in fields if f in kw_map)
            # Class/entity: keep source keyword order
            return ", ".join(kw_map.values())

        if all_kw:
            arg_s = "{ " + ", ".join(f"{k}: {v}" for k, v in kw_map.items()) + " }"
        else:
            args: list[str] = []
            for a in expr.args:
                if isinstance(a, KeywordArg):
                    args.append(self._maybe_copy_struct(a.value))
                else:
                    args.append(self._maybe_copy_struct(a))
            arg_s = ", ".join(args)

        if isinstance(expr.callee, Member):
            method = expr.callee.name
            recv_obj = expr.callee.object
            # TraitName.method(this, …) → this._TraitName_method(…)
            if (
                isinstance(recv_obj, Identifier)
                and recv_obj.name in self.trait_defs
            ):
                mangled = f"_{recv_obj.name}_{method}"
                args_list = list(expr.args)
                if (
                    args_list
                    and isinstance(args_list[0], Identifier)
                    and args_list[0].name in ("self", "this")
                ):
                    rest = ", ".join(
                        self._maybe_copy_struct(a) for a in args_list[1:]
                    )
                    return f"this.{mangled}({rest})" if rest else f"this.{mangled}()"
                joined = ", ".join(self._maybe_copy_struct(a) for a in args_list)
                return f"{mangled}({joined})"
            recv = self._expr(recv_obj)
            if (
                isinstance(recv_obj, Identifier)
                and recv_obj.name in self.atomic_vars
                and method in {"get", "compareAndSet"}
            ):
                raw = recv_obj.name
                return f"{raw}.{method}({arg_s})"
            if method == "append":
                return f"{recv}.push({arg_s})"
            if method == "pop":
                if arg_s:
                    return f"_pys_dict_pop({recv}, {arg_s})"
                return f"{recv}.pop()"
            if method == "loop" and len(expr.args) == 1:
                return f"{recv}.map({self._expr(expr.args[0])})"
            str_map = {
                "upper": "toUpperCase",
                "lower": "toLowerCase",
                "strip": "trim",
                "startswith": "startsWith",
                "endswith": "endsWith",
                "find": "indexOf",
            }
            if method in str_map and not arg_s:
                return f"{recv}.{str_map[method]}()"
            if method in str_map:
                return f"{recv}.{str_map[method]}({arg_s})"
            # Namespace constructors: ng.QMainWindow(), tk.Tk(), …
            if method and method[0].isupper():
                return f"new {recv}.{method}({arg_s})"
            return f"{recv}.{method}({arg_s})"

        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            if (
                name in self.class_names
                or name in self.data_names
                or name in self.struct_names
                or name in self.entity_names
            ):
                if all_kw:
                    arg_s = positional_from_kwargs(name) or arg_s
                return f"new {name}({arg_s})"
            if name == "len":
                return f"({arg_s}).length"
            if name == "dict" and not arg_s:
                return "{}"
            if name == "list" and not arg_s:
                return "[]"
            if name == "set" and not arg_s:
                return "new Set()"
            if name == "str":
                return f"_pys_format({arg_s})"
            if name == "int":
                return f"(Math.trunc(Number({arg_s})))"
            if name == "float":
                return f"Number({arg_s})"
            if name == "bool":
                return f"Boolean({arg_s})"
            if name == "ok":
                return f"_pys_ok({arg_s})" if arg_s else "_pys_ok()"
            if name == "error":
                return f"_pys_error({arg_s})"
            if name in ("parseFloat", "parseInt"):
                helper = (
                    "_pys_parse_float"
                    if name == "parseFloat"
                    else "_pys_parse_int"
                )
                return f"{helper}({arg_s})"
            if name in ("toBin", "toHex", "toOct"):
                helper = {
                    "toBin": "_pys_to_bin",
                    "toHex": "_pys_to_hex",
                    "toOct": "_pys_to_oct",
                }[name]
                return f"{helper}({arg_s})"
            if name == "panic":
                return f"_pys_panic({arg_s})"
            if name == "_pys_keep_alive":
                return f"_pys_keep_alive({arg_s})"
            return f"{name}({arg_s})"
        return f"{self._expr(expr.callee)}({arg_s})"

    def _binop(self, expr: BinaryOp) -> str:
        op = expr.op
        if op in ("and", "&&"):
            op = "&&"
        elif op in ("or", "||"):
            op = "||"
        elif op == "//":
            return f"Math.floor({self._expr(expr.left)} / {self._expr(expr.right)})"
        elif op == "+":
            left = self._expr(expr.left)
            right = self._expr(expr.right)
            if (
                self._infer_kind(expr.left) == "string"
                or self._infer_kind(expr.right) == "string"
            ):
                return f"String({left}) + String({right})"
            # list/array concat (PYS `a + b` on lists) — avoid JS string coercion
            if self._infer_kind(expr.left) == "array" or self._infer_kind(
                expr.right
            ) == "array" or isinstance(expr.left, (ArrayLiteral, BraceLiteral, TupleLiteral)) or isinstance(
                expr.right, (ArrayLiteral, BraceLiteral, TupleLiteral)
            ):
                return f"[].concat({left}, {right})"
            return f"{left} + {right}"
        elif op in ("==", "!="):
            left = self._expr(expr.left)
            right = self._expr(expr.right)
            eq = f"_pys_value_eq({left}, {right})"
            return f"!({eq})" if op == "!=" else eq
        left = self._expr(expr.left)
        right = self._expr(expr.right)
        return f"({left} {op} {right})"

    def _cast(self, expr: Cast) -> str:
        inner = self._expr(expr.expr)
        t = expr.type_name
        if t in ("int", "byte", "nibble", "int16", "int32", "int64", "dword"):
            return f"Math.trunc(Number({inner}))"
        if t == "float":
            return f"Number({inner})"
        if t in ("string", "char"):
            return f"String({inner})"
        if t == "bool":
            return f"Boolean({inner})"
        return inner

    def _literal(self, lit: Literal) -> str:
        if lit.kind == "bool":
            return "true" if lit.text == "true" else "false"
        if lit.kind == "null":
            return "null"
        return lit.text

    def _infer_kind(self, expr: Expr | None) -> str:
        if expr is None:
            return "number"
        if isinstance(expr, Literal):
            if expr.kind in ("string", "char"):
                return "string"
            return "number"
        if isinstance(expr, InterpolatedString):
            return "string"
        if isinstance(expr, Identifier):
            return self.var_kinds.get(expr.name, "number")
        if isinstance(expr, BinaryOp) and expr.op == "+":
            if (
                self._infer_kind(expr.left) == "string"
                or self._infer_kind(expr.right) == "string"
            ):
                return "string"
        return "number"

    def _js_default(self, type_name: str) -> str:
        return {
            "int": "0",
            "float": "0.0",
            "char": "''",
            "string": "''",
            "bool": "false",
            "byte": "0",
            "nibble": "0",
            "int16": "0",
            "int32": "0",
            "int64": "0",
            "dword": "0",
        }.get(type_name or "", "null")


JS_RUNTIME_PREAMBLE = """\
function _pys_format(value) {
  if (value === null || value === undefined) return "null";
  if (value instanceof Set) return JSON.stringify([...value]);
  if (Array.isArray(value)) return JSON.stringify(value);
  if (typeof value === "object" && value._pys_result_kind) {
    return value._pys_result_kind + "(" + _pys_format(value.value) + ")";
  }
  if (typeof value === "boolean") return value ? "True" : "False";
  return String(value);
}
function _pys_slice(obj, start, stop, step) {
  const s = start == null ? 0 : start;
  const exclusive = stop == null ? undefined : (stop + 1);
  const st = step == null ? 1 : step;
  if (st === 1) {
    if (typeof obj === "string") {
      return obj.substring(s, exclusive === undefined ? obj.length : exclusive);
    }
    return obj.slice(s, exclusive);
  }
  const out = [];
  const end = exclusive === undefined ? obj.length : exclusive;
  if (st > 0) {
    for (let i = s; i < end; i += st) out.push(obj[i]);
  } else if (st < 0) {
    const from = start == null ? obj.length - 1 : start;
    const to = stop == null ? -1 : stop;
    for (let i = from; i > to; i += st) out.push(obj[i]);
  }
  return typeof obj === "string" ? out.join("") : out;
}
class _PysResult {
  constructor(kind, value, sites) {
    this._pys_result_kind = kind;
    this.value = value;
    this.sites = sites ? [...sites] : [];
  }
}
function _pys_ok(value) { return new _PysResult("ok", value === undefined ? null : value); }
function _pys_error(value) { return new _PysResult("error", value); }
function _pys_propagate(result, file, line, functionName) {
  if (result && result._pys_result_kind === "ok") return result.value;
  if (!result || result._pys_result_kind !== "error") {
    throw new TypeError("propagate expected a PYS result value");
  }
  const sites = [...(result.sites || []), [file, line, functionName]];
  const err = new Error("PYS propagate");
  err._pys_propagate = true;
  err.result = new _PysResult("error", result.value, sites);
  throw err;
}
function _pys_eq_tuple(a, b) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (!_pys_value_eq(a[i], b[i])) return false;
  return true;
}
function _pys_hash_tuple(parts) {
  let h = 0;
  for (const p of parts) {
    const s = String(p);
    for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return h;
}
function _pys_enum_member(name, value) {
  return Object.freeze({ name, value });
}
function print(value) {
  console.log(_pys_format(value));
}
function _pys_iter(obj) {
  if (obj == null) return [];
  if (typeof obj[Symbol.iterator] === "function") return obj;
  return Object.keys(obj);
}
function _pys_dict_pop(obj, key) {
  const v = obj[key];
  delete obj[key];
  return v;
}
function _pys_keep_alive(value) {
  globalThis.__pys_keep = globalThis.__pys_keep || [];
  globalThis.__pys_keep.push(value);
  return value;
}
function _pys_parse_float(text) {
  const n = Number(String(text).trim());
  if (Number.isNaN(n)) return _pys_error("invalid float");
  return _pys_ok(n);
}
function _pys_parse_int(text) {
  const n = parseInt(String(text).trim(), 10);
  if (Number.isNaN(n)) return _pys_error("invalid int");
  return _pys_ok(n);
}
""" + JS_VALUE_HELPERS + JS_CONCURRENCY_PREAMBLE

