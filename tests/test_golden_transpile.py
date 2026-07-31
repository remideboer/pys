"""Characterization: current transpile() must match committed expected/*.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.transpiler import transpile

GOLDEN = Path(__file__).resolve().parent / "golden"
EXPECTED = GOLDEN / "expected"


def _cases() -> list[Path]:
    files: list[Path] = []
    for root_name in ("ebnf", "fixtures"):
        root = GOLDEN / root_name
        if root.is_dir():
            files.extend(sorted(root.rglob("*.pys")))
    # Multi-module entry is exercised via transpile_with_modules elsewhere;
    # single-file transpile of use_helper alone is still a valid import shape.
    return files


def _expected_path(pys: Path) -> Path:
    rel = pys.relative_to(GOLDEN)
    key = str(rel.with_suffix("")).replace("\\", "/").replace("/", "__")
    return EXPECTED / f"{key}.py"


@pytest.mark.parametrize("pys_path", _cases(), ids=lambda p: str(p.relative_to(GOLDEN)))
def test_golden_transpile(pys_path: Path) -> None:
    exp = _expected_path(pys_path)
    assert exp.is_file(), f"Missing golden {exp.name}; run: python tests/golden/regen.py"
    source = pys_path.read_text(encoding="utf-8")
    got = transpile(source)
    assert got == exp.read_text(encoding="utf-8")
