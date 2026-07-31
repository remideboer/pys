"""Python emitter for PYS AST.

Lex/parse build a real Module AST. Python text emit still goes through the
quarantined legacy Parser for exact parity while structured lowering grows.
When `emit` walks AST nodes directly, prefer matching characterization goldens
before removing `_legacy_emit`.
"""
from __future__ import annotations

from pathlib import Path

from ..ast_nodes import Module


def emit(module: Module, *, source_path: Path | None = None) -> str:
    return _legacy_emit(module.source, source_path=source_path)


def _legacy_emit(source: str, *, source_path: Path | None = None) -> str:
    from ..transpiler import Parser

    return Parser(source, source_path=source_path).parse()
