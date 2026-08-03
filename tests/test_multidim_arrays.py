"""Multi-dimensional PYS arrays (innate T[][]…, nested init, T[n][] alloc)."""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_2d_brace_initializer_emits_nested_array_array() -> None:
    """Given int[][] with nested brace init, when transpile, then rows are array.array."""
    py = transpile(
        "int[][] myNumbers = { {1, 4, 2}, {3, 6, 8} }\n"
        "print(myNumbers[0][1])\n"
    )
    assert "from array import array" in py
    assert "array('i', [1, 4, 2])" in py
    assert "array('i', [3, 6, 8])" in py
    assert "myNumbers = [" in py
    assert "list<" not in py
    assert "print(myNumbers[0][1])" in py


def test_2d_bracket_initializer_also_works() -> None:
    py = transpile("int[][] g = [[1, 2], [3, 4]]\n")
    assert "array('i', [1, 2])" in py
    assert "array('i', [3, 4])" in py


def test_3d_alloc_with_outer_size() -> None:
    """Given int[][][] arr = int[3][][], when transpile, then length-3 outer of null slots."""
    py = transpile("int[][][] arr = int[3][][]\n")
    assert "arr = [None] * 3" in py or "arr = [None, None, None]" in py


def test_fully_sized_2d_alloc_zero_fills_array_rows() -> None:
    py = transpile("int[][] grid = int[2][3]\n")
    assert "from array import array" in py
    assert "array('i'" in py
    assert py.count("array('i'") >= 1
    assert "range(2)" in py or py.count("array('i'") >= 2


def test_1d_arrays_unchanged() -> None:
    py = transpile("int[] numbers = [1, 2, 3]\n")
    assert py.strip() == "from array import array\nnumbers = array('i', [1, 2, 3])"


def test_sized_decl_rejected_use_unsized() -> None:
    with pytest.raises(TranspileError, match="Sized array type|not valid on a declaration"):
        transpile("int[3] primes = [2, 3, 5]\n")


def test_2d_rejects_scalar_in_row() -> None:
    with pytest.raises(TranspileError, match="Int array elements must be integers|Array"):
        transpile("int[][] bad = { {1, 2.5}, {3, 4} }\n")


def test_2d_sized_decl_rejected() -> None:
    with pytest.raises(TranspileError, match="Sized array type|not valid on a declaration"):
        transpile("int[2][] bad = { {1}, {2} }\n")


def test_assign_nested_literal_into_slot_uses_array_array() -> None:
    """Given a 3D alloc slot filled with braces, when transpile, then rows stay array.array."""
    py = transpile(
        "int[][][] arr = int[3][][]\n"
        "arr[0] = { {1, 2}, {3, 4} }\n"
        "print(arr[0][1][0])\n"
    )
    assert "arr = [None] * 3" in py
    assert "array('i', [1, 2])" in py
    assert "array('i', [3, 4])" in py
    assert "arr[0] = [[" not in py


def test_nested_foreach_typed_array_binder() -> None:
    """Given int[][] , when loop (int[] row in …), then emit nested for-loops."""
    py = transpile(
        "int[][] g = { {1, 2}, {3, 4} }\n"
        "loop (int[] row in g) {\n"
        "    loop (int x in row) {\n"
        "        print(x)\n"
        "    }\n"
        "}\n"
    )
    assert "for " in py
    assert "print(" in py
