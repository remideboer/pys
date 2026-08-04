"""Tests for examples/webserver/scripts/check_idempotency.py (F2)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "examples" / "webserver"
SCRIPT = ROOT / "scripts" / "check_idempotency.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_idempotency", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_idempotency"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_idempotency_gate_passes_on_project() -> None:
    gate = _load_gate()
    errs = gate.check(ROOT)
    assert errs == [], errs


def test_idempotency_gate_detects_missing_table_row(tmp_path: Path) -> None:
    gate = _load_gate()
    (tmp_path / "router.pys").write_text(
        'if (req.method == "GET" && req.path == "/new") {\n}\n',
        encoding="utf-8",
    )
    (tmp_path / "idempotency.md").write_text(
        "| Endpoint | x |\n|---|---|\n| `GET /health` | Yes |\n",
        encoding="utf-8",
    )
    (tmp_path / "idempotency.pys").write_text(
        'if (key == "GET /health") {\n}\n',
        encoding="utf-8",
    )
    errs = gate.check(tmp_path)
    assert any("idempotency.md" in e for e in errs)
    assert any("/new" in e for e in errs)
