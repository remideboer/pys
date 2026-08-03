"""Compile PYS source through lex → parse → sem → emit[target]."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from . import parse as parse_mod
from . import sem as sem_mod
from .emit import python as emit_python

Target = Literal["python"]


def compile_pys(
    source: str,
    *,
    target: Target = "python",
    source_path: Path | None = None,
    allow_runtime_introspection: bool = False,
) -> str:
    """Compile PYS to the requested backend. Only `python` is implemented."""
    text, _maps, _names = compile_pys_with_map(
        source,
        target=target,
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    return text


def compile_pys_with_map(
    source: str,
    *,
    target: Target = "python",
    source_path: Path | None = None,
    allow_runtime_introspection: bool = False,
) -> tuple[str, list[dict[str, int]], dict[str, str]]:
    """Compile PYS and return ``(python_text, line_map, debug_names)``.

    ``line_map`` entries are ``{"py": int, "pys": int}`` (1-based).
    ``debug_names`` maps emitted locals → PYS display names.
    """
    if target != "python":
        raise ValueError(f"Unsupported emit target {target!r}; only 'python' is available.")
    # parse_program lexes first, so invalid tokens still fail before any emit.
    tree = parse_mod.parse_program(source)
    tree = sem_mod.analyze(
        tree,
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    if os.environ.get("PYS_SUPPRESS_WARNINGS", "").strip() not in {"1", "true", "yes"}:
        for warn in getattr(tree, "analysis_warnings", []) or []:
            print(str(warn), file=sys.stderr)
    return emit_python.emit_with_map(tree, source_path=source_path)
