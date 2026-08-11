"""Whole-file PYS AST pretty-printer (brace mode).

Formats already-parsed modules into canonical layout. Does not repair illegal
kind order or tabs (those fail lex/parse before format — CER-062).
"""
from __future__ import annotations

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
    EnumMember,
    Expr,
    ExprStmt,
    FieldDecl,
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
    OpaqueStmt,
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
    StructField,
    SwitchCase,
    SwitchExpr,
    SwitchStmt,
    TaskDef,
    TasksBlock,
    TraitDef,
    TraitRequire,
    TraitUse,
    TupleLiteral,
    UnaryOp,
    WhileStmt,
)

LINE_LIMIT = 100
INDENT = "    "


def format_source(source: str) -> str | None:
    """Parse and format brace-mode source. Returns None if parse fails or not brace mode."""
    from .parse import FatalParseError, parse_program

    try:
        module = parse_program(source)
    except (FatalParseError, SyntaxError, ValueError):
        return None
    if not module.brace_mode:
        return None
    return format_module(module)


def format_module(module: Module) -> str:
    printer = _Printer(module)
    text = printer.print_module()
    return _finalize(text)


def _finalize(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        stripped = line.rstrip(" \t")
        if stripped == "":
            blank_run += 1
            if blank_run <= 1:
                cleaned.append("")
            continue
        blank_run = 0
        cleaned.append(stripped)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned) + "\n"


