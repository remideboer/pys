from __future__ import annotations

import hashlib
import os
import sys
import sysconfig
import zipfile
from pathlib import Path

import pytest

from transpiler.deps import (
    DEFAULT_INDEX_URL,
    MANIFEST_FILENAME,
    DepsLock,
    DepsError,
    Dependency,
    LockedPackage,
    deps_fingerprint,
    ensure_dependency,
    ensure_site_paths_for,
    find_deps_file,
    generate_lock,
    load_deps,
    lookup_cached_dependency,
    parse_deps_from_toml,
    parse_deps_text,
    prepend_pythonpath,
    read_lock,
    resolve_python_executable,
    resolve_site_paths,
    validate_lock,
    write_lock,
    _lock_environment_path,
)


SAMPLE = """
[interpreter]
	version: >=3.9

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
    assert len(config.dependencies) == 4
    assert config.dependencies[0] == Dependency("mysql-connector-python", "8.0.33", "run")
    assert config.dependencies[1] == Dependency("matplotlib", None, None)
    assert config.dependencies[2] == Dependency("my-lib", None, "test")
    assert config.dependencies[3].name == "my-other-lib"


def test_parse_deps_from_toml_basic() -> None:
    text = """
[interpreter]
version = ">=3.9"

[dependencies]
requests = { version = "2.32.3", build = "run" }
pytest = { version = "8.3.2", build = "test" }

[dependencies.npm]
mysql2 = "^3.11.0"
"""
    config = parse_deps_from_toml(text)
    assert config is not None
    assert config.interpreter.version == ">=3.9"
    assert [(d.name, d.version, d.build) for d in config.dependencies] == [
        ("requests", "2.32.3", "run"),
        ("pytest", "8.3.2", "test"),
    ]


def test_parse_deps_from_toml_rejects_interpreter_path() -> None:
    with pytest.raises(DepsError, match="interpreter.path"):
        parse_deps_from_toml('[interpreter]\npath = "./evil"\n')


def test_parse_deps_from_toml_npm_only_returns_none() -> None:
    assert (
        parse_deps_from_toml(
            '[project]\nmain = "main.pys"\n\n[dependencies.npm]\nmysql2 = "^3"\n'
        )
        is None
    )


def test_load_deps_prefers_pys_toml(tmp_path: Path) -> None:
    (tmp_path / "pys.toml").write_text(
        '[interpreter]\nversion = ">=3.10"\n\n'
        '[dependencies]\n"demo-pkg" = { version = "1.0.0", build = "run" }\n',
        encoding="utf-8",
    )
    (tmp_path / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n\told\n\t\tversion: 9.9.9\n",
        encoding="utf-8",
    )
    config = load_deps(tmp_path / "main.pys", stop_at=tmp_path)
    assert config is not None
    assert config.source_path == (tmp_path / MANIFEST_FILENAME).resolve()
    assert config.dependencies[0].name == "demo-pkg"


def test_load_deps_legacy_pys_deps_warns(tmp_path: Path) -> None:
    (tmp_path / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n",
        encoding="utf-8",
    )
    with pytest.warns(DeprecationWarning, match="pys.deps is deprecated"):
        config = load_deps(tmp_path / "main.pys", stop_at=tmp_path)
    assert config is not None
    assert config.source_path and config.source_path.name == "pys.deps"
    assert config.interpreter.version is None
    assert config.dependencies == []


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
    assert resolve_python_executable(config) == sys.executable


def test_interpreter_version_check_fails() -> None:
    config = parse_deps_text("[interpreter]\n\tversion: <3.0\n[dependencies]\n")
    with pytest.raises(DepsError, match="does not satisfy"):
        resolve_python_executable(config)


@pytest.mark.parametrize(
    "interpreter_path",
    [
        "./tools/evil.exe",
        "/tmp/external-python",
        r"C:\Python311\python.exe",
        r"\\attacker\share\python.exe",
    ],
)
def test_interpreter_path_is_rejected(interpreter_path: str) -> None:
    text = (
        "[interpreter]\n"
        "\tversion: any\n"
        f"\tpath: {interpreter_path}\n"
        "[dependencies]\n"
    )
    with pytest.raises(DepsError, match=r"interpreter\.path is not allowed"):
        parse_deps_text(text)


def test_parse_rejects_unsafe_dependency_version() -> None:
    """F4: version must be a simple token — no markers, options, or paths."""
    for bad in ("1.0; evil", "--help", "../x", "1.0 evil"):
        text = f"[dependencies]\n\tpkg\n\t\tversion: {bad}\n"
        with pytest.raises(DepsError, match="invalid dependency version"):
            parse_deps_text(text)


def test_parse_allows_simple_dependency_versions() -> None:
    for good in ("8.0.33", "1.2.3rc1", "2.0.0a1", "1.0.post1"):
        config = parse_deps_text(f"[dependencies]\n\tpkg\n\t\tversion: {good}\n")
        assert config.dependencies[0].version == good


def test_find_deps_file_stops_at_workspace_root(tmp_path: Path) -> None:
    """F5: do not honor pys.deps above the workspace root."""
    above = tmp_path / "above"
    workspace = above / "workspace"
    nested = workspace / "src"
    nested.mkdir(parents=True)
    (above / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n",
        encoding="utf-8",
    )
    (workspace / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n\tinside\n",
        encoding="utf-8",
    )
    found = find_deps_file(nested / "main.pys", stop_at=workspace)
    assert found == workspace / "pys.deps"
    # Parent above workspace must be ignored when stop_at is set.
    only_nested = workspace / "alone"
    only_nested.mkdir()
    (above / "pys.deps").unlink()
    # Recreate only the above-workspace deps (no workspace deps).
    (workspace / "pys.deps").unlink()
    (above / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n\tabove\n",
        encoding="utf-8",
    )
    assert find_deps_file(only_nested / "main.pys", stop_at=workspace) is None
    assert load_deps(only_nested / "main.pys", stop_at=workspace) is None


def test_find_deps_file_respects_env_workspace_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    above = tmp_path / "above"
    workspace = above / "ws"
    workspace.mkdir(parents=True)
    (above / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(workspace))
    assert find_deps_file(workspace / "main.pys") is None


def test_find_deps_file_stops_at_nearest_pys_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nested pys.toml bounds deps without PYS_WORKSPACE_ROOT (CLI / ADR-017)."""
    monkeypatch.delenv("PYS_WORKSPACE_ROOT", raising=False)
    parent = tmp_path / "monorepo"
    project = parent / "shop"
    src = project / "src"
    src.mkdir(parents=True)
    (parent / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n\tparent-only\n",
        encoding="utf-8",
    )
    (project / "pys.toml").write_text(
        '[project]\nmain = "src/main.pys"\n[source_roots]\nmain = "src"\n',
        encoding="utf-8",
    )
    (src / "main.pys").write_text("print(1)\n", encoding="utf-8")
    # No local pys.deps — must not climb past pys.toml to the parent lock.
    assert find_deps_file(src / "main.pys") is None
    assert load_deps(src / "main.pys") is None


