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
    # Filled by sem.analyze — non-fatal diagnostics (not part of parse).
    analysis_warnings: list[Any] = field(default_factory=list)


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
class ResultCtor(Expr):
    """Built-in ``ok(value)`` or ``err(error)`` result constructor."""

    kind: str = ""
    value: Expr | None = None


@dataclass
class PropagateExpr(Expr):
    """Postfix ``expr propagate`` early-returning result unwrap."""

    operand: Expr | None = None


@dataclass
class ResultPattern(Expr):
    """Result switch pattern: ``ok(value)``, ``ok()``, or ``err(error)``."""

    kind: str = ""
    binding: str = ""
    binding_span: Span | None = None


@dataclass
class KeywordArg(Expr):
    """Named argument in a call: `host="localhost"`."""

    name: str = ""
    value: Expr | None = None


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
    """Bracket list literal ``[a, b]`` (and nested ``[[…]]``)."""

    elements: list[Expr] = field(default_factory=list)


@dataclass
class BraceLiteral(Expr):
    """Unresolved ``{…}`` without ``key: value`` pairs; resolved by expected type."""

    elements: list[Expr] = field(default_factory=list)


@dataclass
class DictLiteral(Expr):
    """Keyed brace literal ``{k: v, …}``."""

    entries: list[tuple[Expr, Expr]] = field(default_factory=list)


@dataclass
class SetLiteral(Expr):
    """Resolved set literal (usually after type-directed brace resolution)."""

    elements: list[Expr] = field(default_factory=list)


@dataclass
class TupleLiteral(Expr):
    """Parenthesized tuple ``(a, b)``, ``(a,)``, or ``()``."""

    elements: list[Expr] = field(default_factory=list)


@dataclass
class ArrayAlloc(Expr):
    """Allocate a (possibly multi-dimensional) array: ``int[3][][]``, ``int[2][3]``."""

    elem_type: str = ""
    dims: list[int | None] = field(default_factory=list)


@dataclass
class LambdaExpr(Expr):
    """Anonymous function: `(params) => expr|{…}` or `n => expr`."""

    params: list[str] = field(default_factory=list)
    param_types: list[str] = field(default_factory=list)
    body: Expr | Block | None = None


@dataclass
class CommentStmt(Node):
    """Standalone `# ...` line preserved in Python output."""

    text: str = ""


@dataclass
class BlankStmt(Node):
    """Blank line preserved after a closing `}` (legacy preprocess)."""

    pass


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
    visibility: str = ""  # global|package|module for top-level const/fix exports
    name_span: Span | None = None


@dataclass
class ArrayDecl(Node):
    elem_type: str = ""
    name: str = ""
    size: int | None = None  # unused on decls (sized types rejected); kept for compat
    dims: list[int | None] = field(default_factory=list)  # rank ≥ 1; all None on decls
    value: Expr | None = None
    name_span: Span | None = None

    def rank(self) -> int:
        if self.dims:
            return len(self.dims)
        return 1


@dataclass
class AugAssignStmt(Node):
    name: str = ""
    op: str = ""  # += etc or ++/--
    value: Expr | None = None
    name_span: Span | None = None


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
class SwitchCase(Node):
    """One arm of a switch statement or expression."""

    labels: list[Expr] = field(default_factory=list)  # empty when is_default
    is_default: bool = False
    body: Block | None = None  # statement form
    value: Expr | None = None  # expression form (`=> expr`)
    fallthrough: bool = False  # statement arm ends with switch-continue
    brace_scoped: bool = False  # statement arm body was an explicit `{ }` block


@dataclass
class SwitchStmt(Node):
    subject: Expr | None = None
    cases: list[SwitchCase] = field(default_factory=list)


@dataclass
class SwitchExpr(Expr):
    subject: Expr | None = None
    cases: list[SwitchCase] = field(default_factory=list)


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
    name_span: Span | None = None


@dataclass
class ForEachStmt(Node):
    var: str = ""
    var_type: str = ""
    iterable: Expr | None = None
    body: Block | None = None
    name_span: Span | None = None


@dataclass
class RepeatStmt(Node):
    """Legacy `repeat N times:` → `for _ in range(N):`."""

    count: Expr | None = None
    body: Block | None = None


@dataclass
class SharedDecl(Node):
    name: str = ""
    value: Expr | None = None
    declare_type: str = ""
    name_span: Span | None = None


@dataclass
class AtomicDecl(Node):
    """`atomic int x = 0` — implies shared for capture; indivisible RMW ops."""

    name: str = ""
    value: Expr | None = None
    declare_type: str = ""
    name_span: Span | None = None


