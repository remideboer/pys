"""Build dist/pys-student-<version>.zip for ELO / offline install.

Expects pys-language/pys-language-<version>.vsix to exist (run npm run package first).
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DIST = REPO / "dist"
PKG = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
VERSION = PKG["version"]
VSIX_NAME = f"pys-language-{VERSION}.vsix"
VSIX = ROOT / VSIX_NAME
STAGE = DIST / f"pys-student-{VERSION}"
ZIP_PATH = DIST / f"pys-student-{VERSION}.zip"

INSTALL_NL_EN = f"""PYS student pack {VERSION}
=======================

Inhoud / Contents
-----------------
- {VSIX_NAME}     VS Code-extensie (transpiler + Run ingebundeld)
- install.cmd     Windows: dubbelklik of in cmd uitvoeren
- install.sh      macOS/Linux
- INSTALL.txt     dit bestand

Vereisten / Requirements
------------------------
- Visual Studio Code (of Cursor)
- Python 3.10+ op PATH (`python` of `python3`)

Installeren / Install
---------------------
1. Unzip dit archief.
2. Windows: dubbelklik install.cmd
   macOS/Linux:  chmod +x install.sh && ./install.sh
3. Herlaad VS Code / Reload Window.
4. Open een map met .pys-bestanden → PYS: Run File.

Handmatig / Manual
------------------
  code --install-extension {VSIX_NAME} --force

Bibliotheken (pys.deps): geen venv. Bij eerste Run kunnen packages
naar ~/.pys/repository gedownload worden.

Marketplace (aanbevolen als beschikbaar):
  ext install remideboer.pys-language
"""

INSTALL_CMD = f"""@echo off
setlocal
cd /d "%~dp0"
where code >nul 2>nul
if errorlevel 1 (
  echo VS Code 'code' staat niet op PATH.
  echo Open VS Code → Command Palette → "Shell Command: Install 'code' command in PATH"
  exit /b 1
)
echo Installing {VSIX_NAME} ...
code --install-extension "%~dp0{VSIX_NAME}" --force
if errorlevel 1 exit /b 1
echo.
echo Klaar. Herlaad VS Code (Developer: Reload Window).
pause
"""

INSTALL_SH = f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v code >/dev/null 2>&1; then
  echo "VS Code 'code' is not on PATH."
  echo "VS Code → Command Palette → Install 'code' command in PATH"
  exit 1
fi
echo "Installing {VSIX_NAME} ..."
code --install-extension "./{VSIX_NAME}" --force
echo
echo "Done. Reload VS Code (Developer: Reload Window)."
"""


def main() -> None:
    if not VSIX.is_file():
        raise SystemExit(f"Missing {VSIX}. Run: npm run package")

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    shutil.copy2(VSIX, STAGE / VSIX_NAME)
    (STAGE / "INSTALL.txt").write_text(INSTALL_NL_EN, encoding="utf-8", newline="\n")
    (STAGE / "install.cmd").write_text(INSTALL_CMD, encoding="utf-8", newline="\r\n")
    (STAGE / "install.sh").write_text(INSTALL_SH, encoding="utf-8", newline="\n")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in STAGE.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=f"pys-student-{VERSION}/{path.relative_to(STAGE).as_posix()}")

    print(f"ELO zip -> {ZIP_PATH}")


if __name__ == "__main__":
    main()
