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
    "transpile",
    "transpile_path",
    "transpile_with_modules",
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


def transpile(
    source_code: str,
    *,
    source_path: Path | None = None,
    allow_runtime_introspection: bool = False,
) -> str:
    """Convert teaching language source into valid Python source."""
    from .pipeline import compile_pys

    return compile_pys(
        source_code,
        target="python",
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )


def transpile_with_modules(
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
) -> dict[str, str]:
    """Transpile a .pys entry file and all imported .pys modules.

    Returns a mapping of module stem -> Python source text.
    """
    from .imports import discover_imported_modules
    from .pipeline import compile_pys

    source_path = source_path.resolve()
    text = source_path.read_text(encoding="utf-8")
    module_cache = discover_imported_modules(
        source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    modules = {
        source_path.stem: compile_pys(
            text,
            target="python",
            source_path=source_path,
            allow_runtime_introspection=allow_runtime_introspection,
        ),
    }
    for path in module_cache:
        modules[path.stem] = compile_pys(
            path.read_text(encoding="utf-8"),
            target="python",
            source_path=path,
            allow_runtime_introspection=allow_runtime_introspection,
        )
    return modules


def transpile_path(source_path: Path, target_path: Path) -> None:
    """Transpile a file to Python and write the output (plus imported modules)."""
    source_path = source_path.resolve()
    if source_path.suffix == ".pys":
        modules = transpile_with_modules(source_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(modules[source_path.stem], encoding="utf-8")
        for stem, python_text in modules.items():
            if stem == source_path.stem:
                continue
            (target_path.parent / f"{stem}.py").write_text(python_text, encoding="utf-8")
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def run_source(source_path: Path) -> int:
    """Transpile a source file and execute it with the current Python interpreter."""
    from .deps import (
        DepsError,
        WORKSPACE_ROOT_ENV,
        load_deps,
        prepend_pythonpath,
        resolve_python_executable,
        resolve_site_paths,
    )

    source_path = source_path.resolve()
    env = dict(os.environ)
    python_exe = sys.executable
    workspace_value = os.environ.get(WORKSPACE_ROOT_ENV)
    workspace_root = Path(workspace_value).expanduser().resolve() if workspace_value else None
    try:
        deps_config = load_deps(source_path, stop_at=workspace_root)
        if deps_config is not None:
            python_exe = resolve_python_executable(deps_config)
            site_paths = resolve_site_paths(deps_config, build="run", python=python_exe)
            env = prepend_pythonpath(site_paths, env)
    except DepsError as exc:
        raise TranspileError(str(exc), source_file=source_path) from exc

    if source_path.suffix == ".pys":
        modules = transpile_with_modules(
            source_path,
            allow_runtime_introspection=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
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
