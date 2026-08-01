from __future__ import annotations

import ast
from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = [
    ROOT / "examples" / "main.pys",
    ROOT / "examples" / "concurrency" / "main.pys",
    ROOT / "examples" / "gui" / "pokemontcg" / "main.pys",
]


def test_acceptance_examples_transpile() -> None:
    """Showcase entries must compile on the AST pipeline (multi-module)."""
    for path in ACCEPTANCE:
        assert path.is_file(), path
        modules = transpile_with_modules(path)
        assert path.stem in modules
        assert modules[path.stem].strip()
        for stem, python_text in modules.items():
            try:
                ast.parse(python_text)
            except SyntaxError as exc:
                raise AssertionError(f"{path.name} module {stem!r} is not valid Python: {exc}") from exc


def test_acceptance_concurrency_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Concurrency showcase must execute end-to-end (no GUI / DB)."""
    path = ROOT / "examples" / "concurrency" / "main.pys"
    # This example has no third-party dependencies. Bound its Run exactly as
    # the extension does so it cannot inherit the unrelated root MySQL lock.
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(path.parent))
    assert run_source(path) == 0


def test_acceptance_pokemontcg_compiles_gui_entry() -> None:
    """Pokemon TCG Tk entry must transpile (run would block on Tk mainloop)."""
    path = ROOT / "examples" / "gui" / "pokemontcg" / "main.pys"
    modules = transpile_with_modules(path)
    joined = "\n".join(modules.values())
    assert "PokemonApp" in joined or "class PokemonApp" in modules.get("ui", "")
    assert "openStore" in joined or "def openStore" in modules.get("store", "")


def test_acceptance_pokemontcg_pyqt_compiles_gui_entry() -> None:
    """Pokemon TCG PyQt silo must transpile (run would block on Qt event loop)."""
    path = ROOT / "examples" / "gui" / "PyQt" / "main.pys"
    modules = transpile_with_modules(path)
    ui = modules.get("ui", "")
    assert "PokemonQtApp" in ui or "class PokemonQtApp" in ui
    assert "QMainWindow" in ui
    assert "from PyQt6.QtWidgets import" in ui
    assert "currentRowChanged" in ui
    assert "openStore" in "\n".join(modules.values()) or "def openStore" in modules.get("store", "")


def test_acceptance_main_showcase_compiles() -> None:
    """Dense main.pys showcase must transpile (run needs MySQL)."""
    path = ROOT / "examples" / "main.pys"
    modules = transpile_with_modules(path)
    main_py = modules["main"]
    assert "import mysql.connector" in main_py or "mysql" in main_py
    assert any("def " in text or "class " in text for text in modules.values())
