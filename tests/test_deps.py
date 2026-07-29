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
    from transpiler.transpiler import Parser

    # Fake a site package: pkgutil is stdlib; use math which is always available.
    main = tmp_path / "main.pys"
    main.write_text("import math\nprint(math.pi)\n", encoding="utf-8")
    python = Parser(main.read_text(encoding="utf-8"), source_path=main).parse()
    assert "import math" in python


def test_external_dep_import_from_site_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.transpiler import Parser

    site = tmp_path / "site"
    pkg = site / "mysql" / "connector"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        "transpiler.transpiler.Parser._deps_paths",
        lambda self: [site],
    )
    main = tmp_path / "main.pys"
    main.write_text("import mysql.connector\n", encoding="utf-8")
    python = Parser(main.read_text(encoding="utf-8"), source_path=main).parse()
    assert "import mysql.connector" in python


def test_missing_type_suggests_library_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.transpiler import Parser, TranspileError

    site = tmp_path / "site"
    # minimal fake package with annotated method
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
    monkeypatch.setattr("transpiler.transpiler.Parser._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text(
        "import demo\n"
        "Conn db = demo.connect()\n"
        "Cursor cur = db.cursor()\n"
        "rows = cur.fetchall()\n",
        encoding="utf-8",
    )
    with pytest.raises(TranspileError) as caught:
        Parser(main.read_text(encoding="utf-8"), source_path=main).parse()
    assert caught.value.code == "pys.missing-type"
    assert caught.value.suggested_fix == "list rows = cur.fetchall()"


def test_unknown_library_type_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.transpiler import Parser, TranspileError

    site = tmp_path / "site"
    (site / "demo").mkdir(parents=True)
    (site / "demo" / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr("transpiler.transpiler.Parser._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text("import demo\nNoSuchType x = 1\n", encoding="utf-8")
    with pytest.raises(TranspileError, match="Unknown type 'NoSuchType'"):
        Parser(main.read_text(encoding="utf-8"), source_path=main).parse()


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
    monkeypatch.setattr("transpiler.transpiler.Parser._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text("import demo\nWidget w = demo.make()\n", encoding="utf-8")
    result = analyze_file(main)
    assert result["ok"]
    loc = result["symbols"]["Widget"]
    assert loc["kind"] == "type"
    assert loc["file"].endswith("__init__.py")
    assert "Widget" in result["validated_types"]
