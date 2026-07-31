"""PYS AST node types (target-neutral). Spans are 1-based line/column."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Span:
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None


@dataclass
class Node:
    span: Span | None = None


@dataclass
class Module(Node):
    source: str = ""
    body: list[Any] = field(default_factory=list)
    brace_mode: bool = False
    use_legacy: bool = False


@dataclass
class OpaqueStmt(Node):
    text: str = ""


@dataclass
class Expr(Node):
    pass


@dataclass
class Identifier(Expr):
    name: str = ""


@dataclass
class Literal(Expr):
    kind: str = ""
    text: str = ""


@dataclass
class BinaryOp(Expr):
    op: str = ""
    left: Expr | None = None
    right: Expr | None = None


@dataclass
class UnaryOp(Expr):
    op: str = ""
    operand: Expr | None = None


@dataclass
class Call(Expr):
    callee: Expr | None = None
    args: list[Expr] = field(default_factory=list)


@dataclass
class Member(Expr):
    object: Expr | None = None
    name: str = ""


@dataclass
class Index(Expr):
    object: Expr | None = None
    index: Expr | None = None


@dataclass
class Slice(Expr):
    object: Expr | None = None
    start: Expr | None = None
    stop: Expr | None = None
    step: Expr | None = None


@dataclass
class Cast(Expr):
    type_name: str = ""
    expr: Expr | None = None


@dataclass
class InterpolatedString(Expr):
    """String with {expr} / #t{expr} parts; `raw` is original PYS literal text."""

    raw: str = ""


@dataclass
class ArrayLiteral(Expr):
    elements: list[Expr] = field(default_factory=list)


@dataclass
class PrintStmt(Node):
    value: Expr | None = None
    raw: str = ""


@dataclass
class AssignStmt(Node):
    name: str = ""
    value: Expr | None = None
    declare_type: str | None = None  # int/float/... or "var"/"const"/"fix"
    is_const: bool = False
    is_fix: bool = False


@dataclass
class ArrayDecl(Node):
    elem_type: str = ""
    name: str = ""
    size: int | None = None
    value: Expr | None = None


@dataclass
class AugAssignStmt(Node):
    name: str = ""
    op: str = ""  # += etc or ++/--
    value: Expr | None = None


@dataclass
class ReturnStmt(Node):
    value: Expr | None = None


@dataclass
class PassStmt(Node):
    pass


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


@dataclass
class Block(Node):
    statements: list[Any] = field(default_factory=list)


@dataclass
class IfStmt(Node):
    cond: Expr | None = None
    then_body: Block | None = None
    else_body: Block | None = None  # may be IfStmt for else-if chain
    negated: bool = False  # if not / unless


@dataclass
class WhileStmt(Node):
    cond: Expr | None = None
    body: Block | None = None


@dataclass
class ForRangeStmt(Node):
    var: str = ""
    start: Expr | None = None
    stop: Expr | None = None
    body: Block | None = None


@dataclass
class ForEachStmt(Node):
    var: str = ""
    iterable: Expr | None = None
    body: Block | None = None


@dataclass
class ImportStmt(Node):
    kind: str = ""  # module|as|all_from|name_from
    module: str = ""
    name: str = ""
    alias: str = ""


@dataclass
class FunctionDef(Node):
    name: str = ""
    params: list[str] = field(default_factory=list)
    body: Block | None = None
    visibility: str = ""


@dataclass
class FieldDecl(Node):
    access: str = ""
    type_name: str = ""
    name: str = ""


@dataclass
class MethodDef(Node):
    access: str = ""
    name: str = ""
    params: list[str] = field(default_factory=list)  # without self
    param_types: list[str] = field(default_factory=list)
    body: Block | None = None
    is_constructor: bool = False
    return_type: str = ""


@dataclass
class ClassDef(Node):
    name: str = ""
    bases: list[str] = field(default_factory=list)
    fields: list[FieldDecl] = field(default_factory=list)
    methods: list[MethodDef] = field(default_factory=list)
    visibility: str = ""
    sealed: bool = False


@dataclass
class InterfaceDef(Node):
    name: str = ""
    methods: list[str] = field(default_factory=list)  # method names
    visibility: str = ""


@dataclass
class ExprStmt(Node):
    expr: Expr | None = None
