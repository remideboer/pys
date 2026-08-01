"""Compile PYS source through lex → parse → sem → emit[target]."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from . import parse as parse_mod
from . import sem as sem_mod
from .emit import python as emit_python
from .lex import LexError, tokenize

Target = Literal["python"]


def compile_pys(
    source: str,
    *,
    target: Target = "python",
    source_path: Path | None = None,
    allow_runtime_introspection: bool = False,
) -> str:
    """Compile PYS to the requested backend. Only `python` is implemented."""
    if target != "python":
        raise ValueError(f"Unsupported emit target {target!r}; only 'python' is available.")
    # Lex early so invalid tokens fail before legacy emit.
    try:
        tokenize(source)
    except LexError as exc:
        from .transpiler import TranspileError

        raise TranspileError(str(exc.message), exc.line, exc.column, "") from exc

    tree = parse_mod.parse_program(source)
    tree = sem_mod.analyze(
        tree,
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    return emit_python.emit(tree, source_path=source_path)
