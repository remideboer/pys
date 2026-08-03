"""Enforced member / import ordering (requirements/enforced_ordering.md)."""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_import_after_declaration_is_parse_error() -> None:
    src = "int x = 1\nimport math\n"
    with pytest.raises(TranspileError, match="Import statement found after other code"):
        transpile(src)


def test_imports_then_code_ok() -> None:
    src = "import math\nint x = 1\nprint(x)\n"
    out = transpile(src)
    assert "math" in out


def test_consecutive_name_from_imports_ok() -> None:
    """Back-to-back `import Name from mod` must not be misread as Python from-import."""
    from transpiler.parse import parse_program

    mod = parse_program(
        "import shout from toolbox\nimport MAX_LABEL_LEN from toolbox\nint x = 1\n"
    )
    imports = [s for s in mod.body if getattr(s, "kind", None) in {"name_from", "module", "all_from", "as"}]
    assert len(imports) == 2
    assert imports[0].kind == "name_from" and imports[0].name == "shout"
    assert imports[1].kind == "name_from" and imports[1].name == "MAX_LABEL_LEN"


def test_blank_and_comment_before_import_ok() -> None:
    src = "# header\n\nimport math\nint x = 1\n"
    transpile(src)


def test_struct_fix_after_mutable_errors() -> None:
    src = """
struct Point {
    int x
    fix int y
}
"""
    with pytest.raises(TranspileError, match="Fix field 'y' found after mutable"):
        transpile(src)


def test_struct_fix_then_mutable_ok() -> None:
    src = """
struct Point {
    fix int id
    int x
}
Point p = Point(1, 2)
print(p.x)
"""
    transpile(src)


def test_trait_requires_after_method_errors() -> None:
    src = """
trait Printer {
    print() {
        print(this.label)
    }
    requires string label
}
"""
    with pytest.raises(TranspileError, match="found before trait Printer's 'requires'"):
        transpile(src)


def test_trait_requires_then_method_ok() -> None:
    src = """
trait Printer {
    requires string label
    print() {
        print(this.label)
    }
}
package class Tag uses Printer {
    public string label
    public Tag(string label) {
        this.label = label
    }
}
"""
    transpile(src)


def test_class_method_before_field_errors() -> None:
    src = """
package class Box {
    public open() {
        print(1)
    }
    private int n
}
"""
    # Violation surfaces on the late field (optional field section already passed).
    with pytest.raises(TranspileError, match="Field 'n' found after a constructor"):
        transpile(src)


def test_class_field_after_ctor_errors() -> None:
    src = """
package class Box {
    public Box() {
    }
    private int n
}
"""
    with pytest.raises(TranspileError, match="Field 'n' found after a constructor"):
        transpile(src)


def test_class_const_after_mutable_errors() -> None:
    src = """
package class Box {
    private int n
    public const int MAX = 10
}
"""
    with pytest.raises(TranspileError, match="Constant 'MAX' found after non-const"):
        transpile(src)


def test_class_ordered_const_fix_field_ctor_method_ok() -> None:
    src = """
package class Box {
    public const int MAX = 10
    private fix int id
    private int n
    public Box(int id, int n) {
        this.id = id
        this.n = n
    }
    public int get() {
        return this.n
    }
}
Box b = Box(1, 2)
print(b.get())
"""
    transpile(src)


def test_entity_mutable_before_identity_errors() -> None:
    src = """
entity Customer identity(customerId) {
    public string name
    private fix int customerId
    public Customer(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}
"""
    with pytest.raises(TranspileError, match="found before identity field"):
        transpile(src)


def test_entity_identity_first_ok() -> None:
    src = """
entity Customer identity(customerId) {
    private fix int customerId
    public string name
    public Customer(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}
Customer c = Customer(1, "Ada")
print(c.name)
"""
    transpile(src)
