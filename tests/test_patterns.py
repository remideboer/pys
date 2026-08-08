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
    assert len(general) == 2, "expected DI + service locator under general/"
    authentication = [p for p in paths if "authentication" in p.parts]
    assert len(authentication) == 4, "expected four authentication pattern demos"
    architectural = [p for p in paths if "architectural" in p.parts]
    assert len(architectural) == 6, "expected six architectural pattern demos"
    messaging = [p for p in paths if "messaging" in p.parts]
    assert len(messaging) == 7, "expected seven messaging pattern demos"
    reactive = [p for p in paths if "reactive" in p.parts]
    assert len(reactive) == 1, "expected reactive demo"
    persistence = [p for p in paths if "persistence" in p.parts]
    assert len(persistence) == 6, "expected six persistence pattern demos"
    application = [p for p in paths if "application" in p.parts]
    assert len(application) == 6, "expected six application pattern demos"
    authorization = [p for p in paths if "authorization" in p.parts]
    assert len(authorization) == 3, "expected three authorization pattern demos"
    resilience = [p for p in paths if "resilience" in p.parts]
    assert len(resilience) == 7, "expected seven resilience pattern demos"
    testing = [p for p in paths if "testing" in p.parts]
    assert len(testing) == 3, "expected three testing pattern demos"
    for path in paths:
        try:
            out = transpile(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AssertionError(
                f"{path.relative_to(ROOT)} failed to transpile: {exc}"
            ) from exc
        assert isinstance(out, str)
        assert len(out) > 0
