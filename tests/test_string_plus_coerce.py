"""String-involved + concatenates and coerces (CER-033)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from transpiler.transpiler import transpile


def _run(source: str) -> list[str]:
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
    return proc.stdout.strip().splitlines()


def test_concat_coerces_typed_int_identifier() -> None:
    py = transpile(
        """
var firstName = "Tom"
fix int birthYear = 1990
print(firstName + " was born in " + birthYear)
"""
    )
    assert "str(birthYear)" in py
    assert _run(
        """
var firstName = "Tom"
fix int birthYear = 1990
print(firstName + " was born in " + birthYear)
"""
    ) == ["Tom was born in 1990"]


def test_concat_coerces_int_on_left() -> None:
    assert _run('print(1990 + " was a year")\n') == ["1990 was a year"]


def test_numeric_plus_unchanged() -> None:
    assert _run("print(3 + 10)\n") == ["13"]


def test_concat_coerces_float_and_bool() -> None:
    assert _run('print("x=" + 3.5)\n') == ["x=3.5"]
    out = _run('print("ok=" + true)\n')
    assert out == ["ok=True"]  # Python emit str(True)
