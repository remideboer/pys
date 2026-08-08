"""Transpile gate for examples/patterns/**/*.pys."""

from __future__ import annotations

from pathlib import Path

from transpiler.transpiler import transpile

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "examples" / "patterns"


def test_patterns_pys_transpile() -> None:
    paths = sorted(PATTERNS.rglob("*.pys"))
    assert paths, "expected examples/patterns/**/*.pys"
    concurrency = [p for p in paths if "concurrency" in p.parts]
    assert len(concurrency) == 4, "expected four concurrency pattern demos"
    general = [p for p in paths if "general" in p.parts]
    assert len(general) == 1, "expected dependency_injection under general/"
    authentication = [p for p in paths if "authentication" in p.parts]
    assert len(authentication) == 4, "expected four authentication pattern demos"
    for path in paths:
        try:
            out = transpile(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AssertionError(
                f"{path.relative_to(ROOT)} failed to transpile: {exc}"
            ) from exc
        assert isinstance(out, str)
        assert len(out) > 0
