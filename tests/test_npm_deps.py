"""Central npm cache for the JavaScript emit target."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from transpiler.npm_deps import (
    NpmDepsError,
    ensure_npm_environment,
    find_npm_deps_source,
    find_package_json,
    load_npm_deps,
    npm_deps_fingerprint,
    package_json_fingerprint,
    parse_npm_from_toml,
    qode_executable,
    resolve_npm_environment,
    run_dir_for_source,
)
from transpiler.workspace import WORKSPACE_ROOT_ENV


def _write_package_json(path: Path, deps: dict[str, str]) -> Path:
    path.write_text(
        json.dumps(
            {
                "name": "pys-test-npm",
                "private": True,
                "type": "module",
                "dependencies": deps,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_package_json_fingerprint_stable(tmp_path: Path) -> None:
    a = _write_package_json(tmp_path / "package.json", {"mysql2": "^3.11.0"})
    b = _write_package_json(tmp_path / "other.json", {"mysql2": "^3.11.0"})
    assert package_json_fingerprint(a) == package_json_fingerprint(b)


def test_package_json_fingerprint_changes_with_deps(tmp_path: Path) -> None:
    a = _write_package_json(tmp_path / "a.json", {"mysql2": "^3.11.0"})
    b = _write_package_json(tmp_path / "b.json", {"mysql2": "^3.12.0"})
    assert package_json_fingerprint(a) != package_json_fingerprint(b)


def test_parse_npm_from_toml_and_fingerprint() -> None:
    text = """
[project]
main = "main.pys"

