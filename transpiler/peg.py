"""Packrat (PEG) brace-mode entry — PEP 617-inspired, pure Python.

Lexer stays in ``lex.py`` (same split as CPython tokenizer vs pegen). Productions
and grammar actions live in ``parse.py``; this module turns on per-parse packrat
memoization so a ``(rule, position)`` is never expanded twice.
"""
from __future__ import annotations

from .ast_nodes import Module
from .lex import Token
from .parse import _parse_brace_module_rd


def parse_brace_module(
    tokens: list[Token],
    *,
    source: str = "",
    brace_mode: bool = True,
) -> Module:
    """Parse a non-indent token stream with packrat memoization enabled."""
    return _parse_brace_module_rd(
        tokens, source=source, brace_mode=brace_mode, packrat=True
    )
