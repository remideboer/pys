"""Dev helper: package and install the local PYS VS Code/Cursor extension."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
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


def _reload_window_windows() -> None:
    # Command palette accepts the English command title (NLS resolvedLanguage is typically en).
    script = r"""
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
$activated = $false
foreach ($title in @('Cursor', 'Visual Studio Code')) {
  if ($shell.AppActivate($title)) { $activated = $true; break }
}
if (-not $activated) {
  # Fallback: any window title containing Cursor / Code
  $procs = Get-Process | Where-Object { $_.MainWindowTitle -match 'Cursor|Visual Studio Code' }
  foreach ($p in $procs) {
    if ($shell.AppActivate($p.Id)) { $activated = $true; break }
  }
}
if (-not $activated) { throw 'Could not activate Cursor/VS Code window' }
Start-Sleep -Milliseconds 250
$shell.SendKeys('^+p')
Start-Sleep -Milliseconds 350
$shell.SendKeys('Developer: Reload Window')
Start-Sleep -Milliseconds 350
$shell.SendKeys('{ENTER}')
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
    )


def _reload_window_macos() -> None:
    script = """
tell application "System Events"
  set appNames to {"Cursor", "Code", "Visual Studio Code"}
  set target to missing value
  repeat with n in appNames
    if exists process n then
      set target to n
      exit repeat
    end if
  end repeat
  if target is missing value then error "Cursor/VS Code not running"
  tell process target
    set frontmost to true
    keystroke "p" using {command down, shift down}
    delay 0.35
    keystroke "Developer: Reload Window"
    delay 0.35
    key code 36
  end tell
end tell
"""
    subprocess.run(["osascript", "-e", script], check=True)


def _reload_window_linux() -> None:
    if not shutil.which("xdotool"):
        raise FileNotFoundError(
            "xdotool not found (needed to send Reload Window keys on Linux)."
        )
    # Prefer Cursor, then Code.
    for name in ("Cursor", "code"):
        search = subprocess.run(
            ["xdotool", "search", "--name", name],
            check=False,
            capture_output=True,
            text=True,
        )
        window_ids = [w for w in search.stdout.split() if w]
        if not window_ids:
            continue
        wid = window_ids[0]
        subprocess.run(["xdotool", "windowactivate", "--sync", wid], check=True)
        subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+shift+p"], check=True)
        time.sleep(0.35)
        subprocess.run(["xdotool", "type", "--clearmodifiers", "Developer: Reload Window"], check=True)
        time.sleep(0.35)
        subprocess.run(["xdotool", "key", "--clearmodifiers", "Return"], check=True)
        return
    raise FileNotFoundError("No Cursor/VS Code window found for xdotool.")


def reload_editor_window() -> None:
    """Best-effort invoke ``Developer: Reload Window`` via the command palette."""
    import sys

    if os.name == "nt":
        _reload_window_windows()
    elif sys.platform == "darwin":
        _reload_window_macos()
    else:
        _reload_window_linux()


def install_extension(
    *,
    repo_root: Path | None = None,
    build: bool = True,
    editor: str = "auto",
    reload: bool = True,
) -> Path:
    """Package (optional) and install the newest local ``pys-language-*.vsix``.

    Returns the installed VSIX path.
    """
    ext_dir = find_extension_dir(repo_root)
    if build:
        build_vsix(ext_dir)
    vsix = latest_vsix(ext_dir)
    install_vsix(vsix, editor=editor)
    if reload:
        try:
            reload_editor_window()
        except (FileNotFoundError, OSError, subprocess.CalledProcessError) as exc:
            print(
                f"Could not auto-reload the editor: {exc}\n"
                "Run Developer: Reload Window manually.",
                flush=True,
            )
            return vsix
    return vsix
