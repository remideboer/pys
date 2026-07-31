#!/usr/bin/env python3
"""Regenerate golden expected/*.py from current transpile(). Opt-in only — never CI.

Usage (repo root):
  python tests/golden/regen.py
  python tests/golden/regen.py --only ebnf/expressions
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from transpiler.transpiler import TranspileError, transpile  # noqa: E402

GOLDEN = Path(__file__).resolve().parent
EBNF = GOLDEN / "ebnf"
FIXTURES = GOLDEN / "fixtures"
EXPECTED = GOLDEN / "expected"


def _rel_key(pys_path: Path) -> str:
    try:
        rel = pys_path.relative_to(GOLDEN)
    except ValueError:
        rel = pys_path.name
    return str(rel.with_suffix("")).replace("\\", "/")


def expected_path_for(pys_path: Path) -> Path:
    key = _rel_key(pys_path).replace("/", "__")
    return EXPECTED / f"{key}.py"


def iter_pys(only: str | None) -> list[Path]:
    roots = [EBNF, FIXTURES]
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        files.extend(sorted(root.rglob("*.pys")))
    if only:
        only_norm = only.replace("\\", "/").strip("/")
        files = [f for f in files if only_norm in str(f.relative_to(GOLDEN)).replace("\\", "/")]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default=None, help="Substring filter on path under tests/golden")
    args = parser.parse_args()
    EXPECTED.mkdir(parents=True, exist_ok=True)
    ok = 0
    fail = 0
    for pys in iter_pys(args.only):
        out = expected_path_for(pys)
        try:
            text = transpile(pys.read_text(encoding="utf-8"))
        except TranspileError as exc:
            print(f"SKIP (error) {pys.relative_to(GOLDEN)}: {exc}")
            fail += 1
            continue
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"WROTE {out.relative_to(GOLDEN)}")
        ok += 1
    print(f"Done: {ok} wrote, {fail} errors")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
