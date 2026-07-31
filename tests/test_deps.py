from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.deps import (
    DepsError,
    Dependency,
    ensure_dependency,
    parse_deps_text,
    prepend_pythonpath,
    resolve_python_executable,
)


SAMPLE = """
[interpreter]
	version: >=3.9
	path: /usr/bin/python3

[dependencies]
	mysql-connector-python
		version: 8.0.33
		build: run
	matplotlib
	my-lib
		version: latest
		build: test
	my-other-lib
"""


def test_parse_deps_basic() -> None:
    config = parse_deps_text(SAMPLE)
    assert config.interpreter.version == ">=3.9"
    assert config.interpreter.path == "/usr/bin/python3"
    assert len(config.dependencies) == 4
    assert config.dependencies[0] == Dependency("mysql-connector-python", "8.0.33", "run")
    assert config.dependencies[1] == Dependency("matplotlib", None, None)
    assert config.dependencies[2] == Dependency("my-lib", None, "test")
    assert config.dependencies[3].name == "my-other-lib"


def test_parse_rejects_unknown_section() -> None:
    with pytest.raises(DepsError, match="unknown section"):
        parse_deps_text("[plugins]\n")


def test_parse_allows_comments_and_blanks() -> None:
    text = """
# project deps
[interpreter]
	version: any  # default

[dependencies]
	# no packages yet
"""
    config = parse_deps_text(text)
    assert config.interpreter.version is None
    assert config.dependencies == []


def test_interpreter_version_check_passes() -> None:
    config = parse_deps_text("[interpreter]\n\tversion: >=3.0\n[dependencies]\n")
    assert resolve_python_executable(config)


def test_interpreter_version_check_fails() -> None:
    config = parse_deps_text("[interpreter]\n\tversion: <3.0\n[dependencies]\n")
    with pytest.raises(DepsError, match="does not satisfy"):
        resolve_python_executable(config)


def test_flyweight_reuses_installed_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_pip(python: str, package_spec: str, target: Path, *, progress_label: str | None = None) -> None:
        calls.append([python, package_spec, str(target)])
        target.mkdir(parents=True, exist_ok=True)
        dist = target / "demo-1.2.3.dist-info"
        dist.mkdir()
        (dist / "METADATA").write_text("Name: demo\nVersion: 1.2.3\n", encoding="utf-8")
        (target / "demo.py").write_text("VALUE = 1\n", encoding="utf-8")

    monkeypatch.setattr("transpiler.deps._pip_install", fake_pip)
    dep = Dependency("demo", "1.2.3")
    first = ensure_dependency(dep, python="python", repo_root=tmp_path)
    second = ensure_dependency(dep, python="python", repo_root=tmp_path)
    assert first == second
    assert len(calls) == 1  # second call is a flyweight hit


