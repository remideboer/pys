"""parseFloat / parseInt builtins returning result<T, string>."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_parse_float_ok_and_err_runtime() -> None:
    source = """
result<float, string> good = parseFloat("3.14")
switch (good) {
    case ok(value):
        print(value)
    case err(message):
        print(message)
}
result<float, string> bad = parseFloat("abc")
switch (bad) {
    case ok(value):
        print(value)
    case err(message):
        print("fail")
}
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["3.14", "fail"]


def test_parse_int_ok_and_err_runtime() -> None:
    source = """
result<int, string> good = parseInt("42")
switch (good) {
    case ok(value):
        print(value)
    case err(message):
        print(message)
}
result<int, string> bad = parseInt("3.14")
switch (bad) {
    case ok(value):
        print(value)
    case err(message):
        print("fail")
}
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["42", "fail"]


def test_looks_like_float_via_parse_float() -> None:
    source = """
function bool looksLikeFloat(string input) {
    result<float, string> parsed = parseFloat(input.strip())
    switch (parsed) {
        case ok(value): return true
        case err(message): return false
    }
}
print(looksLikeFloat("1e10"))
print(looksLikeFloat("nope"))
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["True", "False"]


def test_parse_float_result_not_assignable_to_float() -> None:
    with pytest.raises(TranspileError, match="result"):
        transpile('float n = parseFloat("1")\n')


def test_parse_helpers_omitted_when_unused() -> None:
    """Result programs without parseFloat/parseInt must not emit parse helpers."""
    py = transpile(
        """
result<int, string> r = ok(1)
switch (r) {
    case ok(value):
        print(value)
    case err(message):
        print(message)
}
"""
    )
    assert "_pys_ok" in py
    assert "_pys_parse_float" not in py
    assert "_pys_parse_int" not in py


def test_parse_helpers_emitted_when_used() -> None:
    py = transpile('result<float, string> n = parseFloat("1")\n')
    assert "def _pys_parse_float" in py
    assert "def _pys_ok" in py
