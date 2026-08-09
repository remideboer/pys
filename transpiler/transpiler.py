"""Public transpile / run API for the PYS → Python pipeline."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .concurrency import CONCURRENCY_PREAMBLE
from .imports import ModuleInfo

# Back-compat alias for callers that still import the private name.
_CONCURRENCY_PREAMBLE = CONCURRENCY_PREAMBLE

__all__ = [
    "ModuleInfo",
    "TranspileError",
    "TranspileWarning",
    "transpile",
    "transpile_path",
    "transpile_with_modules",
    "transpile_with_modules_and_maps",
    "run_source",
]


class TranspileError(ValueError):
    """Raised when source code cannot be transpiled."""

    def __init__(
        self,
        message: str,
        line_number: int | None = None,
        column: int | None = None,
        code_line: str | None = None,
        source_file: Path | None = None,
        code: str | None = None,
        suggested_fix: str | None = None,
        tips: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.column = column
        self.code_line = code_line
        self.source_file = source_file
        self.code = code
        self.suggested_fix = suggested_fix
        self.tips = tips or []

    def __str__(self) -> str:
        base = super().__str__()
        parts: list[str] = []
        if self.line_number is not None:
            parts.append(f"line {self.line_number}")
        if self.column is not None:
            parts.append(f"column {self.column}")
        if parts:
            return f"{base} ({', '.join(parts)})"
        return base


class TranspileWarning:
    """Non-fatal diagnostic collected during analysis (does not abort compile)."""

    def __init__(
        self,
        message: str,
        line_number: int | None = None,
        column: int | None = None,
        code_line: str | None = None,
        *,
        code: str | None = None,
        suggested_fix: str | None = None,
        tips: list[str] | None = None,
    ) -> None:
        self.message = message
        self.line_number = line_number
        self.column = column
        self.code_line = code_line
        self.code = code
        self.suggested_fix = suggested_fix
        self.tips = tips or []

    def __str__(self) -> str:
        parts: list[str] = []
        if self.line_number is not None:
            parts.append(f"line {self.line_number}")
        if self.column is not None:
            parts.append(f"column {self.column}")
        loc = f" ({', '.join(parts)})" if parts else ""
        return f"warning: {self.message}{loc}"

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "line": self.line_number,
            "column": self.column,
            "code_line": self.code_line,
            "code": self.code,
            "suggested_fix": self.suggested_fix,
            "tips": list(self.tips),
        }


def transpile(
    source_code: str,
    *,
    source_path: Path | None = None,
    allow_runtime_introspection: bool = False,
    is_entrypoint: bool = False,
    target: str = "python",
) -> str:
    """Convert teaching language source into the requested backend text."""
    from .pipeline import compile_pys

    return compile_pys(
        source_code,
        target=target,  # type: ignore[arg-type]
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
        is_entrypoint=is_entrypoint,
    )


def transpile_with_modules(
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
    target: str = "python",
) -> dict[str, str]:
    """Transpile a .pys entry file and all imported .pys modules.

    Returns a mapping of module stem -> emitted source text.
    """
    modules, _maps, _names = transpile_with_modules_and_maps(
        source_path,
        allow_runtime_introspection=allow_runtime_introspection,
        target=target,
    )
    return modules


def transpile_with_modules_and_maps(
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
    target: str = "python",
) -> tuple[dict[str, str], dict[str, list[dict[str, int]]], dict[str, dict[str, str]]]:
    """Transpile entry + imports; return emitted text, line maps, and debug names."""
    from .imports import discover_imported_modules
    from .pipeline import compile_pys_with_map
    from .project_manifest import resolve_entrypoint

    source_path = resolve_entrypoint(source_path)
    text = source_path.read_text(encoding="utf-8")
    module_cache = discover_imported_modules(
        source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    modules: dict[str, str] = {}
    maps: dict[str, list[dict[str, int]]] = {}
    names: dict[str, dict[str, str]] = {}
    emitted, line_map, debug_names = compile_pys_with_map(
        text,
        target=target,  # type: ignore[arg-type]
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
        is_entrypoint=True,
    )
    modules[source_path.stem] = emitted
    maps[source_path.stem] = line_map
    names[source_path.stem] = debug_names
    for path in module_cache:
        emitted, line_map, debug_names = compile_pys_with_map(
            path.read_text(encoding="utf-8"),
            target=target,  # type: ignore[arg-type]
            source_path=path,
            allow_runtime_introspection=allow_runtime_introspection,
            is_entrypoint=False,
        )
        modules[path.stem] = emitted
        maps[path.stem] = line_map
        names[path.stem] = debug_names
    return modules, maps, names


def transpile_path(
    source_path: Path,
    target_path: Path,
    *,
    target: str = "python",
) -> None:
    """Transpile a file and write the output (plus imported modules)."""
    source_path = source_path.resolve()
    if source_path.is_dir() or source_path.suffix == ".pys":
        from .project_manifest import resolve_entrypoint

        source_path = resolve_entrypoint(source_path)
    if source_path.suffix == ".pys":
        modules = transpile_with_modules(source_path, target=target)
        ext = ".mjs" if target == "javascript" else ".py"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(modules[source_path.stem], encoding="utf-8")
        for stem, text in modules.items():
            if stem == source_path.stem:
                continue
            (target_path.parent / f"{stem}{ext}").write_text(text, encoding="utf-8")
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def _resolve_js_runtime(
    source_path: Path,
    *,
    npm_root: Path | None = None,
) -> str:
    """Prefer ``qode`` from a central npm env (or local silo); else ``node`` on PATH.

    Plain ``node`` cannot load ``@nodegui/nodegui``'s native addon (Qt DLLs);
    NodeGUI apps must run under ``@nodegui/qode``.
    """
    import shutil

    from .npm_deps import qode_executable

    if npm_root is not None:
        qode = qode_executable(npm_root)
        if qode is not None:
            return qode

    here = source_path.parent.resolve()
    for folder in [here, *here.parents]:
        qode_cmd = folder / "node_modules" / ".bin" / ("qode.cmd" if os.name == "nt" else "qode")
        nodegui = folder / "node_modules" / "@nodegui" / "nodegui"
        if qode_cmd.is_file() and nodegui.is_dir():
            return str(qode_cmd)
        if (folder / "package.json").is_file() and folder != here:
            # Stop at package root even if qode missing — fall through to node.
            break
        if folder != here and (folder / "pys.toml").is_file():
            break

    node = shutil.which("node")
    if node is None:
        raise TranspileError(
            "Node.js (`node`) was not found on PATH. Install Node.js to run "
            "--target javascript programs."
        )
    return node


def _resolve_node_executable() -> str:
    """Return a Node.js executable on PATH, or raise TranspileError."""
    return _resolve_js_runtime(Path.cwd())


def run_source(source_path: Path, *, target: str | None = None) -> int:
    """Transpile a source file and execute it (Python or Node per ``target``).

    When ``target`` is omitted, use ``[project].target`` from the nearest
    ``pys.toml`` (default ``python``).
    """
    from .deps import (
        DepsError,
        load_deps,
        prepend_pythonpath,
        resolve_python_executable,
        resolve_site_paths,
    )
    from .npm_deps import (
        NpmDepsError,
        resolve_npm_environment,
        run_dir_for_source,
    )

    from .project_manifest import load_project_emit_target, resolve_entrypoint

    if target is None:
        target = load_project_emit_target(source_path)
    if target not in ("python", "javascript"):
        raise TranspileError(f"Unsupported run target {target!r}")

    source_path = resolve_entrypoint(source_path)
    env = dict(os.environ)
    python_exe = sys.executable
    # Deps stop at PYS_WORKSPACE_ROOT or nearest pys.toml (see find_deps_file).
    # Python site-packages apply only to the python emit target.
    try:
        deps_config = load_deps(source_path)
        if deps_config is not None and target == "python":
            python_exe = resolve_python_executable(deps_config)
            site_paths = resolve_site_paths(deps_config, build="run", python=python_exe)
            env = prepend_pythonpath(site_paths, env)
    except DepsError as exc:
        raise TranspileError(str(exc), source_file=source_path) from exc

    if source_path.suffix == ".pys":
        modules = transpile_with_modules(
            source_path,
            allow_runtime_introspection=True,
            target=target,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            if target == "javascript":
                # package.json → ~/.pys/repository/npm/<digest> (parity with pys.deps).
                # pys.toml [dependencies.npm] → ~/.pys/repository/npm/<digest>.
                npm_root: Path | None = None
                try:
                    npm_root = resolve_npm_environment(source_path, install=True)
                except NpmDepsError as exc:
                    raise TranspileError(str(exc), source_file=source_path) from exc
                out_root = (
                    run_dir_for_source(npm_root, source_path)
                    if npm_root is not None
                    else temp_root
                )
                for stem, js_text in modules.items():
                    (out_root / f"{stem}.mjs").write_text(js_text, encoding="utf-8")
                main_file = out_root / f"{source_path.stem}.mjs"
                node_exe = _resolve_js_runtime(source_path, npm_root=npm_root)
                # ESM walks from the .mjs upward to find node_modules; emit under
                # npm_root/runs/<id>/ so the central cache resolves. cwd stays the
                # source folder for relative data files.
                process = subprocess.run(
                    [node_exe, str(main_file)],
                    check=False,
                    cwd=str(source_path.parent),
                    env=env,
                )
                return process.returncode

            for stem, python_text in modules.items():
                (temp_root / f"{stem}.py").write_text(python_text, encoding="utf-8")
            main_file = temp_root / f"{source_path.stem}.py"
            # Run with the source folder as cwd so relative data files resolve;
            # put the temp modules first on PYTHONPATH for sibling imports.
            run_env = dict(env)
            existing = run_env.get("PYTHONPATH", "")
            run_env["PYTHONPATH"] = (
                str(temp_root) if not existing else str(temp_root) + os.pathsep + existing
            )
            process = subprocess.run(
                [python_exe, str(main_file)],
                check=False,
                cwd=str(source_path.parent),
                env=run_env,
            )
            return process.returncode

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(source_path.read_text(encoding="utf-8"))
        temp_filename = temp_file.name

    process = subprocess.run([python_exe, temp_filename], check=False, env=env)
    return process.returncode
