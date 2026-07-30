"""Project dependency resolution via pys.deps (Maven-style central repo, no venv).

Flyweight: packages live once under ~/.pys/repository/packages/<name>/<version>/
and are shared across projects. The runner only adds those paths to PYTHONPATH.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


DEPS_FILENAME = "pys.deps"
REPO_ROOT_ENV = "PYS_REPO"
DEFAULT_REPO = Path.home() / ".pys" / "repository"


@dataclass
class Dependency:
    name: str
    version: str | None = None  # None => latest
    build: str | None = None  # run | test | None (both)


@dataclass
class InterpreterConfig:
    version: str | None = None  # e.g. ">=3.9", "<3.5", "any"
    path: str | None = None


@dataclass
class DepsConfig:
    interpreter: InterpreterConfig = field(default_factory=InterpreterConfig)
    dependencies: list[Dependency] = field(default_factory=list)
    source_path: Path | None = None


class DepsError(ValueError):
    """Invalid pys.deps or dependency resolution failure."""


def default_repo_root() -> Path:
    override = os.environ.get(REPO_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_REPO.resolve()


def find_deps_file(start: Path) -> Path | None:
    """Walk upward from start (file or dir) looking for pys.deps."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in [current, *current.parents]:
        candidate = directory / DEPS_FILENAME
        if candidate.is_file():
            return candidate
        # Stop at filesystem root-ish: when parent == self
        if directory.parent == directory:
            break
    return None


def parse_deps_text(text: str, *, source_path: Path | None = None) -> DepsConfig:
    """Parse the indented pys.deps format."""
    config = DepsConfig(source_path=source_path)
    section: str | None = None
    current_dep: Dependency | None = None
    dep_indent: int | None = None

    def _strip_comment(line: str) -> str:
        in_string = False
        quote = ""
        for i, ch in enumerate(line):
            if in_string:
                if ch == quote:
                    in_string = False
                continue
            if ch in {'"', "'"}:
                in_string = True
                quote = ch
                continue
            if ch == "#":
                return line[:i].rstrip()
        return line.rstrip()

    def _indent_width(raw: str) -> int:
        width = 0
        for ch in raw:
            if ch == " ":
                width += 1
            elif ch == "\t":
                width += 4
            else:
                break
        return width

    lines = text.splitlines()
    for line_no, raw in enumerate(lines, start=1):
        stripped = _strip_comment(raw)
        if not stripped.strip():
            continue
        indent = _indent_width(stripped)
        content = stripped.strip()
        label = str(source_path) if source_path else "pys.deps"

        section_match = re.fullmatch(r"\[(?P<name>[A-Za-z_]\w*)\]", content)
        if section_match:
            if indent != 0:
                raise DepsError(f"{label}:{line_no}: section headers must not be indented")
            section = section_match.group("name").lower()
            current_dep = None
            dep_indent = None
            if section not in {"interpreter", "dependencies"}:
                raise DepsError(f"{label}:{line_no}: unknown section '[{section}]'")
            continue

        if section is None:
            raise DepsError(f"{label}:{line_no}: content outside of a [section]")

        if section == "interpreter":
            if indent == 0:
                raise DepsError(f"{label}:{line_no}: interpreter entries must be indented")
            key, sep, value = content.partition(":")
            if not sep:
                raise DepsError(f"{label}:{line_no}: expected `key: value`")
            key = key.strip().lower()
            value = value.strip()
            if key == "version":
                config.interpreter.version = None if value.lower() in {"", "any"} else value
            elif key == "path":
                config.interpreter.path = value or None
            else:
                raise DepsError(f"{label}:{line_no}: unknown interpreter key '{key}'")
            continue

        # [dependencies]
        if indent == 0:
            raise DepsError(
                f"{label}:{line_no}: dependency names must be indented under [dependencies]"
            )

        is_property = (
            current_dep is not None
            and dep_indent is not None
            and indent > dep_indent
            and ":" in content
        )
        if is_property:
            key, sep, value = content.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "version":
                current_dep.version = None if value.lower() in {"", "latest"} else value
            elif key == "build":
                if value and value not in {"run", "test"}:
                    raise DepsError(f"{label}:{line_no}: build must be 'run' or 'test'")
                current_dep.build = value or None
            else:
                raise DepsError(f"{label}:{line_no}: unknown dependency key '{key}'")
            continue

        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+\-]*", content):
            current_dep = Dependency(name=content)
            dep_indent = indent
            config.dependencies.append(current_dep)
            continue

        raise DepsError(f"{label}:{line_no}: invalid dependency line '{content}'")

    return config


