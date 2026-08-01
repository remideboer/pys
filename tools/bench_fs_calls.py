"""Count filesystem calls (resolve/stat/exists/read) by transpiler call site during analyze."""
from __future__ import annotations

import sys
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from transpiler import parse as parse_mod  # noqa: E402
from transpiler import sem as sem_mod  # noqa: E402

counts: Counter[str] = Counter()
TRACKED = ("resolve", "exists", "is_file", "is_dir", "read_text", "stat")


def call_site() -> str:
    """Nearest transpiler frame above the pathlib call."""
    for frame in reversed(traceback.extract_stack()[:-2]):
        if "python-transpiler\\transpiler" in frame.filename or "python-transpiler/transpiler" in frame.filename:
            return f"{Path(frame.filename).name}:{frame.lineno} {frame.name}"
    return "<outside transpiler>"


def install() -> None:
    for name in TRACKED:
        original = getattr(Path, name)

        def make(original=original, name=name):
            def wrapper(self, *args, **kwargs):
                counts[f"{name:<10} {call_site()}"] += 1
                return original(self, *args, **kwargs)

            return wrapper

        setattr(Path, name, make())


def main() -> int:
    paths = sorted((ROOT / "examples").rglob("*.pys"), key=lambda p: -p.stat().st_size)
    files = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        try:
            sem_mod.analyze(parse_mod.parse_program(text), source_path=path)
        except Exception:  # noqa: BLE001
            continue
        files.append((path, parse_mod.parse_program(text)))

    install()
    for path, tree in files:
        sem_mod.analyze(tree, source_path=path)

    total = sum(counts.values())
    print(f"{total} filesystem calls across {len(files)} analyze() calls\n")
    for site, count in counts.most_common(25):
        print(f"{count:>7}  {site}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
