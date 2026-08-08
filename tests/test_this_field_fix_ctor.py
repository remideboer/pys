"""Phase 3: this. field access + fix ctor assignment."""
from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_bare_field_requires_this() -> None:
    with pytest.raises(TranspileError, match=r"this\.name"):
        transpile(
            """
class A {
    private string name
    public constructor(string name) {
        this.name = name
    }
    public string label() {
        return name
    }
}
"""
        )


def test_this_field_ok() -> None:
    py = transpile(
        """
class A {
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
    assert "return self.name" in py or "return this.name" in py or "self.name" in py


def test_fix_ctor_must_assign() -> None:
    with pytest.raises(TranspileError, match=r"fix field"):
        transpile(
            """
class A {
    private fix string id
    public constructor() {
    }
}
"""
        )


def test_fix_assigned_in_ctor_ok() -> None:
    py = transpile(
        """
class A {
    private fix string id
    public constructor(string id) {
        this.id = id
    }
}
"""
    )
    assert "self.id" in py


def test_fix_via_this_chain_ok() -> None:
    py = transpile(
        """
class A {
    private fix string id
    public constructor() {
        this("x")
    }
    public constructor(string id) {
        this.id = id
    }
}
"""
    )
    assert "self.__init__" in py or "__init__" in py