def load_deps(start: Path) -> DepsConfig | None:
    path = find_deps_file(start)
    if path is None:
        return None
    return parse_deps_text(path.read_text(encoding="utf-8"), source_path=path)


def _normalize_package_dir(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_version_constraint(constraint: str | None) -> None:
    """Validate interpreter version against the running interpreter (or raise)."""
    if constraint is None:
        return
    text = constraint.strip()
    if not text or text.lower() == "any":
        return

    current = sys.version_info[:3]

    def _parse_ver(token: str) -> tuple[int, ...]:
        parts = token.strip().split(".")
        try:
            return tuple(int(p) for p in parts[:3])
        except ValueError as exc:
            raise DepsError(f"Invalid interpreter version '{token}'") from exc

    # Support: >=3.9 | >3.9 | <=3.12 | <3.5 | ==3.11 | 3.11
    match = re.fullmatch(r"(>=|<=|>|<|==)?\s*(\d+(?:\.\d+){0,2})", text)
    if not match:
        raise DepsError(
            f"Invalid interpreter version constraint '{constraint}'. "
            "Use forms like 'any', '>=3.9', '<3.5'."
        )
    op = match.group(1) or "=="
    required = _parse_ver(match.group(2))
    # Pad for comparison
    cur = current + (0,) * (len(required) - len(current))
    req = required + (0,) * (len(current) - len(required))
    cur = cur[: max(len(required), 3)]
    req = req[: max(len(required), 3)]
    ok = {
        ">=": cur >= req,
        ">": cur > req,
        "<=": cur <= req,
        "<": cur < req,
        "==": cur[: len(required)] == required,
    }[op]
    if not ok:
        running = ".".join(str(x) for x in sys.version_info[:3])
        raise DepsError(
            f"Interpreter version {running} does not satisfy pys.deps requirement '{constraint}'."
        )


def resolve_python_executable(config: DepsConfig) -> str:
    _parse_version_constraint(config.interpreter.version)
    if config.interpreter.path:
        path = Path(config.interpreter.path).expanduser()
        if not path.exists():
            raise DepsError(f"Interpreter path not found: {path}")
        return str(path.resolve())
    return sys.executable


def _read_installed_version(target_dir: Path) -> str | None:
    if not target_dir.is_dir():
        return None
    for dist in target_dir.glob("*.dist-info"):
        meta = dist / "METADATA"
        if not meta.is_file():
            continue
        for line in meta.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    return None


def _progress_prefix(index: int | None, total: int | None) -> str:
    if index is not None and total is not None and total > 0:
        return f"[{index}/{total}] "
    return ""


def _pip_install(
    python: str,
    package_spec: str,
    target: Path,
    *,
    progress_label: str | None = None,
) -> None:
    import threading

    target.mkdir(parents=True, exist_ok=True)
    cmd = [
        python,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        "--target",
        str(target),
        package_spec,
    ]

    stop = threading.Event()
    spinner_thread: threading.Thread | None = None

    if progress_label:
        frames = ["|", "/", "-", "\\"]

        def _spin() -> None:
            i = 0
            while not stop.wait(0.12):
                frame = frames[i % len(frames)]
                sys.stdout.write(f"\r  {progress_label} {frame}")
                sys.stdout.flush()
                i += 1

        spinner_thread = threading.Thread(target=_spin, daemon=True)
        spinner_thread.start()

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    stop.set()
    if spinner_thread is not None:
        spinner_thread.join(timeout=1.0)
        # Clear the spinner line before the final status is printed by the caller.
        sys.stdout.write("\r" + " " * (len(progress_label) + 8) + "\r")
        sys.stdout.flush()

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise DepsError(f"Failed to install '{package_spec}' into central repo:\n{detail}")


def _latest_pointer(package_root: Path) -> Path:
    return package_root / "LATEST"


def ensure_dependency(
    dep: Dependency,
    *,
    python: str,
    repo_root: Path | None = None,
    index: int | None = None,
    total: int | None = None,
    quiet: bool = False,
) -> Path:
    """Install (if needed) and return the flyweight package directory."""
    repo = repo_root or default_repo_root()
    pkg_key = _normalize_package_dir(dep.name)
    package_root = repo / "packages" / pkg_key
    prefix = _progress_prefix(index, total)
    version_label = dep.version or "latest"
    label = f"{dep.name} ({version_label})"

    def _status(message: str) -> None:
        if not quiet:
            print(f"  {message}", flush=True)

    if dep.version:
        target = package_root / dep.version
        if target.is_dir() and _read_installed_version(target):
            _status(f"{prefix}cached  {label}")
            return target  # flyweight hit
        progress = None if quiet else f"{prefix}downloading {label}"
        _pip_install(python, f"{dep.name}=={dep.version}", target, progress_label=progress)
        if not _read_installed_version(target):
            raise DepsError(f"Install of {dep.name}=={dep.version} produced no dist-info in {target}")
        _status(f"{prefix}downloaded {label}")
        return target

    # latest: reuse LATEST pointer when present
    pointer = _latest_pointer(package_root)
    if pointer.is_file():
        pointed = package_root / pointer.read_text(encoding="utf-8").strip()
        if pointed.is_dir() and _read_installed_version(pointed):
            _status(f"{prefix}cached  {dep.name} ({pointed.name})")
            return pointed

    staging = package_root / "_staging_latest"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    progress = None if quiet else f"{prefix}downloading {label}"
    _pip_install(python, dep.name, staging, progress_label=progress)
    version = _read_installed_version(staging)
    if not version:
        raise DepsError(f"Could not determine installed version for '{dep.name}'")
    target = package_root / version
    if target.exists():
        shutil.rmtree(staging, ignore_errors=True)
    else:
        shutil.move(str(staging), str(target))
    pointer.write_text(version + "\n", encoding="utf-8")
    _status(f"{prefix}downloaded {dep.name} ({version})")
    return target


def deps_for_build(config: DepsConfig, build: str = "run") -> list[Dependency]:
    selected: list[Dependency] = []
    for dep in config.dependencies:
        if dep.build is None or dep.build == build:
            selected.append(dep)
    return selected


def resolve_site_paths(
    config: DepsConfig,
    *,
    build: str = "run",
    python: str | None = None,
    repo_root: Path | None = None,
    quiet: bool = False,
) -> list[Path]:
    """Ensure dependencies are present in the central repo; return paths for PYTHONPATH."""
    python_exe = python or resolve_python_executable(config)
    deps = deps_for_build(config, build=build)
    total = len(deps)
    if total and not quiet:
        noun = "dependency" if total == 1 else "dependencies"
        src = f" from {config.source_path}" if config.source_path else ""
        print(f"Resolving {total} {noun}{src}...", flush=True)
    paths: list[Path] = []
    for index, dep in enumerate(deps, start=1):
        paths.append(
            ensure_dependency(
                dep,
                python=python_exe,
                repo_root=repo_root,
                index=index,
                total=total,
                quiet=quiet,
            )
        )
    if total and not quiet:
        print("Dependencies ready.", flush=True)
    return paths


def prepend_pythonpath(paths: Iterable[Path], env: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(env or os.environ)
    extra = os.pathsep.join(str(p) for p in paths)
    if not extra:
        return merged
    existing = merged.get("PYTHONPATH", "")
    merged["PYTHONPATH"] = extra if not existing else f"{extra}{os.pathsep}{existing}"
    return merged


def module_present_on_paths(module_ref: str, site_paths: Iterable[Path]) -> bool:
    """True if dotted module_ref exists under any site path (as file or package)."""
    parts = [p for p in module_ref.split(".") if p]
    if not parts:
        return False
    for site in site_paths:
        base = Path(site)
        candidate = base.joinpath(*parts)
        if candidate.with_suffix(".py").is_file():
            return True
        if (candidate / "__init__.py").is_file():
            return True
        if candidate.is_dir() and any(candidate.iterdir()):
            return True
    return False


def is_external_python_module(module_ref: str, site_paths: Iterable[Path] | None = None) -> bool:
    """True if module_ref is importable from deps site paths or the stdlib."""
    ref = module_ref.strip().strip("\"'")
    if not ref or "/" in ref or "\\" in ref or ref.lower().endswith(".pys"):
        return False
    paths = list(site_paths or [])
    if paths and module_present_on_paths(ref, paths):
        return True
    try:
        import importlib.util

        return importlib.util.find_spec(ref) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def ensure_site_paths_for(start: Path, *, build: str = "run", quiet: bool = False) -> list[Path]:
    """Load pys.deps near start (if any) and ensure packages are present."""
    config = load_deps(start)
    if config is None:
        return []
    return resolve_site_paths(config, build=build, quiet=quiet)
