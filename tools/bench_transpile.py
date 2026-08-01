"""Benchmark the PYS compile pipeline per phase.

Usage:
    python tools/bench_transpile.py                # timing table
    python tools/bench_transpile.py --repeat 20    # more iterations
    python tools/bench_transpile.py --profile      # cProfile of the whole corpus
"""
from __future__ import annotations

import argparse
import cProfile
import pstats
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from transpiler import parse as parse_mod  # noqa: E402
from transpiler import sem as sem_mod  # noqa: E402
from transpiler.emit import python as emit_python  # noqa: E402
from transpiler.lex import tokenize_with_flags  # noqa: E402

PHASES = ("tokenize", "parse", "analyze", "emit")


def corpus() -> list[tuple[Path, str]]:
    """Every .pys file we can compile standalone, largest first."""
    paths = sorted(
        {*(ROOT / "examples").rglob("*.pys"), *(ROOT / "tests" / "golden").rglob("*.pys")},
        key=lambda p: -p.stat().st_size,
    )
    files: list[tuple[Path, str]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        try:
            tree = parse_mod.parse_program(text)
            sem_mod.analyze(tree, source_path=path)
        except Exception:  # noqa: BLE001 - error-case fixtures are not benchmarkable
            continue
        files.append((path, text))
    return files


def time_phases(path: Path, text: str) -> dict[str, float]:
    """One full compile, timing each phase separately.

    Lex once, then parse from tokens so the parse column is parse-only
    (matches ``compile_pys``, which lexes once inside ``parse_program``).
    """
    timings: dict[str, float] = {}

    start = time.perf_counter()
    lexed = tokenize_with_flags(text)
    timings["tokenize"] = time.perf_counter() - start

    start = time.perf_counter()
    tree = parse_mod.parse_program_from_tokens(lexed, source=text)
    timings["parse"] = time.perf_counter() - start

    start = time.perf_counter()
    tree = sem_mod.analyze(tree, source_path=path)
    timings["analyze"] = time.perf_counter() - start

    start = time.perf_counter()
    emit_python.emit(tree, source_path=path)
    timings["emit"] = time.perf_counter() - start

    return timings


def run_timing(files: list[tuple[Path, str]], repeat: int) -> None:
    per_file: dict[Path, dict[str, float]] = {}
    for path, text in files:
        runs = [time_phases(path, text) for _ in range(repeat)]
        per_file[path] = {
            phase: statistics.median(run[phase] for run in runs) for phase in PHASES
        }

    header = f"{'file':<44}" + "".join(f"{phase:>11}" for phase in PHASES) + f"{'total':>11}"
    print(header)
    print("-" * len(header))
    totals = dict.fromkeys(PHASES, 0.0)
    for path, timings in sorted(per_file.items(), key=lambda kv: -sum(kv[1].values())):
        row = f"{path.relative_to(ROOT).as_posix():<44}"
        for phase in PHASES:
            totals[phase] += timings[phase]
            row += f"{timings[phase] * 1000:>10.2f}m"
        print(row + f"{sum(timings.values()) * 1000:>10.2f}m")
    print("-" * len(header))
    grand = sum(totals.values())
    summary = f"{'TOTAL':<44}"
    for phase in PHASES:
        summary += f"{totals[phase] * 1000:>10.2f}m"
    print(summary + f"{grand * 1000:>10.2f}m")
    share = f"{'share':<44}"
    for phase in PHASES:
        share += f"{totals[phase] / grand * 100:>10.1f}%"
    print(share)


def run_profile(files: list[tuple[Path, str]], repeat: int) -> None:
    def workload() -> None:
        for _ in range(repeat):
            for path, text in files:
                time_phases(path, text)

    profiler = cProfile.Profile()
    profiler.enable()
    workload()
    profiler.disable()
    pstats.Stats(profiler).sort_stats("tottime").print_stats(30)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=10)
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()

    files = corpus()
    print(f"corpus: {len(files)} files, {sum(len(t) for _, t in files)} bytes, repeat={args.repeat}\n")
    if args.profile:
        run_profile(files, args.repeat)
    else:
        run_timing(files, args.repeat)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
