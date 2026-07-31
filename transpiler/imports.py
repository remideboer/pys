"""`.pys` import resolution / visibility (shared by sem + emit).

Resolution still uses the legacy module loader for now; call sites go through
this module instead of constructing `Parser` directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def make_resolver(source: str, source_path: Path) -> Any:
    from .transpiler import Parser

    return Parser(source, source_path=source_path, enforce_formatting=False)


def translate_import(resolver: Any, line: str, line_number: int = 1) -> str | None:
    return resolver._translate_import_statement(line, line_number, line)