@dataclass
class AwaitExpr(Expr):
    """`await name` or `await name(args)`."""

    target: Expr | None = None


@dataclass
class TaskDef(Node):
    name: str = ""  # handle, including `_anon_N`
    params: list[str] = field(default_factory=list)
    is_template: bool = False
    body: Block | None = None


@dataclass
class TasksBlock(Node):
    group_id: int = 0
    tasks: list[TaskDef] = field(default_factory=list)


@dataclass
class ImportStmt(Node):
    kind: str = ""  # module|as|all_from|name_from
    module: str = ""
    name: str = ""  # first / sole name for name_from (compat)
    names: list[str] = field(default_factory=list)  # all names for name_from
    alias: str = ""


@dataclass
class FunctionDef(Node):
    name: str = ""
    params: list[str] = field(default_factory=list)
    param_types: list[str] = field(default_factory=list)
    body: Block | None = None
    visibility: str = ""
    return_type: str = ""
    name_span: Span | None = None


@dataclass
class FieldDecl(Node):
    access: str = ""
    type_name: str = ""
    name: str = ""
    is_fix: bool = False
    is_const: bool = False
    default: Expr | None = None
    name_span: Span | None = None


@dataclass
class StructField(Node):
    access: str = "public"  # fields are always public; kept for metadata symmetry
    type_name: str = ""
    name: str = ""
    is_fix: bool = False
    default: Expr | None = None
    name_span: Span | None = None


@dataclass
class StructDef(Node):
    """Identity-free value type (fields only; canonical constructor)."""

    name: str = ""
    fields: list[StructField] = field(default_factory=list)
    visibility: str = ""
    type_params: list[str] = field(default_factory=list)
    type_fix: bool = False  # leading `fix struct`
    name_span: Span | None = None


@dataclass
class DataDef(Node):
    """Immutable value object: structural equality over all fields."""

    name: str = ""
    fields: list[StructField] = field(default_factory=list)
    visibility: str = ""
    name_span: Span | None = None


@dataclass
class EntityDef(Node):
    """Identity-keyed type: equality over identity(...) fields only."""

    name: str = ""
    parent: str = ""
    identity: list[str] = field(default_factory=list)  # local identity clause fields
    fields: list[FieldDecl] = field(default_factory=list)
    methods: list[MethodDef] = field(default_factory=list)
    visibility: str = ""
    name_span: Span | None = None


@dataclass
class EnumMember(Node):
    name: str = ""
    value: Expr | None = None  # Literal int/string when explicit
    name_span: Span | None = None


@dataclass
class EnumDef(Node):
    """Nominal closed set of named constants (identity-style members)."""

    name: str = ""
    members: list[EnumMember] = field(default_factory=list)
    visibility: str = ""
    name_span: Span | None = None


@dataclass
class MethodDef(Node):
    access: str = ""
    name: str = ""
    params: list[str] = field(default_factory=list)  # without self
    param_types: list[str] = field(default_factory=list)
    body: Block | None = None
    is_constructor: bool = False
    is_abstract: bool = False
    return_type: str = ""
    name_span: Span | None = None


@dataclass
class ClassDef(Node):
    name: str = ""
    bases: list[str] = field(default_factory=list)
    parent: str = ""  # superclass from `inherits` / header `super` (not interfaces)
    uses: list[str] = field(default_factory=list)  # trait names (composition, not bases)
    fields: list[FieldDecl] = field(default_factory=list)
    methods: list[MethodDef] = field(default_factory=list)
    visibility: str = ""
    sealed: bool = False
    abstract: bool = False
    name_span: Span | None = None


@dataclass
class InterfaceDef(Node):
    name: str = ""
    methods: list[str] = field(default_factory=list)  # method names
    method_arities: dict[str, int] = field(default_factory=dict)
    visibility: str = ""
    name_span: Span | None = None


@dataclass
class TraitRequire(Node):
    """Host obligation declared by a trait (`requires …`)."""

    kind: str = "field"  # "field" | "method"
    type_name: str = ""  # field type or method return type
    name: str = ""
    params: list[str] = field(default_factory=list)
    param_types: list[str] = field(default_factory=list)


@dataclass
class TraitDef(Node):
    """Composable behavior: methods + requires; not a nominal type."""

    name: str = ""
    requires: list[TraitRequire] = field(default_factory=list)
    methods: list[MethodDef] = field(default_factory=list)
    visibility: str = ""


@dataclass
class ExprStmt(Node):
    expr: Expr | None = None