def test_run_source_ignores_deps_above_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3: explicit Run uses the same workspace boundary as IDE analysis."""
    from types import SimpleNamespace

    from transpiler.transpiler import run_source

    parent = tmp_path / "parent"
    workspace = parent / "workspace"
    workspace.mkdir(parents=True)
    # This would fail parsing if Run incorrectly walked above the workspace.
    (parent / "pys.deps").write_text(
        "[interpreter]\n\tpath: ./evil.exe\n[dependencies]\n",
        encoding="utf-8",
    )
    source = workspace / "main.pys"
    source.write_text("print(1)\n", encoding="utf-8")
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(workspace))
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("transpiler.transpiler.subprocess.run", fake_run)
    assert run_source(source) == 0
    assert len(calls) == 1


def test_pys_import_cannot_escape_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from transpiler.transpiler import TranspileError, transpile_with_modules

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "evil.pys").write_text(
        "function int value() {\n    return 7\n}\n",
        encoding="utf-8",
    )
    main = workspace / "main.pys"
    main.write_text(
        "import all from ../outside/evil.pys\nprint(value())\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(workspace))

    with pytest.raises(TranspileError, match="Cannot find module"):
        transpile_with_modules(main)


def test_pys_import_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from transpiler.transpiler import TranspileError, transpile_with_modules

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "evil.pys").write_text(
        "function int value() {\n    return 7\n}\n",
        encoding="utf-8",
    )
    link = workspace / "linked"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    main = workspace / "main.pys"
    main.write_text(
        "import all from linked/evil.pys\nprint(value())\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(workspace))

    with pytest.raises(TranspileError, match="Cannot find module"):
        transpile_with_modules(main)


def test_ide_rejects_symlinked_document_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from transpiler.ide import analyze_file
    from transpiler.transpiler import TranspileError

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.pys"
    outside.write_text("print(1)\n", encoding="utf-8")
    linked = workspace / "linked.pys"
    try:
        os.symlink(outside, linked)
    except OSError as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(workspace))

    with pytest.raises(TranspileError, match="outside the workspace"):
        analyze_file(linked)


def test_import_module_from_sites_rejects_workspace_shadow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3: workspace PYTHONPATH shadows must not be used for typing imports."""
    from transpiler.pytypes import import_module_from_sites

    site = tmp_path / "site"
    site.mkdir()
    workspace = tmp_path / "workspace"
    shadow = workspace / "shadowpkg"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text("MARKER = 'evil'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(workspace))
    sys.modules.pop("shadowpkg", None)

    assert import_module_from_sites("shadowpkg", [site]) is None

    # Modules present under the deps site are still loaded.
    good = site / "goodpkg"
    good.mkdir()
    (good / "__init__.py").write_text("MARKER = 'good'\n", encoding="utf-8")
    sys.modules.pop("goodpkg", None)
    loaded = import_module_from_sites("goodpkg", [site])
    assert loaded is not None
    assert loaded.MARKER == "good"

    # Stdlib remains available even when unrelated site_paths are present.
    math_mod = import_module_from_sites("math", [site])
    assert math_mod is not None


def test_static_analysis_does_not_execute_cached_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4: IDE/transpile are safe; explicit runtime introspection may import."""
    from transpiler.ide import analyze_file
    from transpiler.transpiler import transpile

    package_name = "security_side_effect_pkg"
    repo = tmp_path / "repo"
    monkeypatch.setattr("transpiler.deps.default_repo_root", lambda: repo)
    deps_path = tmp_path / "pys.deps"
    deps_path.write_text(
        "[interpreter]\n"
        "\tversion: any\n"
        "[dependencies]\n"
        f"\t{package_name}\n"
        "\t\tversion: 1.0.0\n",
        encoding="utf-8",
    )
    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None
    lock = _demo_lock(
        config,
        LockedPackage(
            package_name,
            "1.0.0",
            "https://example.invalid/security.whl",
            "f" * 64,
        ),
    )
    write_lock(lock, tmp_path / "pys.lock")
    site = _lock_environment_path(lock, repo)
    site.mkdir(parents=True)
    (site / ".pys-lock.json").write_text("{}", encoding="utf-8")
    package = site / package_name
    package.mkdir(parents=True)
    marker = tmp_path / "dependency-imported"
    (package / "__init__.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "class Widget:\n"
        "    pass\n",
        encoding="utf-8",
    )
    source_path = tmp_path / "main.pys"
    source_path.write_text(
        f"import {package_name}\n"
        f"Widget widget = {package_name}.Widget()\n",
        encoding="utf-8",
    )

    transpile(source_path.read_text(encoding="utf-8"), source_path=source_path)
    assert analyze_file(source_path)["ok"]
    assert not marker.exists()

    transpile(
        source_path.read_text(encoding="utf-8"),
        source_path=source_path,
        allow_runtime_introspection=True,
    )
    assert marker.read_text(encoding="utf-8") == "executed"
    sys.modules.pop(package_name, None)


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


def test_resolve_site_paths_install_false_skips_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IDE/validate path must never download — only return already-cached packages."""
    calls: list[str] = []

    def fake_pip(python: str, package_spec: str, target: Path, *, progress_label: str | None = None) -> None:
        calls.append(package_spec)
        raise AssertionError("pip must not run when install=False")

    monkeypatch.setattr("transpiler.deps._pip_install", fake_pip)
    config = parse_deps_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n\tevildist\n\t\tversion: 1.0.0\n"
    )
    paths = resolve_site_paths(config, repo_root=tmp_path, quiet=True, install=False)
    assert paths == []
    assert calls == []
    assert lookup_cached_dependency(Dependency("evildist", "1.0.0"), repo_root=tmp_path) is None


