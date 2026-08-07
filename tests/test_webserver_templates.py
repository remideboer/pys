"""examples/webserver-templates — engine suite + transpile main."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "webserver-templates"


def test_webserver_templates_main_transpiles() -> None:
    modules = transpile_with_modules(EX / "src" / "main.pys")
    assert "main" in modules
    for text in modules.values():
        ast.parse(text)


def test_webserver_templates_engine_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EX))
    monkeypatch.setenv("PYS_TEMPLATES_DIR", str(EX / "templates"))
    assert run_source(EX / "tests" / "test_templates.pys") == 0
