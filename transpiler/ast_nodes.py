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
    """Compilation unit. `source` retained for transitional Python emit parity."""

    source: str = ""
    body: list[Any] = field(default_factory=list)
    brace_mode: bool = False


@dataclass
class OpaqueStmt(Node):
    """Statement region not yet lowered to structured AST."""

    text: str = ""


@dataclass
class Expr(Node):
    pass


@dataclass
class Identifier(Expr):
    name: str = ""


@dataclass
class Literal(Expr):
    kind: str = ""  # int|float|string|char|bool|null
    text: str = ""


@dataclass
class PrintStmt(Node):
    value: Expr | None = None
    raw: str = ""
