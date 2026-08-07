"""examples/webserver-static — resolve suite + transpile main."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "webserver-static"


def test_webserver_static_main_transpiles() -> None:
    modules = transpile_with_modules(EX / "src" / "main.pys")
    assert "main" in modules
    for stem, text in modules.items():
        ast.parse(text)


def test_webserver_static_resolve_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EX))
    monkeypatch.setenv("PYS_STATIC_WWW", str(EX / "www"))
    assert run_source(EX / "tests" / "test_static_resolve.pys") == 0