def test_resolve_site_paths_install_false_uses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_pip(python: str, package_spec: str, target: Path, *, progress_label: str | None = None) -> None:
        target.mkdir(parents=True, exist_ok=True)
        dist = target / "demo-1.2.3.dist-info"
        dist.mkdir()
        (dist / "METADATA").write_text("Name: demo\nVersion: 1.2.3\n", encoding="utf-8")

    monkeypatch.setattr("transpiler.deps._pip_install", fake_pip)
    dep = Dependency("demo", "1.2.3")
    cached = ensure_dependency(dep, python="python", repo_root=tmp_path)
    config = parse_deps_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n\tdemo\n\t\tversion: 1.2.3\n"
    )
    # Reset pip to a bomb so read-only mode cannot call it.
    monkeypatch.setattr(
        "transpiler.deps._pip_install",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no pip")),
    )
    paths = resolve_site_paths(config, repo_root=tmp_path, quiet=True, install=False)
    assert paths == [cached]


def test_import_resolver_does_not_install_on_validate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Opening/transpiling a .pys file must not pip-install from pys.deps (F1)."""
    from transpiler.transpiler import transpile

    calls: list[str] = []

    def fake_pip(python: str, package_spec: str, target: Path, *, progress_label: str | None = None) -> None:
        calls.append(package_spec)

    monkeypatch.setattr("transpiler.deps._pip_install", fake_pip)
    monkeypatch.setattr("transpiler.deps.default_repo_root", lambda: tmp_path / "repo")
    (tmp_path / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n[dependencies]\n\tevildist\n\t\tversion: 9.9.9\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("print(1)\n", encoding="utf-8")
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "print(_pys_format(1))" in python
    assert calls == []


def _demo_lock(config, package: LockedPackage) -> DepsLock:
    return DepsLock(
        deps_fingerprint=deps_fingerprint(config),
        python=f"{sys.version_info.major}.{sys.version_info.minor}",
        platform=sysconfig.get_platform(),
        index_url=DEFAULT_INDEX_URL,
        packages=(package,),
    )


def test_lock_declares_transitive_lock_packages(tmp_path: Path) -> None:
    """Analysis recognizes transitive lock entries (e.g. anyio) without install."""
    from transpiler.deps import lock_declares_module, write_lock

    deps_path = tmp_path / "pys.deps"
    deps_path.write_text(
        "[dependencies]\n\tfastapi\n\t\tversion: 0.115.6\n",
        encoding="utf-8",
    )
    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None
    lock = DepsLock(
        deps_fingerprint=deps_fingerprint(config),
        python=f"{sys.version_info.major}.{sys.version_info.minor}",
        platform=sysconfig.get_platform(),
        index_url=DEFAULT_INDEX_URL,
        packages=(
            LockedPackage("fastapi", "0.115.6", "https://example.invalid/f.whl", "a" * 64),
            LockedPackage("anyio", "4.14.2", "https://example.invalid/a.whl", "b" * 64),
        ),
    )
    write_lock(lock, tmp_path / "pys.lock")
    main = tmp_path / "main.pys"
    main.write_text("import anyio\n", encoding="utf-8")
    assert lock_declares_module(main, "anyio") is True
    assert lock_declares_module(main, "fastapi") is True
    assert lock_declares_module(main, "missingpkg") is False


def test_lock_serialization_is_deterministic(tmp_path: Path) -> None:
    deps_path = tmp_path / "pys.deps"
    deps_path.write_text(
        "[dependencies]\n\tdemo\n\t\tversion: 1.0.0\n",
        encoding="utf-8",
    )
    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None
    lock = _demo_lock(
        config,
        LockedPackage("demo", "1.0.0", "https://example.invalid/demo.whl", "a" * 64),
    )
    lock_path = tmp_path / "pys.lock"
    write_lock(lock, lock_path)
    first = lock_path.read_bytes()
    write_lock(read_lock(lock_path), lock_path)
    assert lock_path.read_bytes() == first
    validate_lock(read_lock(lock_path), config)


def test_generate_lock_records_resolved_transitive_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace
    import json

    deps_path = tmp_path / "pys.deps"
    deps_path.write_text(
        "[dependencies]\n\tdemo\n\t\tversion: 1.0.0\n",
        encoding="utf-8",
    )
    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        report_path = Path(command[command.index("--report") + 1])
        report_path.write_text(
            json.dumps(
                {
                    "install": [
                        {
                            "metadata": {"name": "demo", "version": "1.0.0"},
                            "download_info": {
                                "url": "https://example.invalid/demo.whl",
                                "archive_info": {"hashes": {"sha256": "d" * 64}},
                            },
                        },
                        {
                            "metadata": {"name": "transitive", "version": "2.0.0"},
                            "download_info": {
                                "url": "https://example.invalid/transitive.whl",
                                "archive_info": {"hashes": {"sha256": "e" * 64}},
                            },
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("transpiler.deps.subprocess.run", fake_run)
    lock_path = generate_lock(config)
    lock = read_lock(lock_path)
    assert [package.name for package in lock.packages] == ["demo", "transitive"]
    validate_lock(lock, config)


def test_missing_and_stale_lock_fail_closed(tmp_path: Path) -> None:
    deps_path = tmp_path / "pys.deps"
    deps_path.write_text(
        "[dependencies]\n\tdemo\n\t\tversion: 1.0.0\n",
        encoding="utf-8",
    )
    with pytest.raises(DepsError, match="Missing pys.lock"):
        ensure_site_paths_for(tmp_path / "main.pys", install=True)

    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None
    lock = _demo_lock(
        config,
        LockedPackage("demo", "1.0.0", "https://example.invalid/demo.whl", "b" * 64),
    )
    write_lock(lock, tmp_path / "pys.lock")
    deps_path.write_text(
        "[dependencies]\n\tdemo\n\t\tversion: 2.0.0\n",
        encoding="utf-8",
    )
    with pytest.raises(DepsError, match="stale"):
        ensure_site_paths_for(tmp_path / "main.pys", install=True)


def test_lock_rejects_wrong_runtime_and_hash(tmp_path: Path) -> None:
    deps_path = tmp_path / "pys.deps"
    deps_path.write_text(
        "[dependencies]\n\tdemo\n\t\tversion: 1.0.0\n",
        encoding="utf-8",
    )
    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None
    package = LockedPackage(
        "demo", "1.0.0", "https://example.invalid/demo.whl", "c" * 64
    )
    valid = _demo_lock(config, package)
    wrong_python = DepsLock(
        valid.deps_fingerprint,
        "0.0",
        valid.platform,
        valid.index_url,
        valid.packages,
    )
    with pytest.raises(DepsError, match="targets Python"):
        validate_lock(wrong_python, config)
    wrong_platform = DepsLock(
        valid.deps_fingerprint,
        valid.python,
        "untrusted-platform",
        valid.index_url,
        valid.packages,
    )
    with pytest.raises(DepsError, match="targets platform"):
        validate_lock(wrong_platform, config)

    lock_path = tmp_path / "pys.lock"
    write_lock(valid, lock_path)
    text = lock_path.read_text(encoding="utf-8").replace("c" * 64, "not-a-hash")
    lock_path.write_text(text, encoding="utf-8")
    with pytest.raises(DepsError, match="Invalid SHA-256"):
        read_lock(lock_path)


def test_locked_local_wheel_installs_and_reuses_cache(tmp_path: Path) -> None:
    wheel = tmp_path / "demo-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("demo/__init__.py", "VALUE = 42\n")
        archive.writestr(
            "demo-1.0.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: demo\nVersion: 1.0.0\n",
        )
        archive.writestr(
            "demo-1.0.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: pys-test\n"
            "Root-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr("demo-1.0.0.dist-info/RECORD", "")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()

    deps_path = tmp_path / "pys.deps"
    deps_path.write_text(
        "[dependencies]\n\tdemo\n\t\tversion: 1.0.0\n",
        encoding="utf-8",
    )
    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None
    lock = _demo_lock(
        config,
        LockedPackage("demo", "1.0.0", wheel.resolve().as_uri(), digest),
    )
    write_lock(lock, tmp_path / "pys.lock")
    repo = tmp_path / "repo"

    first = resolve_site_paths(config, repo_root=repo, quiet=True, install=True)
    second = resolve_site_paths(config, repo_root=repo, quiet=True, install=True)
    assert first == second
    assert (first[0] / "demo" / "__init__.py").is_file()

    bad_lock = _demo_lock(
        config,
        LockedPackage("demo", "1.0.0", wheel.resolve().as_uri(), "0" * 64),
    )
    write_lock(bad_lock, tmp_path / "pys.lock")
    with pytest.raises(DepsError, match="Failed to install locked dependencies"):
        resolve_site_paths(config, repo_root=repo, quiet=True, install=True)


def test_unpinned_run_dependency_is_rejected(tmp_path: Path) -> None:
    deps_path = tmp_path / "pys.deps"
    deps_path.write_text("[dependencies]\n\tdemo\n", encoding="utf-8")
    config = load_deps(deps_path, stop_at=tmp_path)
    assert config is not None
    with pytest.raises(DepsError, match="exact versions"):
        deps_fingerprint(config)


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
        transpile(
            main.read_text(encoding="utf-8"),
            source_path=main,
            allow_runtime_introspection=True,
        )
    assert caught.value.code == "pys.missing-type"
    assert caught.value.suggested_fix == "list rows = cur.fetchall()"


def test_unknown_library_type_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.transpiler import TranspileError, transpile

    # No imports: unknown types fail closed (student Character/Heritage case).
    # Files with library imports keep soft-unverified types (CER-001 / CER-057).
    main = tmp_path / "main.pys"
    main.write_text("NoSuchType x = 1\n", encoding="utf-8")
    with pytest.raises(TranspileError, match="Unknown type 'NoSuchType'"):
        transpile(
            main.read_text(encoding="utf-8"),
            source_path=main,
            allow_runtime_introspection=True,
        )


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
    result = analyze_file(main, allow_runtime_introspection=True)
    assert result["ok"]
    loc = result["symbols"]["Widget"]
    assert loc["kind"] == "type"
    assert loc["file"].endswith("__init__.py")
    assert "Widget" in result["validated_types"]


def test_navigate_to_module_and_function(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from transpiler.deps import clear_filesystem_caches
    from transpiler.ide import analyze_file, lookup_symbol
    from transpiler.pytypes import clear_filesystem_caches as clear_pytypes_caches

    # Prior tests may have memoized module probes / imported mysql into sys.modules.
    clear_filesystem_caches()
    clear_pytypes_caches()
    for key in list(sys.modules):
        if key == "mysql" or key.startswith("mysql."):
            del sys.modules[key]

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
    analysis = analyze_file(main, allow_runtime_introspection=True)
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


def test_navigate_library_sources_cli_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default symbol lookup stays fail-closed; --library-sources opts in (ADR-001)."""
    import json

    from transpiler.ide import main as ide_main

    site = tmp_path / "site"
    pkg = site / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "def ping():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    main = tmp_path / "main.pys"
    main.write_text("import demo\nint x = 1\n", encoding="utf-8")

    assert ide_main([str(main), "demo.ping"]) == 0
    off = json.loads(capsys.readouterr().out)
    assert off["ok"] is False
    assert off["location"] is None
    assert off.get("library_sources") is False

    assert ide_main([str(main), "demo.ping", "--library-sources"]) == 0
    on = json.loads(capsys.readouterr().out)
    assert on["ok"] is True
    assert on["library_sources"] is True
    assert on["location"] is not None
    assert on["location"]["kind"] == "function"
    assert on["location"]["file"].replace("\\", "/").endswith("demo/__init__.py")


