"""Foreach binder type required + must match iterable element type (CER-054)."""
from __future__ import annotations

import pytest

from transpiler.parse import FatalParseError
from transpiler.transpiler import TranspileError, transpile


def test_foreach_requires_binder_type() -> None:
    src = """
int[] arr = {1, 2}
loop (x in arr) {
    print(x)
}
"""
    with pytest.raises((FatalParseError, TranspileError), match=r"requires a type|foreach"):
        transpile(src)


def test_foreach_wrong_element_type_is_type_mismatch() -> None:
    src = """
int[] arr = {3, 4, 5, 6}
loop (string x in arr) {
    print(x)
}
"""
    with pytest.raises(TranspileError, match=r"Type mismatch.*string.*int"):
        transpile(src)


def test_foreach_matching_array_element_type_ok() -> None:
    py = transpile(
        """
int[] arr = {3, 4}
loop (int x in arr) {
    print(x)
}
"""
    )
    assert "for " in py
    assert "print(" in py


def test_foreach_matching_list_element_type_ok() -> None:
    py = transpile(
        """
list<string> xs = ["a", "b"]
loop (string x in xs) {
    print(x)
}
"""
    )
    assert "for " in py


def test_foreach_list_wrong_element_type_denied() -> None:
    src = """
list<int> xs = [1, 2]
loop (string x in xs) {
    print(x)
}
"""
    with pytest.raises(TranspileError, match=r"Type mismatch.*string.*int"):
        transpile(src)


def test_rekenmachine_foreach_negative_wrong_type() -> None:
    from pathlib import Path

    base = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "rekenmachine.pys"
    text = base.read_text(encoding="utf-8")
    # Uncomment the documented wrong-type negative.
    bad = text.replace(
        "# loop (string x in arr) { print(x) }",
        "loop (string x in arr) { print(x) }",
    )
    # Drop the positive typed loop so only the mismatch remains as executable.
    bad = bad.replace(
        "loop (int x in arr) {\n    print(x)\n}\n",
        "",
    )
    with pytest.raises(TranspileError, match=r"Type mismatch|string.*int"):
        transpile(bad)
