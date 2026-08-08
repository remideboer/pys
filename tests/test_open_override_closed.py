"""ADR-028: open / override / closed + closed class + implicit root."""
from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def _ok(source: str) -> str:
    return transpile(source)


def test_open_override_polymorphic() -> None:
    py = _ok(
        """
class Animal {
    public constructor() {}
    public open string speak() { return "..." }
}
class Dog inherits Animal {
    public constructor() { super() }
    public override string speak() { return "woof" }
}
Dog d = Dog()
Animal a = d
print(a.speak())
"""
    )
    assert "def speak(self)" in py
    assert "woof" in py


def test_missing_override_is_error() -> None:
    with pytest.raises(TranspileError, match="override|hides"):
        _ok(
            """
class Animal {
    public constructor() {}
    public open string speak() { return "..." }
}
class Dog inherits Animal {
    public constructor() { super() }
    public string speak() { return "woof" }
}
"""
        )


def test_override_without_open_is_error() -> None:
    with pytest.raises(TranspileError, match="open|not an open socket|override"):
        _ok(
            """
class Animal {
    public constructor() {}
    public string speak() { return "..." }
}
class Dog inherits Animal {
    public constructor() { super() }
    public override string speak() { return "woof" }
}
"""
        )


def test_closed_class_rejects_inherit() -> None:
    with pytest.raises(TranspileError, match="cannot inherit from closed class"):
        _ok(
            """
closed class Foo {
    public constructor() {}
}
class Bar inherits Foo {
    public constructor() { super() }
}
"""
        )


def test_sealed_keyword_rejected() -> None:
    with pytest.raises(Exception, match="closed"):
        _ok(
            """
sealed class Foo {
    public constructor() {}
}
"""
        )


def test_override_closed_blocks_further() -> None:
    with pytest.raises(TranspileError, match="open socket|override closed|cannot override"):
        _ok(
            """
class A {
    public constructor() {}
    public open string f() { return "a" }
}
class B inherits A {
    public constructor() { super() }
    public override closed string f() { return "b" }
}
class C inherits B {
    public constructor() { super() }
    public override string f() { return "c" }
}
"""
        )


def test_private_open_rejected() -> None:
    with pytest.raises(TranspileError, match="private"):
        _ok(
            """
class A {
    public constructor() {}
    private open string f() { return "x" }
}
"""
        )


def test_open_in_closed_class_rejected() -> None:
    with pytest.raises(TranspileError, match="closed"):
        _ok(
            """
closed class A {
    public constructor() {}
    public open string f() { return "x" }
}
"""
        )


def test_abstract_impl_needs_override() -> None:
    with pytest.raises(TranspileError, match="override"):
        _ok(
            """
abstract class A {
    public constructor() {}
    public abstract string name()
}
class B inherits A {
    public constructor() { super() }
    public string name() { return "b" }
}
"""
        )


def test_root_tostring_needs_override() -> None:
    py = _ok(
        """
class A {
    public constructor() {}
    public override string toString() { return "A" }
}
"""
    )
    assert "def toString(self)" in py


def test_standalone_closed_allowed() -> None:
    py = _ok(
        """
class A {
    public constructor() {}
    public closed string tag() { return "a" }
}
"""
    )
    assert "def tag(self)" in py
