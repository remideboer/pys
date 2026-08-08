"""Transpile gate for examples/design_patterns/**/*.pys (GoF demos)."""

from __future__ import annotations

from pathlib import Path

from transpiler.transpiler import transpile

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "examples" / "design_patterns"


def test_design_patterns_pys_transpile() -> None:
    paths = sorted(PATTERNS.rglob("*.pys"))
    assert paths, "expected examples/design_patterns/**/*.pys"
    for path in paths:
        try:
            out = transpile(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AssertionError(
                f"{path.relative_to(ROOT)} failed to transpile: {exc}"
            ) from exc
        assert isinstance(out, str)
        assert len(out) > 0
