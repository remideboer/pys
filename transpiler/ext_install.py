"""Dev helper: package and install the local PYS VS Code/Cursor extension."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

_VSIX_RE = re.compile(r"^pys-language-(\d+)\.(\d+)\.(\d+)\.vsix$", re.IGNORECASE)


def repo_root_from_package() -> Path:
    """Source-tree repo root when ``transpiler`` lives at ``<repo>/transpiler``."""
    return Path(__file__).resolve().parents[1]


def find_extension_dir(repo_root: Path | None = None) -> Path:
    root = (repo_root or repo_root_from_package()).resolve()
    ext = root / "pys-language"
    if not (ext / "package.json").is_file():
        raise FileNotFoundError(
            f"No pys-language/package.json under {root}. "
            "Run from a PYS source checkout (editable install)."
        )
    return ext


def parse_vsix_version(path: Path) -> tuple[int, int, int] | None:
    match = _VSIX_RE.match(path.name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def latest_vsix(extension_dir: Path) -> Path:
    candidates: list[tuple[tuple[int, int, int], Path]] = []
    for path in extension_dir.glob("pys-language-*.vsix"):
        version = parse_vsix_version(path)
        if version is not None:
            candidates.append((version, path))
    if not candidates:
        raise FileNotFoundError(
            f"No pys-language-*.vsix in {extension_dir}. "
            "Build one with: cd pys-language && npm run package"
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def resolve_editor_cli(prefer: str = "auto") -> str:
    """Return absolute path to ``cursor`` or ``code`` on PATH."""
    order: list[str]
    if prefer == "auto":
        order = ["cursor", "code"]
    elif prefer in {"cursor", "code"}:
        order = [prefer]
    else:
        raise ValueError(f"Unknown editor preference: {prefer!r} (use auto|cursor|code)")
    for name in order:
        found = shutil.which(name)
        if found:
            return found
    tried = " / ".join(order)
    raise FileNotFoundError(
        f"Neither editor CLI found on PATH ({tried}). "
        "Cursor/VS Code → Command Palette → Install 'cursor'/'code' command in PATH."
    )


def command_argv(executable: str, *args: str) -> list[str]:
    """Build a subprocess argv that can run Windows ``.cmd`` / ``.bat`` shims."""
    resolved = shutil.which(executable) or executable
    if os.name == "nt":
        # CreateProcess cannot launch .cmd/.bat directly (WinError 2).
        return ["cmd", "/c", resolved, *args]
    return [resolved, *args]


def build_vsix(extension_dir: Path, *, npm: str | None = None) -> None:
    npm_cmd = npm or shutil.which("npm")
    if not npm_cmd:
        raise FileNotFoundError("npm not found on PATH (needed to package the extension).")
    subprocess.run(
        command_argv(npm_cmd, "run", "package"),
        cwd=str(extension_dir),
        check=True,
    )


def install_vsix(vsix: Path, *, editor: str = "auto") -> list[str]:
    cli = resolve_editor_cli(editor)
    cmd = command_argv(cli, "--install-extension", str(vsix.resolve()), "--force")
    subprocess.run(cmd, check=True)
    return cmd


def install_extension(
    *,
    repo_root: Path | None = None,
    build: bool = True,
    editor: str = "auto",
) -> Path:
    """Package (optional) and install the newest local ``pys-language-*.vsix``.

    Returns the installed VSIX path. Does not auto-reload the editor.
    """
    ext_dir = find_extension_dir(repo_root)
    if build:
        build_vsix(ext_dir)
    vsix = latest_vsix(ext_dir)
    install_vsix(vsix, editor=editor)
    return vsix
