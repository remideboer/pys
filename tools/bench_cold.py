"""Cold-process benchmark: one compile per fresh interpreter.

This is the scenario the IDE actually runs (ide-process.js spawns a new Python
process per request), so caches start empty. Reports the best of N spawns.

Usage:
    python tools/bench_cold.py --rounds 3
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHILD = """
import sys, time
from pathlib import Path
sys.path.insert(0, {root!r})
path = Path({target!r})
text = path.read_text(encoding='utf-8')
from transpiler.pipeline import compile_pys
start = time.perf_counter()
compile_pys(text, source_path=path)
print(time.perf_counter() - start)
"""

CHILD_IDE = """
import sys, time
from pathlib import Path
sys.path.insert(0, {root!r})
path = Path({target!r})
from transpiler.ide import analyze_file
start = time.perf_counter()
analyze_file(path)
print(time.perf_counter() - start)
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--label", default="cold")
    parser.add_argument(
        "--ide", action="store_true", help="measure analyze_file (the IDE request path)"
    )
    args = parser.parse_args()
    template = CHILD_IDE if args.ide else CHILD

    # The gui/ examples need third-party deps resolved, which dominates and stalls
    # the IDE path, so measure it on the self-contained examples only.
    targets = [
        ROOT / "examples" / "main.pys",
        ROOT / "examples" / "interfaces.pys",
        ROOT / "examples" / "funcs.pys",
    ] if args.ide else [
        ROOT / "examples" / "gui" / "pokemontcg" / "main.pys",
        ROOT / "examples" / "gui" / "pokemontcg" / "ui.pys",
        ROOT / "examples" / "gui" / "PyQt" / "main.pys",
        ROOT / "examples" / "main.pys",
        ROOT / "examples" / "interfaces.pys",
    ]

    kind = "analyze_file" if args.ide else "compile"
    print(f"[{args.label}] cold {kind}, best of {args.rounds} fresh processes\n")
    total = 0.0
    for target in targets:
        code = template.format(root=str(ROOT), target=str(target))
        best = None
        for _ in range(args.rounds):
            start = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True, check=False
            )
            wall = time.perf_counter() - start
            if proc.returncode != 0:
                print(f"  FAILED {target.name}: {proc.stderr.strip()[:200]}")
                best = None
                break
            inner = float(proc.stdout.strip().splitlines()[-1])
            if best is None or inner < best[0]:
                best = (inner, wall)
        if best is None:
            continue
        total += best[0]
        rel = target.relative_to(ROOT).as_posix()
        print(f"  {best[0] * 1000:>8.1f} ms  ({best[1] * 1000:>7.1f} ms incl. startup)  {rel}")
    print(f"\n[{args.label}] total {kind} time: {total * 1000:.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
