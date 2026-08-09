"""examples/by-target/javascript/rest-api/express/memory — transpile + suites."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "examples" / "by-target" / "javascript" / "rest-api" / "express" / "memory"
MAIN = MEMORY / "src" / "main.pys"
TESTS = [
    MEMORY / "tests" / "test_repos.pys",
    MEMORY / "tests" / "test_api.pys",
]


def test_express_memory_main_transpiles() -> None:
    assert MAIN.is_file()
    modules = transpile_with_modules(MAIN, target="javascript")
    assert "main" in modules
    assert "import express from \"express\";" in modules["main"] or any(
        "import express from \"express\";" in text for text in modules.values()
    )


@pytest.mark.parametrize("path", TESTS, ids=[p.name for p in TESTS])
def test_express_memory_suites_run(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(MEMORY))
    assert path.is_file()
    assert run_source(path, target="javascript") == 0
