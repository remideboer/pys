"""Recursive-descent parser: tokens → AST (brace + legacy).

Builds a Module root. Top-level `print(...)` forms become PrintStmt; remaining
regions stay OpaqueStmt. Full structured coverage grows behind golden tests.
"""
from __future__ import annotations

import re

from .ast_nodes import Identifier, Literal, Module, OpaqueStmt, PrintStmt, Span
from .lex import LexError, TokenKind, tokenize


class ParseError(ValueError):
    def __init__(self, message: str, line: int = 1, column: int = 1) -> None:
        self.line = line
        self.column = column
        super().__init__(f"{message} (line {line}, column {column})")


_PRINT_LINE = re.compile(
    r"^print\s*(?:\((.*)\)|(.+))\s*$",
    re.DOTALL,
)


def parse_program(source: str) -> Module:
    """Parse a full PYS compilation unit."""
    try:
        tokens = tokenize(source)
    except LexError as exc:
        raise ParseError(str(exc.message), exc.line, exc.column) from exc

    brace_mode = any(t.kind in {TokenKind.LBRACE, TokenKind.RBRACE} for t in tokens)
    if brace_mode:
        depth = 0
        for t in tokens:
            if t.kind == TokenKind.LBRACE:
                depth += 1
            elif t.kind == TokenKind.RBRACE:
                depth -= 1
                if depth < 0:
                    raise ParseError("Unexpected closing brace.", t.line, t.column)
        if depth != 0:
            raise ParseError("Unclosed block at end of file.", tokens[-1].line, tokens[-1].column)

    body: list = []
    # Line-oriented structuring for brace-free simple prints; otherwise one opaque.
    if not brace_mode and source.strip():
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            m = _PRINT_LINE.match(stripped)
            if m:
                inner = (m.group(1) if m.group(1) is not None else m.group(2) or "").strip()
                value = _expr_from_text(inner, line_no)
                body.append(PrintStmt(span=Span(line_no, 1), value=value, raw=stripped))
            else:
                body.append(OpaqueStmt(span=Span(line_no, 1), text=line))
    elif source.strip():
        body.append(OpaqueStmt(span=Span(1, 1), text=source))

    return Module(span=Span(1, 1), source=source, body=body, brace_mode=brace_mode)


def _expr_from_text(text: str, line: int):
    if not text:
        return Literal(span=Span(line, 1), kind="null", text="null")
    if text in {"true", "false"}:
        return Literal(span=Span(line, 1), kind="bool", text=text)
    if text == "null":
        return Literal(span=Span(line, 1), kind="null", text=text)
    if re.fullmatch(r"\d+", text):
        return Literal(span=Span(line, 1), kind="int", text=text)
    if re.fullmatch(r"\d+\.\d+", text):
        return Literal(span=Span(line, 1), kind="float", text=text)
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        kind = "char" if text.startswith("'") and len(text) == 3 else "string"
        return Literal(span=Span(line, 1), kind=kind, text=text)
    if re.fullmatch(r"[A-Za-z_]\w*", text):
        return Identifier(span=Span(line, 1), name=text)
    return Identifier(span=Span(line, 1), name=text)
