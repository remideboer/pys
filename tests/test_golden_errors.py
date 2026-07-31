"""Selected error characterizations for migration parity."""
from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_tabs_illegal() -> None:
    with pytest.raises(TranspileError, match="[Tt]abs"):
        transpile("int x = 1\n\tprint(x)\n")


def test_let_rejected() -> None:
    with pytest.raises(TranspileError, match="var"):
        transpile("let z = 1\n")


def test_type_mismatch_assign() -> None:
    with pytest.raises(TranspileError, match="Type mismatch"):
        transpile('int x = 1\nx = "no"\n')


def test_return_requires_type() -> None:
    with pytest.raises(TranspileError, match="return type"):
        transpile(
            """
global function bad() {
    return 1
}
"""
        )


def test_await_cycle_rejected() -> None:
    with pytest.raises(TranspileError, match="cycle|await"):
        transpile(
            """
tasks {
    task a() {
        await b()
    }
    task b() {
        await a()
    }
}
"""
        )
