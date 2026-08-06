"""toBin / toHex / toOct builtins (ADR-024 / CER-032)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile


def _run(source: str) -> list[str]:
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return proc.stdout.strip().splitlines()


def test_to_bin_hex_oct_phase_a_no_prefix() -> None:
    """Given int-like values, When converting without width, Then digits only."""
    out = _run(
        """
print(toBin(0b1010))
print(toHex(0xFF))
print(toOct(10))
byte b = 0b1011_1101
print(toBin(b))
print(toHex(b))
"""
    )
    assert out == ["1010", "ff", "12", "10111101", "bd"]


def test_to_bin_hex_oct_phase_b_width_pads_without_truncating() -> None:
    """Given a width, When shorter than needed pad; When longer keep full digits."""
    out = _run(
        """
print(toBin(0b1010, 8))
print(toHex(0xA, 2))
print(toHex(0xABCD, 2))
print(toOct(1, 3))
"""
    )
    assert out == ["00001010", "0a", "abcd", "001"]


def test_helpers_gated_on_use() -> None:
    bare = transpile("print(1)\n")
    assert "_pys_to_bin" not in bare
    used = transpile("print(toBin(1))\n")
    assert "def _pys_to_bin" in used


def test_arity_rejected() -> None:
    with pytest.raises(TranspileError, match="optional width"):
        transpile("print(toBin())\n")
    with pytest.raises(TranspileError, match="optional width"):
        transpile("print(toHex(1, 2, 3))\n")


def test_non_int_value_rejected() -> None:
    with pytest.raises(TranspileError, match="int-like"):
        transpile('print(toBin("1"))\n')


def test_negative_rejected_at_runtime() -> None:
    py = transpile("print(toBin(-1))\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True
        )
    assert proc.returncode != 0
    assert "non-negative" in (proc.stderr + proc.stdout)


def test_width_zero_rejected_at_runtime() -> None:
    py = transpile("print(toHex(1, 0))\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True
        )
    assert proc.returncode != 0
    assert "width" in (proc.stderr + proc.stdout).lower()
