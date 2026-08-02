"""Enums: parse/sem/emit happy path, SA rejections, naming warnings."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.ide import analyze_file, lookup_symbol
from transpiler.parse import parse_program
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError, run_source, transpile
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "enums.pys"

os.environ.setdefault("PYS_SUPPRESS_WARNINGS", "1")


def test_example_enums_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_enums_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "import enum" in py
    assert "class HttpCategory(enum.Enum):" in py
    assert "LOW = enum.auto()" not in py  # example uses other names
    assert "INFORMATIONAL = enum.auto()" in py
    assert "class HttpStatus(enum.IntEnum):" in py
    assert "class Method(enum.StrEnum):" in py


def test_enum_equality_and_value(capsys: pytest.CaptureFixture[str]) -> None:
    source = """
enum Priority {
    LOW
    HIGH
}
enum HttpStatus {
    OK = 200
    CREATED = 201
}
HttpStatus s = HttpStatus.OK
print(s == HttpStatus.OK)
print(s.value)
print(Priority.LOW == Priority.HIGH)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["True", "200", "False"]


@pytest.mark.parametrize(
    "source, match",
    [
        ("enum Foo {}\n", r"cannot be empty"),
        (
            "enum Foo {\n  A = 1\n  B\n}\n",
            r"fully implicit or fully explicit",
        ),
        (
            "enum Foo {\n  A = 1\n  B = 1\n}\n",
            r"Duplicate enum value",
        ),
        (
            'enum Foo {\n  A = 1\n  B = "x"\n}\n',
            r"homogeneous",
        ),
        (
            "enum A { X }\nenum B { Y }\nprint(A.X == B.Y)\n",
            r"Cannot compare enum",
        ),
        (
            "enum A { X = 1 }\nint n = A.X\n",
            r"Type mismatch",
        ),
        (
            "enum A { X }\nA.X = A.X\n",
            r"immutable",
        ),
        (
            "enum A { X }\nA a = A()\n",
            r"not by calling",
        ),
        (
            "enum A { X = 1 }\nprint(A.X == 1)\n",
            r"Cannot compare enum",
        ),
    ],
)
def test_enum_sa_rejections(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_enum_naming_warning_still_compiles() -> None:
    source = "enum Foo {\n  low\n  HIGH\n}\n"
    tree = analyze(parse_program(source))
    assert any(w.code == "pys.enum-naming" for w in tree.analysis_warnings)
    warn = next(w for w in tree.analysis_warnings if w.code == "pys.enum-naming")
    assert warn.suggested_fix == "LOW"
    py = transpile(source)
    assert "low = enum.auto()" in py


def test_analyze_file_includes_warnings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))
    path = tmp_path / "e.pys"
    path.write_text("enum Foo {\n  low\n}\n", encoding="utf-8")
    result = analyze_file(path)
    assert result["ok"] is True
    assert result["error"] is None
    assert any(w.get("code") == "pys.enum-naming" for w in result["warnings"])


def test_ide_goto_enum_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))
    path = tmp_path / "e.pys"
    path.write_text(
        "enum HttpStatus {\n  OK = 200\n  CREATED = 201\n}\n",
        encoding="utf-8",
    )
    result = analyze_file(path)
    loc = lookup_symbol(result, "HttpStatus.OK")
    assert loc is not None
    assert loc["line"] == 2
    assert "HttpStatus" in result["validated_types"]
