"""Semantic analyzer checks that own errors without relying on legacy emit."""
from __future__ import annotations

import pytest

from transpiler.parse import parse_program
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError, transpile


def _analyze(source: str):
    return analyze(parse_program(source))


def test_sem_typed_interpolation_rejects_wrong_int_spec() -> None:
    with pytest.raises(TranspileError, match="requires int.*is float"):
        _analyze('float f = 3.14\nprint("#i{f} wrong")\n')


def test_sem_typed_interpolation_accepts_correct_spec() -> None:
    _analyze('int x = 10\nprint("#i{x} ok")\n')


def test_sem_typed_interpolation_string_rejects_char() -> None:
    with pytest.raises(TranspileError, match="requires string.*is char"):
        _analyze("char c = 'A'\nprint(\"#s{c} wrong\")\n")


def test_sem_typed_interpolation_object_rejects_primitive() -> None:
    with pytest.raises(TranspileError, match="requires an object.*is int"):
        _analyze('int x = 10\nprint("#o{x} wrong")\n')


def test_sem_typed_interpolation_bool_and_float_specs() -> None:
    _analyze('bool b = true\nprint("#b{b} ok")\n')
    _analyze('float f = 1.5\nprint("#f{f} ok")\n')
    with pytest.raises(TranspileError, match="requires bool.*is int"):
        _analyze('int x = 1\nprint("#b{x} wrong")\n')
    with pytest.raises(TranspileError, match="requires float.*is int"):
        _analyze('int x = 1\nprint("#f{x} wrong")\n')


def test_sem_typed_interpolation_indexed_array_element() -> None:
    _analyze('int[] xs = [1, 2]\nprint("#i{xs[0]} ok")\n')
    with pytest.raises(TranspileError, match="requires string.*is int"):
        _analyze('int[] xs = [1, 2]\nprint("#s{xs[0]} wrong")\n')


def test_pipeline_typed_interpolation_still_errors() -> None:
    with pytest.raises(TranspileError, match="requires int.*is float"):
        transpile('float f = 3.14\nprint("#i{f} wrong")\n')
