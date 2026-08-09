"""Central npm dependency cache for the JavaScript emit target.

Declares npm packages in ``pys.toml`` ``[dependencies.npm]`` (preferred) or
legacy ``package.json``. **Run** installs into
``~/.pys/repository/npm/<fingerprint>/`` (ADR-001 explicit Run may network).
Projects do not need a local ``npm install`` / ``node_modules``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from .deps import (
    MANIFEST_FILENAME,
    _load_tomllib_data,
    _workspace_stop_at,
    default_repo_root,
)

PACKAGE_JSON = "package.json"
NPM_READY_MARKER = ".pys_npm_ready"
_LEGACY_PKG_WARNED: set[str] = set()


class NpmDepsError(ValueError):
    """Invalid npm dependency declaration or resolution failure."""


@dataclass
class NpmDepsConfig:
    """Declared npm dependencies for one project."""

    dependencies: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None
    package_name: str = "pys-npm-env"
    module_type: str = "module"


def default_npm_repo_root() -> Path:
    """``$PYS_REPO/npm`` or ``~/.pys/repository/npm``."""
    return default_repo_root() / "npm"


def _warn_legacy_package_json(path: Path) -> None:
    key = str(path.resolve())
    if key in _LEGACY_PKG_WARNED:
        return
    _LEGACY_PKG_WARNED.add(key)
    warnings.warn(
        f"{path.name} is deprecated; declare [dependencies.npm] in "
        f"{MANIFEST_FILENAME} instead (see docs/LANGUAGE.md).",
        DeprecationWarning,
        stacklevel=3,
    )


def _declared_dependencies(data: dict) -> dict[str, str]:
    merged: dict[str, str] = {}
    for key in ("dependencies", "optionalDependencies"):
        block = data.get(key) or {}
        if isinstance(block, dict):
            for name, ver in block.items():
                merged[str(name)] = str(ver)
    return dict(sorted(merged.items()))


def npm_deps_fingerprint(dependencies: dict[str, str]) -> str:
    """Stable digest of declared dependency names/versions (not lockfile)."""
    payload = json.dumps(
        {"dependencies": dict(sorted(dependencies.items()))},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def package_json_fingerprint(package_json: Path) -> str:
    """Legacy helper: fingerprint a package.json file."""
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NpmDepsError(f"Cannot read {package_json}: {exc}") from exc
    if not isinstance(data, dict):
        raise NpmDepsError(f"{package_json} must contain a JSON object")
    return npm_deps_fingerprint(_declared_dependencies(data))


def parse_npm_from_toml(text: str, *, source_path: Path | None = None) -> NpmDepsConfig | None:
    """Parse ``[dependencies.npm]`` from pys.toml; None if absent."""
    label = str(source_path) if source_path else MANIFEST_FILENAME
    data = _load_tomllib_data(text, label=label)
    deps_table = data.get("dependencies")
    if not isinstance(deps_table, dict) or "npm" not in deps_table:
        return None
    npm = deps_table["npm"]
    if not isinstance(npm, dict):
        raise NpmDepsError(f"{label}: [dependencies.npm] must be a TOML table")
    out: dict[str, str] = {}
    for name, ver in npm.items():
        if not isinstance(name, str) or not name.strip():
            raise NpmDepsError(f"{label}: invalid npm package name '{name}'")
        if not isinstance(ver, str) or not ver.strip():
            raise NpmDepsError(
                f"{label}: npm package '{name}' must have a non-empty version string"
            )
        out[name] = ver.strip()
    js = data.get("javascript")
    package_name = "pys-npm-env"
    module_type = "module"
    if isinstance(js, dict):
        raw_name = js.get("name")
        if isinstance(raw_name, str) and raw_name.strip():
            package_name = raw_name.strip()
        raw_type = js.get("type")
        if isinstance(raw_type, str) and raw_type.strip():
            module_type = raw_type.strip()
    return NpmDepsConfig(
        dependencies=dict(sorted(out.items())),
        source_path=source_path,
        package_name=package_name,
        module_type=module_type,
    )


def parse_npm_from_package_json(
    text: str, *, source_path: Path | None = None
) -> NpmDepsConfig:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NpmDepsError(f"Cannot parse {source_path or PACKAGE_JSON}: {exc}") from exc
    if not isinstance(data, dict):
        raise NpmDepsError(f"{source_path or PACKAGE_JSON} must contain a JSON object")
    name = data.get("name")
    module_type = data.get("type")
    return NpmDepsConfig(
        dependencies=_declared_dependencies(data),
        source_path=source_path,
        package_name=str(name) if isinstance(name, str) and name else "pys-npm-env",
        module_type=str(module_type)
        if isinstance(module_type, str) and module_type
        else "module",
    )


def find_package_json(start: Path, *, stop_at: Path | None = None) -> Path | None:
    """Walk upward for legacy ``package.json`` (same bounds as pys.deps)."""
    try:
        current = start.resolve()
    except OSError:
        return None
    if current.is_file():
        current = current.parent
    bound = _workspace_stop_at(stop_at, start=start)
    for directory in [current, *current.parents]:
        if bound is not None:
            try:
                directory.relative_to(bound)
            except ValueError:
                break
        candidate = directory / PACKAGE_JSON
        if candidate.is_file():
            return candidate
        if bound is not None and directory == bound:
            break
        if directory.parent == directory:
            break
    return None


def find_npm_deps_source(start: Path, *, stop_at: Path | None = None) -> Path | None:
    """Prefer ``pys.toml`` with ``[dependencies.npm]``, else legacy ``package.json``."""
    try:
        current = start.resolve()
    except OSError:
        return None
    if current.is_file():
        current = current.parent
    bound = _workspace_stop_at(stop_at, start=start)
    for directory in [current, *current.parents]:
        if bound is not None:
            try:
                directory.relative_to(bound)
            except ValueError:
                break
        toml = directory / MANIFEST_FILENAME
        if toml.is_file():
            try:
                cfg = parse_npm_from_toml(
                    toml.read_text(encoding="utf-8"),
                    source_path=toml,
                )
            except (OSError, NpmDepsError, ValueError):
                cfg = None
            if cfg is not None:
                return toml
            legacy = directory / PACKAGE_JSON
            if legacy.is_file():
                return legacy
            return None
        candidate = directory / PACKAGE_JSON
        if candidate.is_file():
            return candidate
        if bound is not None and directory == bound:
            break
        if directory.parent == directory:
            break
    return None


def load_npm_deps(start: Path, *, stop_at: Path | None = None) -> NpmDepsConfig | None:
    """Load npm deps from ``pys.toml`` or legacy ``package.json``."""
    start = start.expanduser()
    try:
        start = start.resolve()
    except OSError:
        return None
    if start.is_file() and start.name == MANIFEST_FILENAME:
        return parse_npm_from_toml(
            start.read_text(encoding="utf-8"),
            source_path=start,
        )
    if start.is_file() and start.name == PACKAGE_JSON:
        _warn_legacy_package_json(start)
        return parse_npm_from_package_json(
            start.read_text(encoding="utf-8"),
            source_path=start,
        )
    path = find_npm_deps_source(start, stop_at=stop_at)
    if path is None:
        return None
    if path.name == MANIFEST_FILENAME:
        return parse_npm_from_toml(
            path.read_text(encoding="utf-8"),
            source_path=path,
        )
    _warn_legacy_package_json(path)
    return parse_npm_from_package_json(
        path.read_text(encoding="utf-8"),
        source_path=path,
    )


def npm_env_path(fingerprint: str, *, repo_root: Path | None = None) -> Path:
    return (repo_root or default_npm_repo_root()) / fingerprint


def _write_env_package_json(config: NpmDepsConfig, dest_dir: Path) -> None:
    slim = {
        "name": config.package_name or "pys-npm-env",
        "private": True,
        "type": config.module_type or "module",
        "dependencies": dict(sorted(config.dependencies.items())),
    }
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / PACKAGE_JSON).write_text(
        json.dumps(slim, indent=2) + "\n",
        encoding="utf-8",
    )


def _resolve_npm_cli() -> str:
    npm = shutil.which("npm")
    if npm is None:
        raise NpmDepsError(
            "npm was not found on PATH. Install Node.js (includes npm) to resolve "
            f"[dependencies.npm] in {MANIFEST_FILENAME}."
        )
    return npm


def ensure_npm_environment(
    source: Path | NpmDepsConfig,
    *,
    repo_root: Path | None = None,
    install: bool = True,
    quiet: bool = False,
) -> Path:
    """Return central env dir with ``node_modules`` for this npm declaration.

    ``source`` may be an ``NpmDepsConfig``, a ``pys.toml``, or legacy
    ``package.json``. When ``install`` is False (IDE), only return a path that
    is already ready; never run npm.
    """
    if isinstance(source, NpmDepsConfig):
        config = source
    else:
        path = source.resolve()
        if path.name == MANIFEST_FILENAME:
            loaded = parse_npm_from_toml(
                path.read_text(encoding="utf-8"),
                source_path=path,
            )
            if loaded is None:
                raise NpmDepsError(
                    f"No [dependencies.npm] in {path}"
                )
            config = loaded
        elif path.name == PACKAGE_JSON:
            _warn_legacy_package_json(path)
            config = parse_npm_from_package_json(
                path.read_text(encoding="utf-8"),
                source_path=path,
            )
        else:
            raise NpmDepsError(
                f"npm source must be {MANIFEST_FILENAME} or {PACKAGE_JSON}: {path}"
            )

    label = str(config.source_path) if config.source_path else "npm deps"
    fp = npm_deps_fingerprint(config.dependencies)
    root = npm_env_path(fp, repo_root=repo_root)
    marker = root / NPM_READY_MARKER
    modules = root / "node_modules"
    if marker.is_file() and modules.is_dir():
        return root

    if not install:
        raise NpmDepsError(
            f"npm environment for {label} is not cached under {root}. "
            "Run the program (explicit Run) to install into the central repository."
        )

    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    _write_env_package_json(config, root)
    deps = config.dependencies
    if not deps:
        modules.mkdir(parents=True, exist_ok=True)
        marker.write_text(fp + "\n", encoding="utf-8")
        return root

    npm = _resolve_npm_cli()
    if not quiet:
        print(f"Resolving npm dependencies into {root}...", flush=True)
    proc = subprocess.run(
        [npm, "install", "--ignore-scripts=false"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise NpmDepsError(
            f"npm install failed for {label} (exit {proc.returncode}). {detail}"
        )
    if not modules.is_dir():
        raise NpmDepsError(f"npm install produced no node_modules under {root}")
    marker.write_text(fp + "\n", encoding="utf-8")
    if not quiet:
        print("npm dependencies ready.", flush=True)
    return root


def resolve_npm_environment(
    source_path: Path,
    *,
    install: bool = True,
    quiet: bool = False,
    repo_root: Path | None = None,
) -> Path | None:
    """Find nearest npm deps declaration and ensure a central env; else ``None``."""
    config = load_npm_deps(source_path)
    if config is None:
        return None
    return ensure_npm_environment(
        config,
        repo_root=repo_root,
        install=install,
        quiet=quiet,
    )


def run_dir_for_source(npm_root: Path, source_path: Path) -> Path:
    """Per-entrypoint emit folder under the central npm env (sibling to node_modules)."""
    key = hashlib.sha256(str(source_path.resolve()).encode("utf-8")).hexdigest()[:16]
    out = npm_root / "runs" / key
    out.mkdir(parents=True, exist_ok=True)
    return out


def qode_executable(npm_root: Path) -> str | None:
    """Return ``qode`` under a central env when NodeGUI is present."""
    nodegui = npm_root / "node_modules" / "@nodegui" / "nodegui"
    qode = npm_root / "node_modules" / ".bin" / ("qode.cmd" if os.name == "nt" else "qode")
    if nodegui.is_dir() and qode.is_file():
        return str(qode)
    return None