def test_navigate_param_attr_into_library(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Typed params participate in ``recv.attr`` library navigation (e.g. request.json)."""
    from transpiler.ide import analyze_file, lookup_symbol

    site = tmp_path / "site"
    pkg = site / "web"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "class Request:\n"
        "    def json(self):\n"
        "        return {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    main = tmp_path / "body.pys"
    main.write_text(
        "import Request from web\n"
        "\n"
        "package function object readJson(Request request) {\n"
        "    return request.json()\n"
        "}\n",
        encoding="utf-8",
    )
    off = analyze_file(main, allow_runtime_introspection=False)
    assert lookup_symbol(off, "request.json") is None

    on = analyze_file(main, allow_runtime_introspection=True)
    assert on["variable_types"].get("request") == "Request"
    loc = lookup_symbol(on, "request.json")
    assert loc is not None
    assert loc["kind"] == "function"
    assert loc["file"].replace("\\", "/").endswith("web/__init__.py")
    assert loc["line"] == 2


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
    analysis = analyze_file(main, allow_runtime_introspection=True)
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
        "    public constructor() {\n"
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
        transpile(
            missing.read_text(encoding="utf-8"),
            source_path=missing,
            allow_runtime_introspection=True,
        )
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
        "loop (tuple x in rows) {\n"
        "    print(x)\n"
        "}\n",
        encoding="utf-8",
    )
    analysis = analyze_file(typed, allow_runtime_introspection=True)
    assert analysis["ok"]
    codes = {h["code"] for h in analysis["hints"]}
    assert "pys.untyped-library" in codes
    assert analysis["collection_element_types"].get("rows") == "tuple"

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
    precise_analysis = analyze_file(precise, allow_runtime_introspection=True)
    assert precise_analysis["ok"]
    assert precise_analysis["hints"] == []
