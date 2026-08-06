"""Builtin input(): no import required; returns string."""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_input_without_import_transpiles_and_returns_string() -> None:
    py = transpile(
        'string name = input("What is your name? ")\nprint(name)\n'
    )
    assert "input(" in py
    assert "import" not in py.split("input(")[0] or "builtins" not in py


def test_input_zero_arg_allowed() -> None:
    py = transpile("string line = input()\nprint(line)\n")
    assert "input()" in py


def test_input_legacy_import_still_compiles() -> None:
    py = transpile(
        "import input from builtins\n"
        'string name = input("x")\n'
        "print(name)\n"
    )
    assert "input(" in py


def test_input_rejects_two_args() -> None:
    with pytest.raises(TranspileError):
        transpile('string s = input("a", "b")\n')
