"""ADR-027: explicit constructor keyword."""

from __future__ import annotations

import ast

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_constructor_emits_init() -> None:
    py = transpile(
        """
class Person {
    private string name

    public constructor(string name) {
        this.name = name
    }

    public string label() {
        return this.name
    }
}
"""
    )
    ast.parse(py)
    assert "def __init__(self, name" in py
    assert "self.name = name" in py


def test_class_name_ctor_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
class Foo {
    public Foo() {
    }
}
"""
        )
    assert ei.value.code == "pys.constructor-keyword"


def test_this_chaining_emits_self_init() -> None:
    py = transpile(
        """
class Box {
    private int n

    public constructor() {
        this(0)
    }

    public constructor(int n) {
        this.n = n
    }
}
"""
    )
    ast.parse(py)
    assert "self.__init__(0)" in py
    assert "self(0)" not in py


def test_implicit_super_still_injected() -> None:
    py = transpile(
        """
class Car {
    public constructor() {
    }
}

class Truck inherits Car {
    public constructor() {
    }
}
"""
    )
    ast.parse(py)
    assert "super().__init__()" in py


def test_entity_constructor() -> None:
    py = transpile(
        """
entity Product identity(productId) {
    protected fix int productId
    public string sku

    public constructor(int productId, string sku) {
        this.productId = productId
        this.sku = sku
    }
}
"""
    )
    ast.parse(py)
    assert "def __init__(self, productId" in py
    assert "sku" in py.split("def __init__")[1].split("\n")[0]