def test_prepend_pythonpath(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    env = prepend_pythonpath([a, b], {"PYTHONPATH": "old", "PATH": "x"})
    assert env["PYTHONPATH"].startswith(str(a))
    assert "old" in env["PYTHONPATH"]


def test_external_python_import_passes_through(tmp_path: Path) -> None:
    from transpiler.transpiler import transpile

    main = tmp_path / "main.pys"
    main.write_text("import math\nprint(math.pi)\n", encoding="utf-8")
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "import math" in python


def test_module_present_recognizes_pyd_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Binary extension submodules (PyQt6.QtCore → QtCore.pyd) must count as present."""
    from transpiler.deps import is_external_python_module, module_present_on_paths
    from transpiler.transpiler import transpile

    pkg = tmp_path / "PyQt6"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "QtCore.pyd").write_bytes(b"")
    assert module_present_on_paths("PyQt6.QtCore", [tmp_path])
    assert is_external_python_module("PyQt6.QtCore", [tmp_path])

    monkeypatch.setattr(
        "transpiler.imports.ImportResolver._deps_paths",
        lambda self: [tmp_path],
    )
    main = tmp_path / "main.pys"
    main.write_text("import PyQt6.QtCore\nprint(PyQt6.QtCore)\n", encoding="utf-8")
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "import PyQt6.QtCore" in python


def test_stdlib_import_as_alias(tmp_path: Path) -> None:
    from transpiler.imports import ImportResolver
    from transpiler.transpiler import transpile

    main = tmp_path / "main.pys"
    main.write_text("import tkinter as tk\nprint(tk)\n", encoding="utf-8")
    source = main.read_text(encoding="utf-8")
    python = transpile(source, source_path=main)
    assert "import tkinter as tk" in python
    resolver = ImportResolver(source, source_path=main)
    resolver.translate_import_statement("import tkinter as tk", 1, "import tkinter as tk")
    assert resolver.imported_modules.get("tk") == "tkinter"
    assert resolver.variable_types.get("tk") == "module:tkinter"


def test_external_dep_import_from_site_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.transpiler import transpile

    site = tmp_path / "site"
    pkg = site / "mysql" / "connector"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        "transpiler.imports.ImportResolver._deps_paths",
        lambda self: [site],
    )
    main = tmp_path / "main.pys"
    main.write_text("import mysql.connector\n", encoding="utf-8")
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "import mysql.connector" in python


def test_missing_type_suggests_library_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.transpiler import TranspileError, transpile

    site = tmp_path / "site"
    mod = site / "demo"
    mod.mkdir(parents=True)
    (mod / "__init__.py").write_text(
        "class Cursor:\n"
        "    def fetchall(self) -> list:\n"
        "        return []\n"
        "class Conn:\n"
        "    def cursor(self) -> Cursor:\n"
        "        return Cursor()\n"
        "def connect() -> Conn:\n"
        "    return Conn()\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text(
        "import demo\n"
        "Conn db = demo.connect()\n"
        "Cursor cur = db.cursor()\n"
        "rows = cur.fetchall()\n",
        encoding="utf-8",
    )
    with pytest.raises(TranspileError) as caught:
        transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert caught.value.code == "pys.missing-type"
    assert caught.value.suggested_fix == "list rows = cur.fetchall()"


def test_unknown_library_type_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.transpiler import TranspileError, transpile

    site = tmp_path / "site"
    (site / "demo").mkdir(parents=True)
    (site / "demo" / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text("import demo\nNoSuchType x = 1\n", encoding="utf-8")
    with pytest.raises(TranspileError, match="Unknown type 'NoSuchType'"):
        transpile(main.read_text(encoding="utf-8"), source_path=main)


def test_library_type_definition_is_navigable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.ide import analyze_file

    site = tmp_path / "site"
    mod = site / "demo"
    mod.mkdir(parents=True)
    (mod / "__init__.py").write_text(
        "class Widget:\n"
        "    pass\n"
        "def make() -> Widget:\n"
        "    return Widget()\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text("import demo\nWidget w = demo.make()\n", encoding="utf-8")
    result = analyze_file(main)
    assert result["ok"]
    loc = result["symbols"]["Widget"]
    assert loc["kind"] == "type"
    assert loc["file"].endswith("__init__.py")
    assert "Widget" in result["validated_types"]


def test_navigate_to_module_and_function(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.ide import analyze_file, lookup_symbol

    site = tmp_path / "site"
    pkg = site / "mysql" / "connector"
    pkg.mkdir(parents=True)
    (site / "mysql" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text(
        "def connect(host, user, password, database):\n"
        "    return None\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text(
        'import mysql.connector\n'
        'int x = 1\n',
        encoding="utf-8",
    )
    analysis = analyze_file(main)
    assert analysis["ok"]

    connector = lookup_symbol(analysis, "mysql.connector")
    assert connector is not None
    assert connector["kind"] == "module"
    assert connector["file"].replace("\\", "/").endswith("mysql/connector/__init__.py")

    connect = lookup_symbol(analysis, "mysql.connector.connect")
    assert connect is not None
    assert connect["kind"] == "function"
    assert connect["file"].replace("\\", "/").endswith("mysql/connector/__init__.py")
    assert connect["line"] == 1


def test_navigate_to_instance_method(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.ide import analyze_file, lookup_symbol

    site = tmp_path / "site"
    mod = site / "demo"
    mod.mkdir(parents=True)
    (mod / "__init__.py").write_text(
        "class Conn:\n"
        "    def cursor(self):\n"
        "        return None\n"
        "def connect() -> Conn:\n"
        "    return Conn()\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text(
        "import demo\n"
        "Conn db = demo.connect()\n",
        encoding="utf-8",
    )
    analysis = analyze_file(main)
    assert analysis["ok"]
    loc = lookup_symbol(analysis, "db.cursor")
    assert loc is not None
    assert loc["file"].replace("\\", "/").endswith("demo/__init__.py")
    assert loc["line"] == 2


def test_navigate_to_imported_pys_function(tmp_path: Path) -> None:
    from transpiler.ide import analyze_file, lookup_symbol

    (tmp_path / "store.pys").write_text(
        "package class AppStore {\n"
        "    private int ready\n"
        "\n"
        "    public AppStore() {\n"
        "        this.ready = 1\n"
        "    }\n"
        "}\n"
        "\n"
        "global function AppStore openStore() {\n"
        "    return AppStore()\n"
        "}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text(
        "import store\n"
        "AppStore appStore = openStore()\n",
        encoding="utf-8",
    )
    analysis = analyze_file(main)
    assert analysis["ok"], analysis.get("error")
    loc = lookup_symbol(analysis, "openStore")
    assert loc is not None
    assert loc["file"].replace("\\", "/").endswith("store.pys")
    assert loc["line"] == 9


def test_navigate_to_imported_pys_instance_method(tmp_path: Path) -> None:
    from transpiler.ide import analyze_file, lookup_symbol

    (tmp_path / "ui.pys").write_text(
        "package class PokemonApp {\n"
        "    public run() {\n"
        "        print(\"go\")\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text(
        "import ui\n"
        "PokemonApp app = PokemonApp()\n"
        "app.run()\n",
        encoding="utf-8",
    )
    analysis = analyze_file(main)
    assert analysis["ok"], analysis.get("error")
    loc = lookup_symbol(analysis, "app.run")
    assert loc is not None
    assert loc["file"].replace("\\", "/").endswith("ui.pys")
    assert loc["line"] == 2
    assert loc["kind"] == "method"


def test_untyped_library_hints_for_fetchall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.ide import analyze_file
    from transpiler.transpiler import TranspileError, transpile

    site = tmp_path / "site"
    mod = site / "demo"
    mod.mkdir(parents=True)
    (mod / "__init__.py").write_text(
        "class Cursor:\n"
        "    def fetchall(self) -> list:\n"
        "        return []\n"
        "class Conn:\n"
        "    def cursor(self) -> Cursor:\n"
        "        return Cursor()\n"
        "def connect() -> Conn:\n"
        "    return Conn()\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])

    # Missing type → suggest list + weak-library note + tips payload
    missing = tmp_path / "missing.pys"
    missing.write_text(
        "import demo\n"
        "Conn db = demo.connect()\n"
        "Cursor cur = db.cursor()\n"
        "rows = cur.fetchall()\n",
        encoding="utf-8",
    )
    with pytest.raises(TranspileError) as caught:
        transpile(missing.read_text(encoding="utf-8"), source_path=missing)
    assert caught.value.code == "pys.missing-type"
    assert "list rows" in (caught.value.suggested_fix or "")
    assert "weak/untyped" in str(caught.value)
    assert any("tuple" in tip for tip in (caught.value.tips or []))

    typed = tmp_path / "typed.pys"
    typed.write_text(
        "import demo\n"
        "Conn db = demo.connect()\n"
        "Cursor cur = db.cursor()\n"
        "list rows = cur.fetchall()\n"
        "loop (x in rows) {\n"
        "    print(x)\n"
        "}\n",
        encoding="utf-8",
    )
    analysis = analyze_file(typed)
    assert analysis["ok"]
    codes = {h["code"] for h in analysis["hints"]}
    assert "pys.untyped-library" in codes
    assert "pys.untyped-loop-var" in codes
    assert analysis["collection_element_types"].get("rows") == "tuple"
    loop_hint = next(h for h in analysis["hints"] if h["code"] == "pys.untyped-loop-var")
    assert loop_hint["suggested_loop"] == "loop (tuple x in rows)"

    # User already wrote generics → no untyped-library hint
    precise = tmp_path / "precise.pys"
    precise.write_text(
        "import demo\n"
        "Conn db = demo.connect()\n"
        "Cursor cur = db.cursor()\n"
        "list<tuple> rows = cur.fetchall()\n"
        "loop (tuple x in rows) {\n"
        "    print(x)\n"
        "}\n",
        encoding="utf-8",
    )
    precise_analysis = analyze_file(precise)
    assert precise_analysis["ok"]
    assert precise_analysis["hints"] == []
