#!/usr/bin/env python3
"""Local CI gates that mirror the common GitHub checks before push/tag.

Run from repo root:

    python tools/local_ci.py

Gates (fail-fast):
  1. python -m pytest -q
  2. npm test  (in pys-language/)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "pys-language"


def run(label: str, argv: list[str], *, cwd: Path) -> None:
    print(f"\n==> {label}")
    print(" ".join(argv))
    r = subprocess.run(argv, cwd=str(cwd))
    if r.returncode != 0:
        print(f"\nFAIL: {label} (exit {r.returncode})", file=sys.stderr)
        raise SystemExit(r.returncode)
    print(f"OK: {label}")


def main() -> None:
    run("pytest", [sys.executable, "-m", "pytest", "-q"], cwd=ROOT)

    npm = shutil.which("npm")
    if npm is None:
        print(
            "FAIL: npm not found on PATH — cannot run pys-language tests.\n"
            "Install Node.js, then re-run: python tools/local_ci.py",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not (EXT / "package.json").is_file():
        print(f"FAIL: missing {EXT / 'package.json'}", file=sys.stderr)
        raise SystemExit(1)
    run("pys-language npm test", [npm, "test"], cwd=EXT)

    print("\nAll local CI gates passed.")


if __name__ == "__main__":
    main()