class _Printer:
    def __init__(self, module: Module) -> None:
        self.module = module
        self._depth = 0

    def indent(self) -> str:
        return INDENT * self._depth

    def print_module(self) -> str:
        imports: list[ImportStmt] = []
        rest: list[Any] = []
        for node in self.module.body:
            if isinstance(node, ImportStmt):
                imports.append(node)
            else:
                rest.append(node)
        parts: list[str] = []
        for imp in imports:
            parts.append(self.print_import(imp))
        if imports and rest:
            parts.append("")
        prev_emitted = False
        for node in rest:
            if isinstance(node, BlankStmt):
                continue
            chunk = self.print_top(node)
            if chunk is None:
                continue
            if prev_emitted and not isinstance(node, CommentStmt):
                if parts and parts[-1] != "":
                    parts.append("")
            parts.append(chunk)
            prev_emitted = True
        return "\n".join(parts)

    def print_top(self, node: Any) -> str | None:
        if isinstance(node, BlankStmt):
            # Formatter owns blank layout (Java-style); do not echo source blanks.
            return None
        if isinstance(node, CommentStmt):
            return self.print_comment(node)
        if isinstance(node, ImportStmt):
            return self.print_import(node)
        if isinstance(node, FunctionDef):
            return self.print_function(node)
        if isinstance(node, ClassDef):
            return self.print_class(node)
        if isinstance(node, StructDef):
            return self.print_struct(node)
        if isinstance(node, DataDef):
            return self.print_data(node)
        if isinstance(node, EntityDef):
            return self.print_entity(node)
        if isinstance(node, EnumDef):
            return self.print_enum(node)
        if isinstance(node, InterfaceDef):
            return self.print_interface(node)
        if isinstance(node, TraitDef):
            return self.print_trait(node)
        if isinstance(node, TasksBlock):
            return self.print_tasks(node)
        if isinstance(node, AssignStmt):
            return self.print_assign(node)
        if isinstance(node, SharedDecl):
            return self.print_shared(node)
        if isinstance(node, AtomicDecl):
            return self.print_atomic(node)
        if isinstance(node, ArrayDecl):
            return self.print_array_decl(node)
        if isinstance(node, OpaqueStmt):
            return node.text.rstrip()
        if isinstance(node, ExprStmt):
            return self.print_expr_stmt(node)
        # Fall back to original source slice when possible
        sliced = self._slice_original(node)
        if sliced is not None:
            return sliced
        return None

    def print_comment(self, node: CommentStmt) -> str:
        text = (node.text or "").rstrip()
        if text.startswith("##"):
            return text
        if not text.startswith("#"):
            return f"# {text}"
        return text

    def print_import(self, node: ImportStmt) -> str:
        if node.kind == "module":
            return f"import {node.module}"
        if node.kind == "as":
            return f"import {node.module} as {node.alias}"
        if node.kind == "all_from":
            return f"import all from {node.module}"
        names = node.names or ([node.name] if node.name else [])
        return f"import {', '.join(names)} from {node.module}"

    def _vis(self, visibility: str) -> str:
        return f"{visibility} " if visibility else ""

    def _access(self, access: str) -> str:
        return f"{access} " if access else ""

    def _params(self, params: list[str], param_types: list[str]) -> str:
        bits: list[str] = []
        for i, name in enumerate(params):
            ty = param_types[i] if i < len(param_types) else ""
            bits.append(f"{ty} {name}".strip() if ty else name)
        joined = ", ".join(bits)
        if len(joined) > LINE_LIMIT - 20:
            inner = ",\n".join(f"{INDENT}{b}" for b in bits)
            return f"(\n{inner},\n)"
        return f"({joined})"

    def _extension(self, ext: str | None) -> str:
        if not ext:
            return ""
        if ext == "override_closed":
            return "override closed "
        return f"{ext} "

    def print_function(self, node: FunctionDef) -> str:
        lines: list[str] = []
        for deco in node.decorators:
            lines.append(f"@{self.print_expr(deco)}")
        ret = f"{node.return_type} " if node.return_type else ""
        header = (
            f"{self._vis(node.visibility)}function {ret}{node.name}"
            f"{self._params(node.params, node.param_types)} {{"
        )
        lines.append(header)
        lines.append(self.print_block_body(node.body))
        lines.append("}")
        return "\n".join(lines)

    def print_block_body(self, block: Block | None) -> str:
        if block is None:
            return ""
        self._depth += 1
        try:
            parts: list[str] = []
            i = 0
            stmts = list(block.statements)
            while i < len(stmts):
                stmt = stmts[i]
                if isinstance(stmt, BlankStmt):
                    i += 1
                    continue
                chunk = self.print_stmt(stmt)
                if chunk is None:
                    i += 1
                    continue
                # Skip pure-empty chunks (do not invent blanks inside blocks).
                if chunk == "":
                    i += 1
                    continue
                for line in chunk.split("\n"):
                    parts.append(f"{self.indent()}{line}" if line else "")
                i += 1
            return "\n".join(parts)
        finally:
            self._depth -= 1

    def print_block(self, block: Block | None) -> str:
        body = self.print_block_body(block)
        if body:
            return "{\n" + body + "\n" + self.indent() + "}"
        return "{}"

    def print_class(self, node: ClassDef) -> str:
        lines: list[str] = []
        for deco in node.decorators:
            lines.append(f"@{self.print_expr(deco)}")
        head = self._vis(node.visibility)
        if node.closed or node.sealed:
            head += "closed "
        if node.abstract:
            head += "abstract "
        head += f"class {node.name}"
        if node.type_params:
            head += "<" + ", ".join(node.type_params) + ">"
        if node.parent:
            head += f" inherits {node.parent}"
        if node.uses:
            uses = ", ".join(self._trait_use(u) for u in node.uses)
            head += f" uses {uses}"
        if node.bases:
            head += " implements " + ", ".join(node.bases)
        head += " {"
        lines.append(head)
        body_lines = self._class_like_members(node.fields, node.methods, entity_identity=None)
        if body_lines:
            lines.extend(body_lines)
        lines.append("}")
        return "\n".join(lines)

    def _trait_use(self, use: TraitUse) -> str:
        if not use.remaps:
            return use.name
        remaps = ", ".join(f"{a}: {b}" for a, b in use.remaps)
        return f"{use.name}({remaps})"

    def _class_like_members(
        self,
        fields: list[FieldDecl],
        methods: list[MethodDef],
        *,
        entity_identity: set[str] | None,
    ) -> list[str]:
        consts: list[FieldDecl] = []
        fixes: list[FieldDecl] = []
        mutables: list[FieldDecl] = []
        identity_fields: list[FieldDecl] = []
        for f in fields:
            if entity_identity is not None and f.name in entity_identity:
                identity_fields.append(f)
            elif f.is_const:
                consts.append(f)
            elif f.is_fix:
                fixes.append(f)
            else:
                mutables.append(f)
        ctors = [m for m in methods if m.is_constructor]
        meths = [m for m in methods if not m.is_constructor]
        ordered: list[Any] = []
        if entity_identity is not None:
            ordered.extend(identity_fields)
            ordered.extend(fixes)
        else:
            ordered.extend(consts)
            ordered.extend(fixes)
        ordered.extend(mutables)
        ordered.extend(ctors)
        ordered.extend(meths)

        self._depth += 1
        try:
            out: list[str] = []
            prev_kind = None
            for member in ordered:
                kind = self._member_kind(member, entity_identity)
                if isinstance(member, MethodDef):
                    # Blank line before each method/ctor (and after fields).
                    if out and out[-1] != "":
                        out.append("")
                elif prev_kind is not None and kind != prev_kind and out and out[-1] != "":
                    out.append("")
                prev_kind = kind
                if isinstance(member, FieldDecl):
                    text = self.print_field(member)
                else:
                    # Method text is column-relative; class indent applied below.
                    text = self.print_method(member, relative=True)
                for line in text.split("\n"):
                    out.append(f"{self.indent()}{line}" if line else "")
            return out
        finally:
            self._depth -= 1

    def _member_kind(self, member: Any, entity_identity: set[str] | None) -> str:
        if isinstance(member, FieldDecl):
            if entity_identity is not None and member.name in entity_identity:
                return "identity"
            if member.is_const:
                return "const"
            if member.is_fix:
                return "fix"
            return "field"
        if isinstance(member, MethodDef) and member.is_constructor:
            return "ctor"
        return "method"

    def print_field(self, node: FieldDecl) -> str:
        bits: list[str] = []
        if node.access:
            bits.append(node.access)
        if node.is_static:
            bits.append("static")
        if node.is_const:
            bits.append("const")
        elif node.is_fix:
            bits.append("fix")
        bits.append(node.type_name)
        bits.append(node.name)
        line = " ".join(bits)
        if node.default is not None:
            line += f" = {self.print_expr(node.default)}"
        return line

    def print_method(self, node: MethodDef, *, relative: bool = False) -> str:
        saved = self._depth
        if relative:
            self._depth = 0
        try:
            lines: list[str] = []
            for deco in node.decorators:
                lines.append(f"@{self.print_expr(deco)}")
            bits: list[str] = []
            if node.access:
                bits.append(node.access)
            if node.is_static:
                bits.append("static")
            if node.is_abstract:
                bits.append("abstract")
            ext = self._extension(node.extension)
            if ext:
                bits.append(ext.strip())
            if node.is_constructor:
                bits.append("constructor")
                name_and_params = self._params(node.params, node.param_types)
                header = " ".join(bits) + name_and_params
            else:
                if node.return_type:
                    bits.append(node.return_type)
                bits.append(node.name)
                header = " ".join(bits) + self._params(node.params, node.param_types)
            if node.is_abstract and node.body is None:
                lines.append(header)
                return "\n".join(lines)
            lines.append(header + " {")
            body = self.print_block_body(node.body)
            if body:
                lines.append(body)
            lines.append("}")
            return "\n".join(lines)
        finally:
            self._depth = saved

    def print_struct(self, node: StructDef) -> str:
        head = self._vis(node.visibility)
        if node.type_fix:
            head += "fix "
        head += f"struct {node.name}"
        if node.type_params:
            head += "<" + ", ".join(node.type_params) + ">"
        head += " {"
        lines = [head]
        fixes = [f for f in node.fields if f.is_fix]
        muts = [f for f in node.fields if not f.is_fix]
        self._depth += 1
        try:
            for i, f in enumerate(fixes + muts):
                if i == len(fixes) and fixes and muts:
                    lines.append("")
                lines.append(f"{self.indent()}{self.print_struct_field(f)}")
        finally:
            self._depth -= 1
        lines.append("}")
        return "\n".join(lines)

    def print_struct_field(self, node: StructField) -> str:
        bits: list[str] = []
        if node.is_fix:
            bits.append("fix")
        bits.append(node.type_name)
        bits.append(node.name)
        line = " ".join(bits)
        if node.default is not None:
            line += f" = {self.print_expr(node.default)}"
        return line

    def print_data(self, node: DataDef) -> str:
        head = f"{self._vis(node.visibility)}data {node.name} {{"
        lines = [head]
        self._depth += 1
        try:
            for f in node.fields:
                lines.append(f"{self.indent()}{self.print_struct_field(f)}")
        finally:
            self._depth -= 1
        lines.append("}")
        return "\n".join(lines)

    def print_entity(self, node: EntityDef) -> str:
        head = f"{self._vis(node.visibility)}entity {node.name}"
        if node.parent:
            head += f" inherits {node.parent}"
        if node.identity:
            head += " identity(" + ", ".join(node.identity) + ")"
        head += " {"
        lines = [head]
        lines.extend(
            self._class_like_members(
                node.fields, node.methods, entity_identity=set(node.identity)
            )
        )
        lines.append("}")
        return "\n".join(lines)

    def print_enum(self, node: EnumDef) -> str:
        head = f"{self._vis(node.visibility)}enum {node.name}"
        members = node.members
        if self._enum_fits_one_line(node.name, members):
            inner = ", ".join(self._enum_member(m) for m in members)
            return f"{head} {{ {inner} }}"
        lines = [head + " {"]
        self._depth += 1
        try:
            for m in members:
                lines.append(f"{self.indent()}{self._enum_member(m)},")
        finally:
            self._depth -= 1
        lines.append("}")
        return "\n".join(lines)

    def _enum_member(self, m: EnumMember) -> str:
        if m.value is None:
            return m.name
        return f"{m.name} = {self.print_expr(m.value)}"

    def _enum_fits_one_line(self, name: str, members: list[EnumMember]) -> bool:
        if len(members) > 4:
            return False
        inner = ", ".join(self._enum_member(m) for m in members)
        return len(f"enum {name} {{ {inner} }}") <= LINE_LIMIT

    def print_interface(self, node: InterfaceDef) -> str:
        # AST drops return types/params; prefer original source when available.
        sliced = self._slice_original(node)
        if sliced is not None:
            return self._reindent_top_chunk(sliced)
        head = f"{self._vis(node.visibility)}interface {node.name} {{"
        lines = [head]
        self._depth += 1
        try:
            for name in node.methods:
                arity = node.method_arities.get(name, 0)
                params = ", ".join(f"arg{i}" for i in range(arity))
                lines.append(f"{self.indent()}{name}({params})")
        finally:
            self._depth -= 1
        lines.append("}")
        return "\n".join(lines)

    def print_trait(self, node: TraitDef) -> str:
        head = f"{self._vis(node.visibility)}trait {node.name} {{"
        lines = [head]
        self._depth += 1
        try:
            if node.requires:
                for req in node.requires:
                    lines.append(f"{self.indent()}{self.print_require(req)}")
                if node.methods:
                    lines.append("")
            for i, m in enumerate(node.methods):
                if i > 0 or node.requires:
                    if lines and lines[-1] != "":
                        lines.append("")
                text = self.print_method(m, relative=True)
                for line in text.split("\n"):
                    lines.append(f"{self.indent()}{line}" if line else "")
        finally:
            self._depth -= 1
        lines.append("}")
        return "\n".join(lines)

    def print_require(self, req: TraitRequire) -> str:
        if req.kind == "method":
            return (
                f"requires {req.type_name} {req.name}"
                f"{self._params(req.params, req.param_types)}".replace(" ()", "()")
                if req.type_name
                else f"requires {req.name}{self._params(req.params, req.param_types)}"
            )
        if req.type_name:
            return f"requires {req.type_name} {req.name}"
        return f"requires {req.name}"

    def print_tasks(self, node: TasksBlock) -> str:
        lines = ["tasks {"]
        self._depth += 1
        try:
            for t in node.tasks:
                text = self.print_task(t)
                for line in text.split("\n"):
                    lines.append(f"{self.indent()}{line}" if line else "")
        finally:
            self._depth -= 1
        lines.append("}")
        return "\n".join(lines)

    def print_task(self, node: TaskDef) -> str:
        name = f" {node.name}" if node.name else ""
        lines = [f"task{name} {{"]
        body = self.print_block_body(node.body)
        if body:
            lines.append(body)
        lines.append("}")
        return "\n".join(lines)

    def print_stmt(self, node: Any) -> str | None:
        if isinstance(node, BlankStmt):
            return None
        if isinstance(node, CommentStmt):
            return self.print_comment(node)
        if isinstance(node, AssignStmt):
            return self.print_assign(node)
        if isinstance(node, AugAssignStmt):
            return self.print_aug(node)
        if isinstance(node, ReturnStmt):
            return "return" if node.value is None else f"return {self.print_expr(node.value)}"
        if isinstance(node, PassStmt):
            return "pass"
        if isinstance(node, BreakStmt):
            return "break"
        if isinstance(node, ContinueStmt):
            return "continue"
        if isinstance(node, PrintStmt):
            return f"print({self.print_expr(node.value)})" if node.value else "print()"
        if isinstance(node, IfStmt):
            return self.print_if(node)
        if isinstance(node, WhileStmt):
            return self.print_while(node)
        if isinstance(node, ForRangeStmt):
            return self.print_for_range(node)
        if isinstance(node, ForEachStmt):
            return self.print_foreach(node)
        if isinstance(node, RepeatStmt):
            return self.print_repeat(node)
        if isinstance(node, SwitchStmt):
            return self.print_switch(node)
        if isinstance(node, SharedDecl):
            return self.print_shared(node)
        if isinstance(node, AtomicDecl):
            return self.print_atomic(node)
        if isinstance(node, ArrayDecl):
            return self.print_array_decl(node)
        if isinstance(node, ExprStmt):
            return self.print_expr_stmt(node)
        if isinstance(node, OpaqueStmt):
            return node.text.rstrip()
        if isinstance(node, Block):
            # nested block rare
            return self.print_block(node)
        sliced = self._slice_original(node)
        return sliced

    def print_assign(self, node: AssignStmt) -> str:
        bits: list[str] = []
        if node.visibility:
            bits.append(node.visibility)
        if node.declare_type == "var":
            bits.append("var")
        elif node.declare_type == "const" or node.is_const:
            bits.append("const")
        elif node.declare_type == "fix" or node.is_fix:
            bits.append("fix")
        elif node.declare_type:
            if node.is_const:
                bits.append("const")
            elif node.is_fix:
                bits.append("fix")
            bits.append(node.declare_type)
        bits.append(node.name)
        left = " ".join(bits)
        if node.value is None:
            return left
        return f"{left} = {self.print_expr(node.value)}"

    def print_aug(self, node: AugAssignStmt) -> str:
        if node.op in {"++", "--"}:
            return f"{node.name}{node.op}"
        return f"{node.name} {node.op} {self.print_expr(node.value)}"

    def print_if(self, node: IfStmt) -> str:
        neg = "not " if node.negated else ""
        lines = [f"if {neg}({self.print_expr(node.cond)}) {{"]
        body = self.print_block_body(node.then_body)
        if body:
            lines.append(body)
        lines.append("}")
        if node.else_body is not None:
            # else if chain: Block with single IfStmt
            stmts = node.else_body.statements if node.else_body else []
            if len(stmts) == 1 and isinstance(stmts[0], IfStmt):
                nested = self.print_if(stmts[0])
                first, *rest = nested.split("\n")
                lines.append(f"else {first}")
                lines.extend(rest)
            else:
                lines.append("else {")
                eb = self.print_block_body(node.else_body)
                if eb:
                    lines.append(eb)
                lines.append("}")
        return "\n".join(lines)

    def print_while(self, node: WhileStmt) -> str:
        lines = [f"while ({self.print_expr(node.cond)}) {{"]
        body = self.print_block_body(node.body)
        if body:
            lines.append(body)
        lines.append("}")
        return "\n".join(lines)

    def print_for_range(self, node: ForRangeStmt) -> str:
        header = self._for_range_header(node)
        lines = [f"{header} {{"]
        body = self.print_block_body(node.body)
        if body:
            lines.append(body)
        lines.append("}")
        return "\n".join(lines)

    def _for_range_header(self, node: ForRangeStmt) -> str:
        sliced = self._slice_header_line(node)
        if sliced and "for" in sliced:
            return sliced.rstrip().rstrip("{").rstrip()
        name = node.var or "i"
        start = self.print_expr(node.start) if node.start else "0"
        stop = self.print_expr(node.stop) if node.stop else "0"
        return f"for (int {name} = {start}; {name} < {stop}; {name}++)"

    def print_foreach(self, node: ForEachStmt) -> str:
        iterable = self.print_expr(node.iterable) if node.iterable else ""
        if node.var_type:
            header = f"loop ({node.var_type} {node.var} in {iterable})"
        else:
            header = f"loop ({node.var} in {iterable})"
        sliced = self._slice_header_line(node)
        if sliced and ("loop" in sliced or "for" in sliced):
            header = sliced.rstrip().rstrip("{").rstrip()
        lines = [f"{header} {{"]
        body = self.print_block_body(node.body)
        if body:
            lines.append(body)
        lines.append("}")
        return "\n".join(lines)

    def print_repeat(self, node: RepeatStmt) -> str:
        lines = [f"repeat {self.print_expr(node.count)} times {{"]
        body = self.print_block_body(node.body)
        if body:
            lines.append(body)
        lines.append("}")
        return "\n".join(lines)

    def print_switch(self, node: SwitchStmt) -> str:
        lines = [f"switch ({self.print_expr(node.subject)}) {{"]
        self._depth += 1
        try:
            for case in node.cases:
                text = self.print_case(case)
                for line in text.split("\n"):
                    lines.append(f"{self.indent()}{line}" if line else "")
        finally:
            self._depth -= 1
        lines.append("}")
        return "\n".join(lines)

    def print_case(self, case: SwitchCase) -> str:
        if case.is_default:
            head = "default"
        else:
            labels = ", ".join(self.print_expr(x) for x in case.labels)
            head = f"case {labels}"
        if case.value is not None and case.body is None:
            return f"{head} => {self.print_expr(case.value)}"
        body = self.print_block_body(case.body) if case.body else ""
        if body:
            return f"{head} {{\n{body}\n{self.indent()}}}"
        return f"{head} {{}}"

    def print_shared(self, node: SharedDecl) -> str:
        ty = f"{node.declare_type} " if node.declare_type else ""
        return f"shared {ty}{node.name} = {self.print_expr(node.value)}"

    def print_atomic(self, node: AtomicDecl) -> str:
        ty = f"{node.declare_type} " if node.declare_type else ""
        return f"atomic {ty}{node.name} = {self.print_expr(node.value)}"

    def print_array_decl(self, node: ArrayDecl) -> str:
        brackets = "[]" * max(1, node.rank())
        left = f"{node.elem_type}{brackets} {node.name}"
        if node.value is None:
            return left
        return f"{left} = {self.print_expr(node.value)}"

    def print_expr_stmt(self, node: ExprStmt) -> str:
        if node.expr is None:
            return ""
        return self.print_expr(node.expr)

    def print_expr(self, expr: Expr | None) -> str:
        if expr is None:
            return ""
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, Literal):
            return expr.text
        if isinstance(expr, BinaryOp):
            return f"{self.print_expr(expr.left)} {expr.op} {self.print_expr(expr.right)}"
        if isinstance(expr, UnaryOp):
            op = expr.op
            if op in {"not", "-"}:
                return f"{op} {self.print_expr(expr.operand)}".replace("not  ", "not ")
            return f"{op}{self.print_expr(expr.operand)}"
        if isinstance(expr, Call):
            args = ", ".join(self.print_expr(a) for a in expr.args)
            return f"{self.print_expr(expr.callee)}({args})"
        if isinstance(expr, KeywordArg):
            return f"{expr.name}={self.print_expr(expr.value)}"
        if isinstance(expr, Member):
            return f"{self.print_expr(expr.object)}.{expr.name}"
        if isinstance(expr, Index):
            return f"{self.print_expr(expr.object)}[{self.print_expr(expr.index)}]"
        if isinstance(expr, Slice):
            a = self.print_expr(expr.start) if expr.start else ""
            b = self.print_expr(expr.end) if expr.end else ""
            return f"{self.print_expr(expr.object)}[{a}:{b}]"
        if isinstance(expr, Cast):
            return f"({expr.type_name}){self.print_expr(expr.value)}"
        if isinstance(expr, InterpolatedString):
            return expr.raw or '""'
        if isinstance(expr, ArrayLiteral):
            return "[" + ", ".join(self.print_expr(x) for x in expr.elements) + "]"
        if isinstance(expr, BraceLiteral):
            return "{" + ", ".join(self.print_expr(x) for x in expr.elements) + "}"
        if isinstance(expr, DictLiteral):
            pairs = ", ".join(
                f"{self.print_expr(k)}: {self.print_expr(v)}" for k, v in expr.entries
            )
            return "{" + pairs + "}"
        if isinstance(expr, SetLiteral):
            return "{" + ", ".join(self.print_expr(x) for x in expr.elements) + "}"
        if isinstance(expr, TupleLiteral):
            els = ", ".join(self.print_expr(x) for x in expr.elements)
            if len(expr.elements) == 1:
                els += ","
            return f"({els})"
        if isinstance(expr, ArrayAlloc):
            dims = "][".join("" if d is None else str(d) for d in expr.dims) or ""
            return f"{expr.elem_type}[{dims}]"
        if isinstance(expr, LambdaExpr):
            return self._print_lambda(expr)
        if isinstance(expr, ResultCtor):
            if expr.value is None:
                return f"{expr.kind}()"
            return f"{expr.kind}({self.print_expr(expr.value)})"
        if isinstance(expr, PropagateExpr):
            return f"{self.print_expr(expr.operand)} propagate"
        if isinstance(expr, ResultPattern):
            if expr.binding:
                return f"{expr.kind}({expr.binding})"
            return f"{expr.kind}()"
        if isinstance(expr, AwaitExpr):
            return f"await {self.print_expr(expr.target)}"
        if isinstance(expr, SwitchExpr):
            return self._print_switch_expr(expr)
        return "<?>"

    def _print_lambda(self, expr: LambdaExpr) -> str:
        types = expr.param_types or [""] * len(expr.params)
        params = ", ".join(
            f"{t} {n}".strip() if t else n for n, t in zip(expr.params, types)
        )
        if isinstance(expr.body, Block):
            return f"({params}) => {self.print_block(expr.body)}"
        return f"({params}) => {self.print_expr(expr.body)}"  # type: ignore[arg-type]

    def _print_switch_expr(self, expr: SwitchExpr) -> str:
        sliced = self._slice_original(expr)
        if sliced:
            return sliced
        return f"switch ({self.print_expr(expr.subject)}) {{}}"

    def _slice_header_line(self, node: Any) -> str | None:
        if not self.module.source or not getattr(node, "span", None) or not node.span:
            return None
        lines = self.module.source.replace("\r\n", "\n").split("\n")
        idx = node.span.line - 1
        if 0 <= idx < len(lines):
            return lines[idx]
        return None

    def _slice_original(self, node: Any) -> str | None:
        """Best-effort original text for nodes we cannot round-trip."""
        if not self.module.source or not getattr(node, "span", None) or not node.span:
            return None
        lines = self.module.source.replace("\r\n", "\n").split("\n")
        start = node.span.line - 1
        if start < 0 or start >= len(lines):
            return None
        end_line = node.span.end_line
        if end_line is not None:
            end = end_line - 1
            chunk = "\n".join(lines[start : end + 1])
            return chunk.rstrip()
        # Brace-match from start line
        text = "\n".join(lines[start:])
        depth = 0
        seen = False
        out_chars: list[str] = []
        for ch in text:
            out_chars.append(ch)
            if ch == "{":
                depth += 1
                seen = True
            elif ch == "}":
                depth -= 1
                if seen and depth == 0:
                    break
        if not seen:
            return lines[start].rstrip()
        return "".join(out_chars).rstrip()

    def _reindent_top_chunk(self, chunk: str) -> str:
        # Normalize indentation of a sliced top-level chunk to 4-space grid
        raw_lines = chunk.replace("\r\n", "\n").split("\n")
        if not raw_lines:
            return chunk
        # Compute min indent of non-empty lines after first
        indents = []
        for i, line in enumerate(raw_lines):
            if i == 0 or not line.strip():
                continue
            indents.append(len(line) - len(line.lstrip(" ")))
        base = min(indents) if indents else 0
        out = [raw_lines[0].rstrip()]
        for line in raw_lines[1:]:
            if not line.strip():
                out.append("")
                continue
            stripped = line.lstrip(" ")
            cur = len(line) - len(stripped)
            level = max(0, (cur - base + 3) // 4) if base else max(0, (cur + 3) // 4)
            # Prefer relative to opening of chunk
            rel = max(0, cur - base)
            spaces = " " * rel
            # Snap to 4
            snapped = (rel // 4) * 4
            out.append((" " * snapped) + stripped.rstrip())
        return "\n".join(out)
