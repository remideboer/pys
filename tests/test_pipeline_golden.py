"""New pipeline must match characterization goldens (via compile_pys)."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.pipeline import compile_pys

GOLDEN = Path(__file__).resolve().parent / "golden"
EXPECTED = GOLDEN / "expected"


def _cases() -> list[Path]:
    files: list[Path] = []
    for root_name in ("ebnf", "fixtures"):
        root = GOLDEN / root_name
        if root.is_dir():
            files.extend(sorted(root.rglob("*.pys")))
    return files


def _expected_path(pys: Path) -> Path:
    rel = pys.relative_to(GOLDEN)
    key = str(rel.with_suffix("")).replace("\\", "/").replace("/", "__")
    return EXPECTED / f"{key}.py"


@pytest.mark.parametrize("pys_path", _cases(), ids=lambda p: str(p.relative_to(GOLDEN)))
def test_pipeline_matches_golden(pys_path: Path) -> None:
    exp = _expected_path(pys_path)
    source = pys_path.read_text(encoding="utf-8")
    got = compile_pys(source, target="python")
    assert got == exp.read_text(encoding="utf-8")
