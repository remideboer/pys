"""Project dependency resolution via exact, hashed ``pys.lock`` environments.

Resolved environments are cached by lock digest under ``~/.pys/repository`` and
shared across projects. The runner only adds validated cache paths to PYTHONPATH.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .workspace import WORKSPACE_ROOT_ENV

DEPS_FILENAME = "pys.deps"
LOCK_FILENAME = "pys.lock"
REPO_ROOT_ENV = "PYS_REPO"
DEFAULT_REPO = Path.home() / ".pys" / "repository"
DEFAULT_INDEX_URL = "https://pypi.org/simple"
# Safe version tokens for pip (no spaces, options, URLs, or env markers).
_VERSION_RE = re.compile(r"^(?=.*\d)[A-Za-z0-9][A-Za-z0-9._+-]*$")


@dataclass
class Dependency:
    name: str
    version: str | None = None  # Run dependencies must be exact before locking.
    build: str | None = None  # run | test | None (both)


@dataclass
class InterpreterConfig:
    version: str | None = None  # e.g. ">=3.9", "<3.5", "any"


@dataclass
class DepsConfig:
    interpreter: InterpreterConfig = field(default_factory=InterpreterConfig)
    dependencies: list[Dependency] = field(default_factory=list)
    source_path: Path | None = None


@dataclass(frozen=True)
class LockedPackage:
    name: str
    version: str
    url: str
    sha256: str


@dataclass(frozen=True)
class DepsLock:
    deps_fingerprint: str
    python: str
    platform: str
    index_url: str
    packages: tuple[LockedPackage, ...]


class DepsError(ValueError):
    """Invalid pys.deps or dependency resolution failure."""


def default_repo_root() -> Path:
    override = os.environ.get(REPO_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_REPO.resolve()


def _workspace_stop_at(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    raw = os.environ.get(WORKSPACE_ROOT_ENV)
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def find_deps_file(start: Path, *, stop_at: Path | None = None) -> Path | None:
    """Walk upward from start (file or dir) looking for pys.deps.

    When ``stop_at`` is set (or ``PYS_WORKSPACE_ROOT`` is in the environment),
    do not honor a ``pys.deps`` above that directory.
    """
    current = start.resolve()
    if current.is_file():
        current = current.parent
    bound = _workspace_stop_at(stop_at)
    for directory in [current, *current.parents]:
        if bound is not None:
            try:
                directory.relative_to(bound)
            except ValueError:
                break
        candidate = directory / DEPS_FILENAME
        if candidate.is_file():
            return candidate
        if bound is not None and directory == bound:
            break
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
                raise DepsError(
                    f"{label}:{line_no}: interpreter.path is not allowed in project config. "
                    "Select Python explicitly, for example: "
                    "`/path/to/python -m transpiler run main.pys`."
                )
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
                if value.lower() in {"", "latest"}:
                    current_dep.version = None
                elif not _VERSION_RE.fullmatch(value):
                    raise DepsError(
                        f"{label}:{line_no}: invalid dependency version '{value}'. "
                        "Use a simple version like '1.2.3' or 'latest'."
                    )
                else:
                    current_dep.version = value
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


def load_deps(start: Path, *, stop_at: Path | None = None) -> DepsConfig | None:
    path = find_deps_file(start, stop_at=stop_at)
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


def lookup_cached_dependency(
    dep: Dependency,
    *,
    repo_root: Path | None = None,
) -> Path | None:
    """Return the flyweight package directory if already installed; never download."""
    repo = repo_root or default_repo_root()
    pkg_key = _normalize_package_dir(dep.name)
    package_root = repo / "packages" / pkg_key

    if dep.version:
        target = package_root / dep.version
        if target.is_dir() and _read_installed_version(target):
            return target
        return None

    pointer = _latest_pointer(package_root)
    if pointer.is_file():
        pointed = package_root / pointer.read_text(encoding="utf-8").strip()
        if pointed.is_dir() and _read_installed_version(pointed):
            return pointed
    return None


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

    cached = lookup_cached_dependency(dep, repo_root=repo)
    if cached is not None:
        if dep.version:
            _status(f"{prefix}cached  {label}")
        else:
            _status(f"{prefix}cached  {dep.name} ({cached.name})")
        return cached

    if dep.version:
        target = package_root / dep.version
        progress = None if quiet else f"{prefix}downloading {label}"
        _pip_install(python, f"{dep.name}=={dep.version}", target, progress_label=progress)
        if not _read_installed_version(target):
            raise DepsError(f"Install of {dep.name}=={dep.version} produced no dist-info in {target}")
        _status(f"{prefix}downloaded {label}")
        return target

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
    _latest_pointer(package_root).write_text(version + "\n", encoding="utf-8")
    _status(f"{prefix}downloaded {dep.name} ({version})")
    return target


def deps_for_build(config: DepsConfig, build: str = "run") -> list[Dependency]:
    selected: list[Dependency] = []
    for dep in config.dependencies:
        if dep.build is None or dep.build == build:
            selected.append(dep)
    return selected


def _require_pinned_dependencies(config: DepsConfig, build: str = "run") -> list[Dependency]:
    deps = deps_for_build(config, build=build)
    unpinned = [dep.name for dep in deps if not dep.version]
    if unpinned:
        names = ", ".join(sorted(unpinned))
        raise DepsError(
            f"Run dependencies must use exact versions before locking: {names}. "
            "Set `version: X.Y.Z` in pys.deps."
        )
    return deps


def deps_fingerprint(config: DepsConfig, build: str = "run") -> str:
    deps = _require_pinned_dependencies(config, build)
    payload = [
        {"name": _normalize_package_dir(dep.name), "version": dep.version}
        for dep in sorted(deps, key=lambda item: _normalize_package_dir(item.name))
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _lock_path(config: DepsConfig, lock_path: Path | None = None) -> Path:
    if lock_path is not None:
        return lock_path.resolve()
    if config.source_path is None:
        raise DepsError("Cannot locate pys.lock without a source pys.deps path.")
    return config.source_path.resolve().with_name(LOCK_FILENAME)


def _lock_dict(lock: DepsLock) -> dict:
    return {
        "schema": 1,
        "deps_fingerprint": lock.deps_fingerprint,
        "python": lock.python,
        "platform": lock.platform,
        "index_url": lock.index_url,
        "packages": [
            {
                "name": package.name,
                "version": package.version,
                "url": package.url,
                "sha256": package.sha256,
            }
            for package in lock.packages
        ],
    }


def write_lock(lock: DepsLock, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_lock_dict(lock), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_lock(path: Path) -> DepsLock:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DepsError(
            f"Missing {LOCK_FILENAME}. Run `python -m transpiler deps lock {DEPS_FILENAME}`."
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise DepsError(f"Invalid dependency lock {path}: {exc}") from exc

    if raw.get("schema") != 1 or not isinstance(raw.get("packages"), list):
        raise DepsError(f"Unsupported or invalid dependency lock: {path}")
    packages: list[LockedPackage] = []
    seen_names: set[str] = set()
    for item in raw["packages"]:
        try:
            package = LockedPackage(
                name=str(item["name"]),
                version=str(item["version"]),
                url=str(item["url"]),
                sha256=str(item["sha256"]).lower(),
            )
        except (KeyError, TypeError) as exc:
            raise DepsError(f"Invalid package entry in {path}") from exc
        if not re.fullmatch(r"[0-9a-f]{64}", package.sha256):
            raise DepsError(f"Invalid SHA-256 for {package.name} in {path}")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+\-]*", package.name):
            raise DepsError(f"Invalid package name in {path}: {package.name}")
        if not _VERSION_RE.fullmatch(package.version):
            raise DepsError(f"Invalid package version for {package.name} in {path}")
        if not package.url.startswith(("https://", "file://")):
            raise DepsError(f"Untrusted package URL for {package.name}: {package.url}")
        if any(char.isspace() for char in package.url):
            raise DepsError(f"Invalid whitespace in package URL for {package.name}")
        normalized = _normalize_package_dir(package.name)
        if normalized in seen_names:
            raise DepsError(f"Duplicate package in {path}: {package.name}")
        seen_names.add(normalized)
        packages.append(package)
    return DepsLock(
        deps_fingerprint=str(raw.get("deps_fingerprint", "")),
        python=str(raw.get("python", "")),
        platform=str(raw.get("platform", "")),
        index_url=str(raw.get("index_url", "")),
        packages=tuple(sorted(packages, key=lambda package: _normalize_package_dir(package.name))),
    )


def validate_lock(lock: DepsLock, config: DepsConfig, build: str = "run") -> None:
    expected_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    expected_platform = sysconfig.get_platform()
    if lock.deps_fingerprint != deps_fingerprint(config, build):
        raise DepsError(f"{LOCK_FILENAME} is stale; regenerate it after changing {DEPS_FILENAME}.")
    if lock.python != expected_python:
        raise DepsError(
            f"{LOCK_FILENAME} targets Python {lock.python}, running Python is {expected_python}."
        )
    if lock.platform != expected_platform:
        raise DepsError(
            f"{LOCK_FILENAME} targets platform {lock.platform}, running platform is {expected_platform}."
        )
    if lock.index_url != DEFAULT_INDEX_URL:
        raise DepsError(f"{LOCK_FILENAME} must use trusted index {DEFAULT_INDEX_URL}.")
    locked = {
        _normalize_package_dir(package.name): package.version
        for package in lock.packages
    }
    for dep in _require_pinned_dependencies(config, build):
        if locked.get(_normalize_package_dir(dep.name)) != dep.version:
            raise DepsError(
                f"{LOCK_FILENAME} does not contain the exact direct dependency "
                f"{dep.name}=={dep.version}."
            )


def lock_declares_module(start: Path, module_ref: str, build: str = "run") -> bool:
    """Recognize a locked dependency without importing or installing it."""
    try:
        config = load_deps(start)
        if config is None:
            return False
        lock = read_lock(_lock_path(config))
        if lock.deps_fingerprint != deps_fingerprint(config, build):
            return False
    except DepsError:
        return False

    top = _normalize_package_dir(module_ref.split(".", 1)[0])
    for dep in _require_pinned_dependencies(config, build):
        package = _normalize_package_dir(dep.name)
        if package == top or package.startswith(top + "-"):
            return True
    return False


def generate_lock(
    config: DepsConfig,
    *,
    build: str = "run",
    python: str | None = None,
    lock_path: Path | None = None,
    index_url: str = DEFAULT_INDEX_URL,
) -> Path:
    """Resolve exact packages with pip's report and write a hashed pys.lock."""
    if index_url != DEFAULT_INDEX_URL:
        raise DepsError(f"Only the trusted index {DEFAULT_INDEX_URL} is supported.")
    deps = _require_pinned_dependencies(config, build)
    python_exe = python or resolve_python_executable(config)
    specs = [f"{dep.name}=={dep.version}" for dep in deps]
    destination = _lock_path(config, lock_path)

    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = Path(temp_dir) / "report.json"
        cmd = [
            python_exe,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--disable-pip-version-check",
            "--report",
            str(report_path),
            "--index-url",
            index_url,
            *specs,
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise DepsError(f"Failed to resolve dependency lock:\n{detail}")
        report = json.loads(report_path.read_text(encoding="utf-8"))

    packages: list[LockedPackage] = []
    for item in report.get("install", []):
        metadata = item.get("metadata") or {}
        download = item.get("download_info") or {}
        archive = download.get("archive_info") or {}
        hashes = archive.get("hashes") or {}
        sha256 = hashes.get("sha256")
        name = metadata.get("name")
        version = metadata.get("version")
        url = download.get("url")
        if not all((name, version, url, sha256)):
            raise DepsError("pip resolver report omitted package URL/version/SHA-256.")
        packages.append(
            LockedPackage(
                name=str(name),
                version=str(version),
                url=str(url),
                sha256=str(sha256).lower(),
            )
        )
    if deps and not packages:
        raise DepsError("pip resolver report contained no packages.")

    lock = DepsLock(
        deps_fingerprint=deps_fingerprint(config, build),
        python=f"{sys.version_info.major}.{sys.version_info.minor}",
        platform=sysconfig.get_platform(),
        index_url=index_url,
        packages=tuple(sorted(packages, key=lambda package: _normalize_package_dir(package.name))),
    )
    write_lock(lock, destination)
    return destination


def _lock_environment_path(lock: DepsLock, repo_root: Path | None = None) -> Path:
    repo = repo_root or default_repo_root()
    encoded = json.dumps(_lock_dict(lock), sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return repo / "environments" / digest


def _locked_environment_if_present(
    lock: DepsLock,
    *,
    repo_root: Path | None = None,
) -> Path | None:
    target = _lock_environment_path(lock, repo_root)
    marker = target / ".pys-lock.json"
    if target.is_dir() and marker.is_file():
        return target
    return None


def ensure_locked_environment(
    lock: DepsLock,
    *,
    python: str,
    repo_root: Path | None = None,
    quiet: bool = False,
) -> Path:
    cached = _locked_environment_if_present(lock, repo_root=repo_root)
    if cached is not None:
        return cached

    target = _lock_environment_path(lock, repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    requirements = staging.parent / f".{staging.name}-requirements.txt"
    try:
        requirements.write_text(
            "\n".join(
                f"{package.name} @ {package.url} --hash=sha256:{package.sha256}"
                for package in lock.packages
            )
            + "\n",
            encoding="utf-8",
        )
        cmd = [
            python,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "--require-hashes",
            "--no-deps",
            "--index-url",
            DEFAULT_INDEX_URL,
            "--target",
            str(staging),
            "-r",
            str(requirements),
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise DepsError(f"Failed to install locked dependencies:\n{detail}")
        (staging / ".pys-lock.json").write_text(
            json.dumps(_lock_dict(lock), sort_keys=True),
            encoding="utf-8",
        )
        if target.exists():
            shutil.rmtree(staging, ignore_errors=True)
        else:
            shutil.move(str(staging), str(target))
    finally:
        requirements.unlink(missing_ok=True)
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    if not quiet:
        print("Locked dependencies ready.", flush=True)
    return target


def resolve_site_paths(
    config: DepsConfig,
    *,
    build: str = "run",
    python: str | None = None,
    repo_root: Path | None = None,
    quiet: bool = False,
    install: bool = True,
) -> list[Path]:
    """Return site paths for PYTHONPATH from the central deps repo.

    When ``install`` is True (default), missing packages are downloaded via pip.
    When ``install`` is False, only already-cached packages are returned — never
    network or subprocess work. Use the read-only mode for IDE validation so
    opening a project cannot trigger installs from an untrusted ``pys.deps``.
    """
    deps = deps_for_build(config, build=build)
    total = len(deps)

    if total and config.source_path is not None:
        lock = read_lock(_lock_path(config))
        validate_lock(lock, config, build)
        if not install:
            cached = _locked_environment_if_present(lock, repo_root=repo_root)
            return [cached] if cached is not None else []
        python_exe = python or resolve_python_executable(config)
        return [
            ensure_locked_environment(
                lock,
                python=python_exe,
                repo_root=repo_root,
                quiet=quiet,
            )
        ]

    if not install:
        paths: list[Path] = []
        for dep in deps:
            cached = lookup_cached_dependency(dep, repo_root=repo_root)
            if cached is not None:
                paths.append(cached)
        return paths

    python_exe = python or resolve_python_executable(config)
    if total and not quiet:
        noun = "dependency" if total == 1 else "dependencies"
        src = f" from {config.source_path}" if config.source_path else ""
        print(f"Resolving {total} {noun}{src}...", flush=True)
    paths = []
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
    # Extension suffixes used by binary modules (e.g. PyQt6/QtCore.pyd).
    ext_suffixes = (".py", ".pyd", ".so", ".dylib")
    for site in site_paths:
        base = Path(site)
        candidate = base.joinpath(*parts)
        for suffix in ext_suffixes:
            if candidate.with_suffix(suffix).is_file():
                return True
        # Tagged wheels: name.cp311-win_amd64.pyd / name.cpython-311-*.so
        parent = candidate.parent
        stem = candidate.name
        if parent.is_dir():
            for child in parent.iterdir():
                if not child.is_file():
                    continue
                if child.name == stem or child.name.startswith(stem + "."):
                    if child.suffix in {".pyd", ".so", ".dylib", ".py"} or ".so." in child.name:
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
    # Also accept the top-level package when only a submodule was requested and
    # the leaf is a binary extension we could not see (defensive). Prefer path check above.
    if paths and "." in ref:
        top = ref.split(".", 1)[0]
        if module_present_on_paths(top, paths):
            try:
                from .pytypes import _with_sys_path
                import importlib.util

                with _with_sys_path(paths):
                    if importlib.util.find_spec(ref) is not None:
                        return True
            except (ImportError, ModuleNotFoundError, ValueError):
                pass
    try:
        import importlib.util

        return importlib.util.find_spec(ref) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def ensure_site_paths_for(
    start: Path,
    *,
    build: str = "run",
    quiet: bool = False,
    install: bool = True,
    stop_at: Path | None = None,
) -> list[Path]:
    """Load pys.deps near start (if any) and return site paths.

    Pass ``install=False`` for IDE / compile-time lookups that must not
    download packages as a side effect of opening a file.
    """
    config = load_deps(start, stop_at=stop_at)
    if config is None:
        return []
    return resolve_site_paths(config, build=build, quiet=quiet, install=install)
