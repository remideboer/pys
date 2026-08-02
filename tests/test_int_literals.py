"""Binary/hex literals, width aliases, bitwise ops."""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, run_source, transpile
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "int_literals.pys"


def test_example_int_literals_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "0b1010" in py
    assert "0xFFFF_FFFF" in py or "0xFFFFFFFF" in py.replace("_", "")


def test_literal_values_and_bitwise(capsys: pytest.CaptureFixture[str]) -> None:
    source = """
int i1 = 0b1010
print(i1)
byte b1 = 0b1011_1101
print(b1)
nibble n1 = 0xA
print(n1)
int16 w1 = 0xFFFF
print(w1)
print(0b1010 & 0b0101)
print(0b1010 | 0b0101)
print(0b1010 xor 0b0101)
print(0b1010 shift left 1)
print(0b1010 // 2)
print(2 ** 3)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == [
        "10",
        "189",
        "10",
        "65535",
        "0",
        "15",
        "15",
        "20",
        "5",
        "8",
    ]


@pytest.mark.parametrize(
    "source, match",
    [
        ("byte b = 256\n", r"out of range for byte"),
        ("nibble n = 16\n", r"out of range for nibble"),
        ("print(1.5 & 1)\n", r"int-like"),
        ("print(1 <<< 1)\n", r"rotate"),
        ("print(\"a\" << 1)\n", r"int-like"),
    ],
)
def test_sa_rejections(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_and_or_not_remain_logical() -> None:
    """and/or/not stay short-circuit logical, not bitwise."""
    source = """
print(0b1010 and 0b0101)
print(0b1010 or 0b0101)
print(not 0b1010)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    # Python: 10 and 5 → 5; 10 or 5 → 10; not 10 → False
    assert proc.stdout.strip().splitlines() == ["5", "10", "False"]


def test_width_alias_assignable_from_int() -> None:
    py = transpile("byte b = 10\nint x = b\nprint(x)\n")
    assert "b = 10" in py


def test_nested_generics_still_parse_with_shift_ops() -> None:
    """`>>` shift must not break `list<tuple<int, string>>` closers."""
    py = transpile(
        'list<tuple<int, string, string>> rows = []\n'
        "print(1 << 2)\n"
        "print(8 >> 1)\n"
    )
    assert "<<" in py
    assert ">>" in py
