"""examples/rest-api/shop/memory — transpile + repo/router suites (CER-001 §4)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "examples" / "rest-api" / "shop" / "memory"
MAIN = MEMORY / "src" / "main.pys"
TESTS = [
    MEMORY / "tests" / "test_repos.pys",
    MEMORY / "tests" / "test_router.pys",
    MEMORY / "tests" / "test_http_e2e.pys",
]


def test_shop_memory_main_transpiles() -> None:
    assert MAIN.is_file()
    modules = transpile_with_modules(MAIN)
    assert "main" in modules
    for stem, python_text in modules.items():
        try:
            ast.parse(python_text)
        except SyntaxError as exc:
            raise AssertionError(f"shop memory module {stem!r}: {exc}") from exc


@pytest.mark.parametrize("path", TESTS, ids=[p.name for p in TESTS])
def test_shop_memory_suites_run(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(MEMORY))
    assert path.is_file()
    assert run_source(path) == 0
