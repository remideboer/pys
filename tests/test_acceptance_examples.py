from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = [
    ROOT / "examples" / "main.pys",
    ROOT / "examples" / "concurrency" / "main.pys",
    ROOT / "examples" / "concurrency" / "http" / "http_main.pys",
    ROOT / "examples" / "gui" / "pokemontcg" / "main.pys",
]


def test_examples_root_pys_transpile() -> None:
    """Every top-level examples/*.pys must transpile (catches bare prose / bad comments)."""
    from transpiler.transpiler import transpile

    paths = sorted((ROOT / "examples").glob("*.pys"))
    assert paths, "expected examples/*.pys"
    for path in paths:
        try:
            out = transpile(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AssertionError(f"{path.relative_to(ROOT)} failed to transpile: {exc}") from exc
        assert out.strip(), path.name


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
    # the extension does so it cannot inherit an unrelated parent lock.
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
    """Dense main.pys showcase must transpile (library-independent)."""
    path = ROOT / "examples" / "main.pys"
    modules = transpile_with_modules(path)
    assert path.stem in modules
    assert modules[path.stem].strip()


def test_acceptance_main_showcase_runs_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = ROOT / "examples" / "main.pys"
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(path.parent))
    assert run_source(path, target="python") == 0


@pytest.mark.skipif(
    __import__("shutil").which("node") is None, reason="node not on PATH"
)
def test_acceptance_main_showcase_runs_javascript(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = ROOT / "examples" / "main.pys"
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(path.parent))
    assert run_source(path, target="javascript") == 0


def test_by_target_javascript_mysql_compiles() -> None:
    path = ROOT / "examples" / "by-target" / "javascript" / "mysql" / "main.pys"
    modules = transpile_with_modules(path, target="javascript")
    js = modules[path.stem]
    assert 'from "mysql2"' in js
    assert "createConnection" in js


def test_by_target_javascript_express_memory_compiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    silo = (
        ROOT
        / "examples"
        / "by-target"
        / "javascript"
        / "rest-api"
        / "express"
        / "memory"
    )
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(silo))
    modules = transpile_with_modules(silo / "src" / "main.pys", target="javascript")
    joined = "\n".join(modules.values())
    assert 'from "express"' in joined
    assert "listen" in joined


def test_by_target_javascript_nodegui_compiles() -> None:
    path = (
        ROOT / "examples" / "by-target" / "javascript" / "gui_nodegui" / "main.pys"
    )
    modules = transpile_with_modules(path, target="javascript")
    js = modules[path.stem]
    assert "@nodegui/nodegui" in js
    assert "QMainWindow" in js
    assert "new ng.QMainWindow()" in js


def test_resolve_js_runtime_prefers_qode_for_nodegui(tmp_path: Path) -> None:
    from transpiler.transpiler import _resolve_js_runtime

    npm_root = tmp_path / "npm-env"
    (npm_root / "node_modules" / "@nodegui" / "nodegui").mkdir(parents=True)
    qode_name = "qode.cmd" if os.name == "nt" else "qode"
    qode = npm_root / "node_modules" / ".bin" / qode_name
    qode.parent.mkdir(parents=True)
    qode.write_text("", encoding="utf-8")
    path = ROOT / "examples" / "by-target" / "javascript" / "gui_nodegui" / "main.pys"
    exe = _resolve_js_runtime(path, npm_root=npm_root)
    assert "qode" in exe.lower()


def test_root_teaching_examples_run_under_javascript(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teaching-core root examples exit 0 under --target javascript."""
    import shutil

    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(ROOT / "examples"))
    names = [
        "data.pys",
        "structs.pys",
        "int_literals.pys",
        "lambdas.pys",
        "traits.pys",
        "atomic.pys",
        "results.pys",
        "nullable.pys",
    ]
    for name in names:
        path = ROOT / "examples" / name
        assert run_source(path, target="javascript") == 0, name


def test_by_target_python_mysql_compiles(
    mysql_connector_site: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compile gate only — stub site; no live MySQL / no host-installed connector."""
    silo = ROOT / "examples" / "by-target" / "python" / "mysql"
    path = silo / "main.pys"
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(silo))
    modules = transpile_with_modules(path, target="python")
    assert "mysql.connector" in modules[path.stem]
