"""Compiler warnings: non-fatal diagnostics on the analyze / IDE path."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.ide import analyze_file
from transpiler.parse import parse_program
from transpiler.sem import analyze
from transpiler.transpiler import TranspileWarning, transpile
from transpiler.workspace import WORKSPACE_ROOT_ENV


def test_transpile_warning_to_dict() -> None:
    w = TranspileWarning(
        "demo",
        2,
        3,
        "low",
        code="pys.enum-naming",
        suggested_fix="LOW",
        tips=["Rename"],
    )
    d = w.to_dict()
    assert d["message"] == "demo"
    assert d["code"] == "pys.enum-naming"
    assert d["suggested_fix"] == "LOW"
    assert "warning:" in str(w)


def test_warnings_do_not_fail_compile() -> None:
    source = "enum E {\n  soft\n}\n"
    tree = analyze(parse_program(source))
    assert tree.analysis_warnings
    assert transpile(source)  # still emits


def test_analyze_file_warnings_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))
    path = tmp_path / "w.pys"
    path.write_text("enum E {\n  soft\n}\n", encoding="utf-8")
    result = analyze_file(path)
    assert result["ok"] is True
    assert isinstance(result["warnings"], list)
    assert result["warnings"][0]["code"] == "pys.enum-naming"
