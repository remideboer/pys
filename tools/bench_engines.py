"""Compare hot compile_pys under RD vs PEG brace engines."""
from __future__ import annotations

import statistics
import time
from pathlib import Path

from transpiler import parse as parse_mod
from transpiler.pipeline import compile_pys

FILES = [
    Path("examples/main.pys"),
    Path("examples/interfaces.pys"),
    Path("examples/gui/pokemontcg/main.pys"),
    Path("examples/gui/pokemontcg/ui.pys"),
    Path("examples/gui/PyQt/main.pys"),
]


def main() -> int:
    for eng in ("rd", "peg"):
        parse_mod.set_brace_engine(eng)
        total = 0.0
        print(f"[{eng}] hot compile_pys, median of 8")
        for path in FILES:
            text = path.read_text(encoding="utf-8")
            compile_pys(text, source_path=path)
            times = []
            for _ in range(8):
                start = time.perf_counter()
                compile_pys(text, source_path=path)
                times.append(time.perf_counter() - start)
            med = statistics.median(times)
            total += med
            print(f"{med * 1000:8.1f} ms  {path.as_posix()}")
        print(f"total {total * 1000:.1f} ms\n")
    parse_mod.set_brace_engine("rd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
