"""Collection literals: dict / set / tuple and type-directed braces."""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_tuple_literal_multi_emits_python_tuple() -> None:
    """Given tuple row = (1, \"Ada\"), when transpile, then Python tuple RHS."""
    py = transpile('tuple<int, string> row = (1, "Ada")\nprint(row[0])\n')
    assert 'row = (1, "Ada")' in py
    assert "print(row[0])" in py


def test_tuple_literal_singleton_needs_trailing_comma() -> None:
    py = transpile("tuple<int> one = (42,)\n")
    assert "one = (42,)" in py


def test_tuple_literal_empty() -> None:
    py = transpile("tuple empty = ()\n")
    assert "empty = ()" in py


def test_paren_grouping_still_works() -> None:
    py = transpile("int x = (1 + 2) * 3\n")
    assert "x =" in py


def test_dict_empty_brace_emits_dict() -> None:
    """Given dict ages = {}, when transpile, then RHS is {} not []."""
    py = transpile("dict<string, int> ages = {}\nages[\"Ada\"] = 36\n")
    assert "ages = {}" in py
    assert "ages = []" not in py
    assert 'ages["Ada"] = 36' in py


def test_dict_keyed_literal() -> None:
    py = transpile('dict<string, int> ages = {"Ada": 36, "Tom": 41}\n')
    assert 'ages = {"Ada": 36, "Tom": 41}' in py


def test_dict_rejects_unkeyed_brace() -> None:
    with pytest.raises(TranspileError, match="key: value"):
        transpile("dict<string, int> ages = {1, 2}\n")


def test_dict_rejects_mixed_brace() -> None:
    with pytest.raises(TranspileError, match="key: value"):
        transpile('dict<string, int> ages = {1, "a": 2}\n')


def test_set_literal_emits_set() -> None:
    py = transpile('set<string> tags = {"work", "home"}\n')
    assert 'tags = {"work", "home"}' in py


def test_set_empty_brace_emits_set_call() -> None:
    py = transpile("set<string> tags = {}\n")
    assert "tags = set()" in py


def test_list_brace_still_list() -> None:
    py = transpile("list<int> xs = {1, 2, 3}\n")
    assert "xs = [1, 2, 3]" in py


def test_var_empty_brace_ambiguous() -> None:
    with pytest.raises(TranspileError, match="Ambiguous brace literal"):
        transpile("var x = {}\n")


def test_var_unkeyed_brace_ambiguous() -> None:
    with pytest.raises(TranspileError, match="Ambiguous brace literal"):
        transpile("var x = {1, 2}\n")


def test_int_2d_brace_array_unchanged() -> None:
    py = transpile(
        "int[][] myNumbers = { {1, 4, 2}, {3, 6, 8} }\n"
        "print(myNumbers[0][1])\n"
    )
    assert "from array import array" in py
    assert "array('i', [1, 4, 2])" in py
    assert "array('i', [3, 6, 8])" in py
