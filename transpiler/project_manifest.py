"""Project manifest (`pys.toml`) — source roots and package identity (ADR-017)."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MANIFEST_NAME = "pys.toml"

_ROOT_ASSIGN = re.compile(
    r'^\s*([A-Za-z_][\w-]*)\s*=\s*["\']([^"\']+)["\']\s*(?:#.*)?$'
)


@dataclass(frozen=True, slots=True)
class SourceRoots:
    """Declared source roots relative to the project (manifest) directory."""

    project_root: Path
    roots: tuple[tuple[str, Path], ...]  # (logical name, absolute path)

    def containing_root(self, file_path: Path) -> tuple[str, Path] | None:
        resolved = file_path.resolve()
        best: tuple[str, Path] | None = None
        best_len = -1
        for name, root in self.roots:
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            root_len = len(root.parts)
            if root_len > best_len:
                best = (name, root)
                best_len = root_len
        return best


@dataclass(frozen=True, slots=True)
class PackageIdentity:
    """Post-root-stripping package path (posix, no leading/trailing slash).

    For ``src/billing/Invoice.pys`` with root ``src``, ``rel_dir`` is ``billing``.
    Files directly under a root use empty ``rel_dir`` (``""``).
    """

    rel_dir: str
    root_name: str
    root_path: Path

    @property
    def display(self) -> str:
        return self.rel_dir if self.rel_dir else "."


def find_manifest(start: Path) -> Path | None:
    """Walk upward from ``start`` (file or dir) for ``pys.toml``."""
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for directory in (cur, *cur.parents):
        candidate = directory / MANIFEST_NAME
        if candidate.is_file():
            return candidate
    return None


def _manifest_error(
    message: str,
    *,
    manifest: Path,
    code: str,
    suggested_fix: str | None = None,
    tips: list[str] | None = None,
) -> None:
    from .transpiler import TranspileError

    raise TranspileError(
        message,
        source_file=manifest,
        code=code,
        suggested_fix=suggested_fix,
        tips=tips
        if tips is not None
        else ["Set `[project].main` to a contained `.pys` file."],
    )


def _parse_project_main_text(text: str, manifest: Path) -> str | None:
    """Return the optional `[project].main` string."""
    project = _parse_project_table(text, manifest)
    if project is None:
        return None
    raw = project.get("main")
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        _manifest_error(
            "`[project].main` must be a non-empty path string.",
            manifest=manifest,
            code="pys.entrypoint-main",
        )
    return raw.strip()


EMIT_TARGETS = frozenset({"python", "javascript"})


def _parse_project_table(text: str, manifest: Path) -> dict | None:
    """Return the `[project]` table as a plain dict, or None if absent."""
    if sys.version_info >= (3, 11):
        import tomllib

        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            _manifest_error(
                f"Invalid {MANIFEST_NAME}: {exc}",
                manifest=manifest,
                code="pys.manifest-invalid",
            )
        project = data.get("project")
        if project is None:
            return None
        if not isinstance(project, dict):
            _manifest_error(
                "`[project]` must be a TOML table.",
                manifest=manifest,
                code="pys.manifest-project",
            )
        return project

    # Python < 3.11: line scan for string assignments only.
    in_project = False
    project: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped.lower() == "[project]"
            continue
        if in_project:
            match = _ROOT_ASSIGN.match(line)
            if match:
                key = match.group(1)
                if key in project:
                    _manifest_error(
                        f"`[project].{key}` may be declared only once.",
                        manifest=manifest,
                        code="pys.manifest-invalid",
                    )
                project[key] = match.group(2).strip()
            elif re.match(r"^\s*main\s*=", line):
                _manifest_error(
                    "`[project].main` must be a non-empty path string.",
                    manifest=manifest,
                    code="pys.entrypoint-main",
                )
            elif re.match(r"^\s*target\s*=", line):
                _manifest_error(
                    "`[project].target` must be \"python\" or \"javascript\".",
                    manifest=manifest,
                    code="pys.manifest-target",
                )
    return project or None


def _parse_project_emit_target_text(text: str, manifest: Path) -> str | None:
    """Return optional `[project].target` (``python`` | ``javascript``)."""
    project = _parse_project_table(text, manifest)
    if project is None:
        return None
    raw = project.get("target")
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        _manifest_error(
            '`[project].target` must be "python" or "javascript".',
            manifest=manifest,
            code="pys.manifest-target",
        )
    value = raw.strip().lower()
    if value not in EMIT_TARGETS:
        _manifest_error(
            f'`[project].target` must be "python" or "javascript", got {raw!r}.',
            manifest=manifest,
            code="pys.manifest-target",
            suggested_fix='target = "python"',
            tips=['Use target = "python" or target = "javascript".'],
        )
    return value


@lru_cache(maxsize=64)
def _load_project_emit_target_cached(manifest_path: str, text: str) -> str | None:
    return _parse_project_emit_target_text(text, Path(manifest_path))


def load_project_emit_target(start: Path) -> str:
    """Emit target from nearest ``pys.toml`` ``[project].target``, else ``python``."""
    path = start.expanduser()
    try:
        path = path.resolve()
    except OSError:
        return "python"
    if path.is_file() and path.name == MANIFEST_NAME:
        manifest = path
    else:
        manifest = find_manifest(path)
    if manifest is None:
        return "python"
    text = manifest.read_text(encoding="utf-8")
    return _load_project_emit_target_cached(str(manifest.resolve()), text) or "python"


@lru_cache(maxsize=64)
def _load_project_main_cached(manifest_path: str, text: str) -> Path | None:
    manifest = Path(manifest_path)
    raw = _parse_project_main_text(text, manifest)
    if raw is None:
        return None
    project_root = manifest.parent.resolve()
    candidate = (project_root / raw.replace("\\", "/")).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError:
        _manifest_error(
            f"`[project].main` resolves outside the project: {raw}",
            manifest=manifest,
            code="pys.entrypoint-outside",
        )
    if candidate.suffix.lower() != ".pys":
        _manifest_error(
            f"`[project].main` must name a `.pys` file: {raw}",
            manifest=manifest,
            code="pys.entrypoint-suffix",
        )
    if not candidate.is_file():
        _manifest_error(
            f"Configured entrypoint does not exist: {raw}",
            manifest=manifest,
            code="pys.entrypoint-missing",
        )
    return candidate


def load_project_main(manifest_path: Path) -> Path | None:
    """Load and safely resolve `[project].main` from one manifest."""
    manifest = manifest_path.resolve()
    if not manifest.is_file():
        _manifest_error(
            f"Project manifest not found: {manifest}",
            manifest=manifest,
            code="pys.manifest-missing",
        )
    text = manifest.read_text(encoding="utf-8")
    return _load_project_main_cached(str(manifest), text)


def resolve_entrypoint(selected: Path) -> Path:
    """Resolve a selected file/directory against authoritative manifest main."""
    choice = selected.expanduser().resolve()
    if not choice.exists():
        from .transpiler import TranspileError

        raise TranspileError(
            f"Selected path does not exist: {choice}",
            source_file=choice,
            code="pys.entrypoint-missing",
        )
    manifest = find_manifest(choice)
    configured = load_project_main(manifest) if manifest is not None else None
    if configured is not None:
        if choice.is_file() and choice != configured:
            from .transpiler import TranspileError

            raise TranspileError(
                f"Selected file '{choice.name}' conflicts with the configured "
                f"entrypoint '{configured.name}'.",
                source_file=choice,
                code="pys.entrypoint-conflict",
                suggested_fix=str(configured),
                tips=[
                    "Run the configured entrypoint, or use “Set as entrypoint” "
                    "to update pys.toml."
                ],
            )
        return configured
    if choice.is_file():
        if choice.suffix.lower() != ".pys":
            from .transpiler import TranspileError

            raise TranspileError(
                f"Entrypoint must be a `.pys` file: {choice}",
                source_file=choice,
                code="pys.entrypoint-suffix",
            )
        return choice
    from .transpiler import TranspileError

    raise TranspileError(
        "Running a directory requires `[project].main` in pys.toml.",
        source_file=manifest or choice / MANIFEST_NAME,
        code="pys.entrypoint-main",
        suggested_fix='[project]\nmain = "main.pys"',
        tips=["Choose the project entry file explicitly."],
    )


def _parse_source_roots_text(text: str, project_root: Path) -> SourceRoots | None:
    """Parse ``[source_roots]`` from pys.toml (stdlib tomllib on 3.11+, else line scan)."""
    section: dict[str, str] = {}
    if sys.version_info >= (3, 11):
        import tomllib

        data = tomllib.loads(text)
        raw = data.get("source_roots")
        if isinstance(raw, dict):
            for name, rel in raw.items():
                if isinstance(name, str) and isinstance(rel, str):
                    section[name] = rel
    else:
        in_section = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                in_section = stripped.lower() == "[source_roots]"
                continue
            if not in_section:
                continue
            m = _ROOT_ASSIGN.match(line)
            if m:
                section[m.group(1)] = m.group(2)

    if not section:
        return None
    roots: list[tuple[str, Path]] = []
    for name, rel in section.items():
        rel = rel.strip().replace("\\", "/")
        if not rel or rel in {".", "./"}:
            abs_root = project_root
        else:
            abs_root = (project_root / rel).resolve()
        roots.append((name, abs_root))
    if not roots:
        return None
    roots.sort(key=lambda item: len(item[1].parts), reverse=True)
    return SourceRoots(project_root=project_root, roots=tuple(roots))


def _parse_source_roots(manifest_path: Path) -> SourceRoots | None:
    return _parse_source_roots_text(
        manifest_path.read_text(encoding="utf-8"),
        manifest_path.parent.resolve(),
    )


@lru_cache(maxsize=64)
def load_source_roots(manifest_path: str) -> SourceRoots | None:
    return _parse_source_roots(Path(manifest_path))


def source_roots_for(file_path: Path) -> SourceRoots | None:
    manifest = find_manifest(file_path)
    if manifest is None:
        return None
    return load_source_roots(str(manifest.resolve()))


def package_identity(file_path: Path, roots: SourceRoots | None = None) -> PackageIdentity | None:
    """Return root-relative package dir for ``file_path``, or None if outside roots."""
    path = file_path.resolve()
    if roots is None:
        roots = source_roots_for(path)
    if roots is None:
        return None
    found = roots.containing_root(path)
    if found is None:
        return None
    root_name, root_path = found
    parent = path.parent
    rel = parent.relative_to(root_path)
    rel_dir = "" if rel == Path(".") else rel.as_posix()
    return PackageIdentity(rel_dir=rel_dir, root_name=root_name, root_path=root_path)


def package_peer_files(file_path: Path) -> list[Path]:
    """All ``.pys`` files in the same package (across source roots, or same folder)."""
    path = file_path.resolve()
    roots = source_roots_for(path)
    if roots is None:
        return sorted(p.resolve() for p in path.parent.glob("*.pys"))
    ident = package_identity(path, roots)
    if ident is None:
        return sorted(p.resolve() for p in path.parent.glob("*.pys"))
    peers: list[Path] = []
    for _name, root in roots.roots:
        pkg_dir = root / ident.rel_dir if ident.rel_dir else root
        if pkg_dir.is_dir():
            peers.extend(pkg_dir.glob("*.pys"))
    return sorted({p.resolve() for p in peers})


def same_package(a: Path, b: Path) -> bool:
    """True if both files share a package under declared roots, or same folder (legacy)."""
    roots = source_roots_for(a) or source_roots_for(b)
    if roots is None:
        return a.resolve().parent == b.resolve().parent
    id_a = package_identity(a, roots)
    id_b = package_identity(b, roots)
    if id_a is None or id_b is None:
        return a.resolve().parent == b.resolve().parent
    return id_a.rel_dir == id_b.rel_dir


def package_mismatch_diagnostic(
    *,
    importer: Path,
    declaree: Path,
    symbol: str,
) -> str | None:
    """Educational hint when package scopes differ under source roots (req §4)."""
    roots = source_roots_for(importer) or source_roots_for(declaree)
    if roots is None:
        return None
    id_imp = package_identity(importer, roots)
    id_dec = package_identity(declaree, roots)
    if id_imp is None or id_dec is None:
        return None
    if id_imp.rel_dir == id_dec.rel_dir:
        return None
    suggested = id_imp.root_path / id_dec.rel_dir / importer.name
    try:
        suggested_rel = suggested.relative_to(roots.project_root).as_posix()
    except ValueError:
        suggested_rel = suggested.as_posix()
    return (
        f"'{importer.name}' resolves to package '{id_imp.display}' "
        f"(relative to source root '{id_imp.root_name}'), which does not match "
        f"package '{id_dec.display}' (relative to source root '{id_dec.root_name}') "
        f"where '{symbol}' is declared.\n"
        f"Did you mean to place this file at '{suggested_rel}'?"
    )
