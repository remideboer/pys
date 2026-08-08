"""ADR-029 / CER-047: class static fields and methods."""

from __future__ import annotations

import ast

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_static_field_and_method_emit() -> None:
    py = transpile(
        """
class Counter {
    public static int total = 0

    public constructor() {
        Counter.total = Counter.total + 1
    }

    public static int getTotal() {
        return Counter.total
    }
}

print(Counter.getTotal())
"""
    )
    ast.parse(py)
    assert "total = 0" in py
    assert "@staticmethod" in py
    assert "def getTotal():" in py
    assert "def getTotal(self" not in py


def test_static_const_allowed() -> None:
    py = transpile(
        """
class Mathish {
    public static const int MAX = 100

    public static int clamp(int n) {
        if (n > Mathish.MAX) {
            return Mathish.MAX
        }
        return n
    }
}
"""
    )
    ast.parse(py)
    assert "MAX = 100" in py
    assert "@staticmethod" in py


def test_static_this_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
class Box {
    private int n

    public constructor(int n) {
        this.n = n
    }

    public static int bad() {
        return this.n
    }
}
"""
        )
    assert ei.value.code == "pys.static-this"
    assert "static method" in str(ei.value)
    assert "Processes, threads, and memory" in str(ei.value)


def test_static_open_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
class A {
    public static open int f() {
        return 1
    }
}
"""
        )
    assert ei.value.code == "pys.static-extension"


def test_static_override_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
class Base {
    public open int f() {
        return 1
    }
}

class Sub inherits Base {
    public static override int f() {
        return 2
    }
}
"""
        )
    assert ei.value.code == "pys.static-extension"


def test_static_constructor_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
class A {
    public static constructor() {
    }
}
"""
        )
    assert ei.value.code == "pys.static-ctor"


def test_static_abstract_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
abstract class A {
    public static abstract int f()
}
"""
        )
    assert ei.value.code == "pys.static-abstract"
