"""Brace `{ }` scopes: locals (including loop binders) do not leak."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile_with_modules


def test_foreach_binder_does_not_leak_to_outer_declaration(tmp_path: Path) -> None:
    """After `loop (T x in …) { }`, outer `int x = …` is a fresh binding."""
    src = tmp_path / "loop_scope.pys"
    src.write_text(
        "list<int> xs = [1, 2]\n"
        "loop (int x in xs) {\n"
        "    print(x)\n"
        "}\n"
        "int x = 10\n"
        "print(x)\n",
        encoding="utf-8",
    )
    py = transpile_with_modules(src)["loop_scope"]
    assert "for x in" not in py
    assert "x = 10" in py
    assert "print(_pys_format(x))" in py


def test_foreach_binder_not_visible_after_loop(tmp_path: Path) -> None:
    src = tmp_path / "use_after.pys"
    src.write_text(
        "list<int> xs = [1]\n"
        "loop (int x in xs) {\n"
        "    print(x)\n"
        "}\n"
        "x = 1\n",
        encoding="utf-8",
    )
    with pytest.raises(TranspileError, match="Undeclared variable 'x'"):
        transpile_with_modules(src)


def test_block_local_decl_in_if_does_not_leak(tmp_path: Path) -> None:
    src = tmp_path / "if_scope.pys"
    src.write_text(
        "if (true) {\n"
        "    int y = 1\n"
        "    print(y)\n"
        "}\n"
        "int y = 2\n"
        "print(y)\n",
        encoding="utf-8",
    )
    py = transpile_with_modules(src)["if_scope"]
    assert "y = 2" in py
    assert "_pys_" in py
    assert re.search(r"(?m)^\s*y = 1\s*$", py) is None
    assert re.search(r"(?m)^\s*_pys_\w+_y = 1\s*$", py) is not None
