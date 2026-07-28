import pytest

from transpiler.transpiler import TranspileError, transpile


def test_transpile_error_message_includes_line_number() -> None:
    source = """var x 1
print hello
"""
    with pytest.raises(TranspileError, match=r"line 1"):
        transpile(source)


def test_var_rejects_type_change() -> None:
    source = """var z = 30
z = "adad"
"""
    with pytest.raises(TranspileError, match=r"Type mismatch: cannot assign string to 'z' of type int"):
        transpile(source)


def test_var_allows_same_type_reassignment() -> None:
    source = """var z = 30
z = 40
print(z)
"""
    assert "z = 40" in transpile(source)


def test_let_is_rejected_in_favor_of_var() -> None:
    source = """let z = 30
"""
    with pytest.raises(TranspileError, match=r"Use `var` instead of `let`"):
        transpile(source)


def test_explicit_type_rejects_wrong_assignment() -> None:
    source = """int x = 10
x = "nope"
"""
    with pytest.raises(TranspileError, match=r"Type mismatch: cannot assign string to 'x' of type int"):
        transpile(source)