[dependencies.npm]
mysql2 = "^3.11.0"
"@nodegui/nodegui" = "^0.67.0"
"""
    cfg = parse_npm_from_toml(text)
    assert cfg is not None
    assert cfg.dependencies["mysql2"] == "^3.11.0"
    assert cfg.dependencies["@nodegui/nodegui"] == "^0.67.0"
    assert npm_deps_fingerprint(cfg.dependencies) == npm_deps_fingerprint(
        {"@nodegui/nodegui": "^0.67.0", "mysql2": "^3.11.0"}
    )


def test_load_npm_deps_prefers_toml(tmp_path: Path) -> None:
    (tmp_path / "pys.toml").write_text(
        '[dependencies.npm]\nmysql2 = "^3.11.0"\n',
        encoding="utf-8",
    )
    _write_package_json(tmp_path / "package.json", {"mysql2": "^9.0.0"})
    cfg = load_npm_deps(tmp_path / "main.pys", stop_at=tmp_path)
    assert cfg is not None
    assert cfg.dependencies["mysql2"] == "^3.11.0"
    assert cfg.source_path and cfg.source_path.name == "pys.toml"
    assert find_npm_deps_source(tmp_path / "main.pys", stop_at=tmp_path) == (
        tmp_path / "pys.toml"
    ).resolve()


def test_load_npm_deps_legacy_package_json_warns(tmp_path: Path) -> None:
    _write_package_json(tmp_path / "package.json", {"mysql2": "^3.11.0"})
    with pytest.warns(DeprecationWarning, match="package.json is deprecated"):
        cfg = load_npm_deps(tmp_path / "main.pys", stop_at=tmp_path)
    assert cfg is not None
    assert cfg.dependencies["mysql2"] == "^3.11.0"


def test_find_package_json_stops_at_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    silo = tmp_path / "silo"
    silo.mkdir()
    _write_package_json(silo / "package.json", {})
    nested = silo / "src"
    nested.mkdir()
    outer = tmp_path / "package.json"
    _write_package_json(outer, {"should": "not-see"})
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(silo))
    found = find_package_json(nested / "main.pys")
    assert found == silo / "package.json"


def test_find_package_json_stops_at_pys_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(WORKSPACE_ROOT_ENV, raising=False)
    parent = tmp_path / "parent"
    parent.mkdir()
    _write_package_json(parent / "package.json", {"outer": "1"})
    silo = parent / "silo"
    silo.mkdir()
    (silo / "pys.toml").write_text("[project]\nname = \"silo\"\n", encoding="utf-8")
    # No package.json in silo — must not inherit parent.
    assert find_package_json(silo / "main.pys") is None
    _write_package_json(silo / "package.json", {"inner": "1"})
    assert find_package_json(silo / "main.pys") == silo / "package.json"


def test_ensure_npm_environment_install_false_fails_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    pj = _write_package_json(tmp_path / "package.json", {"left-pad": "1.3.0"})
    with pytest.raises(NpmDepsError, match="not cached"):
        ensure_npm_environment(pj, repo_root=repo, install=False)


def test_ensure_npm_environment_empty_deps_no_network(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    pj = _write_package_json(pkg / "package.json", {})
    root = ensure_npm_environment(pj, repo_root=repo, install=True, quiet=True)
    assert root.parent == repo
    assert (root / "node_modules").is_dir()
    assert (root / ".pys_npm_ready").is_file()
    again = ensure_npm_environment(pj, repo_root=repo, install=False, quiet=True)
    assert again == root


def test_ensure_npm_environment_installs_into_central_cache(tmp_path: Path) -> None:
    if shutil.which("npm") is None:
        pytest.skip("npm not on PATH")
    repo = tmp_path / "repo"
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    # Tiny pure-JS package — exercises real npm install into the central cache.
    pj = _write_package_json(pkg / "package.json", {"is-number": "7.0.0"})
    root = ensure_npm_environment(pj, repo_root=repo, install=True, quiet=True)
    assert root.parent == repo
    assert (root / "node_modules" / "is-number").is_dir()
    assert (root / ".pys_npm_ready").is_file()
    again = ensure_npm_environment(pj, repo_root=repo, install=False, quiet=True)
    assert again == root


def test_run_dir_under_npm_root(tmp_path: Path) -> None:
    npm_root = tmp_path / "env"
    npm_root.mkdir()
    src = tmp_path / "main.pys"
    src.write_text("print(1)\n", encoding="utf-8")
    out = run_dir_for_source(npm_root, src)
    assert out.parent == npm_root / "runs"
    assert out.is_dir()


def test_qode_executable_none_without_nodegui(tmp_path: Path) -> None:
    assert qode_executable(tmp_path) is None


def test_resolve_npm_environment_none_without_package_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))
    src = tmp_path / "main.pys"
    src.write_text("print(1)\n", encoding="utf-8")
    assert resolve_npm_environment(src, install=False) is None


def test_by_target_mysql_npm_deps_in_toml() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "examples" / "by-target" / "javascript" / "mysql" / "main.pys"
    cfg = load_npm_deps(path)
    assert cfg is not None
    assert cfg.source_path is not None
    assert cfg.source_path.name == "pys.toml"
    assert cfg.dependencies.get("mysql2") == "^3.11.0"
    assert find_package_json(path) is None


def test_by_target_express_memory_npm_deps_in_toml() -> None:
    root = Path(__file__).resolve().parents[1]
    path = (
        root
        / "examples"
        / "by-target"
        / "javascript"
        / "rest-api"
        / "express"
        / "memory"
        / "src"
        / "main.pys"
    )
    cfg = load_npm_deps(path)
    assert cfg is not None
    assert cfg.dependencies.get("express") == "^4.21.0"


def test_deps_lock_npm_only_toml_explains_no_pys_lock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """npm-only manifests must not look like a missing deps file."""
    import subprocess
    import sys

    silo = tmp_path / "js-silo"
    silo.mkdir()
    toml = silo / "pys.toml"
    toml.write_text(
        '[project]\nmain = "main.pys"\ntarget = "javascript"\n\n'
        '[dependencies.npm]\nexpress = "^4.21.0"\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-m", "transpiler", "deps", "lock", str(toml)],
        cwd=str(silo),
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = (proc.stdout or "") + (proc.stderr or "")
    assert "[dependencies.npm] only" in out
    assert "pys.lock" in out
    assert not (silo / "pys.lock").exists()


def test_run_source_javascript_uses_central_npm_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run writes under $PYS_REPO/npm/.../runs/ — no silo node_modules."""
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    from transpiler.deps import REPO_ROOT_ENV
    from transpiler.transpiler import run_source

    silo = tmp_path / "silo"
    silo.mkdir()
    (silo / "pys.toml").write_text(
        '[project]\nname = "npm-run"\n\n[dependencies.npm]\n',
        encoding="utf-8",
    )
    src = silo / "main.pys"
    src.write_text('print("central-npm-ok")\n', encoding="utf-8")
    monkeypatch.setenv(REPO_ROOT_ENV, str(tmp_path / "central"))
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(silo))
    assert run_source(src, target="javascript") == 0
    npm_tree = tmp_path / "central" / "npm"
    assert npm_tree.is_dir()
    runs = list(npm_tree.glob("*/runs/*/main.mjs"))
    assert runs, "expected emitted main.mjs under central npm runs/"
    assert not (silo / "node_modules").exists()
